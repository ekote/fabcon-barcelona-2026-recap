#!/usr/bin/env python3
"""fabdemo: build the FabCon Europe 2026 recap demo environment in your own Microsoft Fabric tenant and run the scripted demos.

Everything is synthetic: an invented oud perfume house with formulas, ingredients, and preference trials.
Settings come from config.env next to this file (copy config.example.env). Authentication uses your Azure CLI login (az login).

Environment
  python3 fabdemo.py up [--lang en|pl|de]       capacity, workspace, data, semantic model, eventhouse, failing pipeline, showcase items
  python3 fabdemo.py capacity create|pause|resume|delete|status
  python3 fabdemo.py settings on|off --yes      five preview tenant settings, needs a Fabric administrator
  python3 fabdemo.py workspace | data | model | eventhouse | pipeline
  python3 fabdemo.py showcase aifunc|mlv|agent [--lang en|pl|de]
  python3 fabdemo.py status
  python3 fabdemo.py down [--capacity]          deletes the workspace, and the capacity with --capacity

Scripted demos (see runbooks/)
  python3 fabdemo.py catalog-search <text> [Type,Type]
  python3 fabdemo.py table-read <table> [col,col]
  python3 fabdemo.py uc [table]  |  irc [table]
  python3 fabdemo.py core-mcp init|tools|call <tool> [json]
  python3 fabdemo.py iq-mcp tools|discover <text>|dax <model> <DAX>
"""
import base64, json, os, random, re, subprocess, sys, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
API = 'https://api.fabric.microsoft.com/v1'
ARM = 'https://management.azure.com'
LH_NAME, LH_MLV, EH_NAME, MODEL = 'lh_oud_rd', 'lh_oud_mlv', 'eh_oud_trials', 'Oud RnD'
SETTINGS = ['OntologyPreview', 'PolicySetTenantSwitch', 'PowerBIMCP', 'MonitoringTenant', 'WorkspaceBlockOutboundAccess']


# ── configuration and auth ───────────────────────────────────────────────────
def config():
    c = {}
    f = HERE / 'config.env'
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k, v = line.split('=', 1); c[k.strip()] = v.strip()
    c.update({k: v for k, v in os.environ.items() if k.startswith('FABDEMO_')})
    need = ['FABDEMO_SUBSCRIPTION', 'FABDEMO_RESOURCE_GROUP', 'FABDEMO_CAPACITY', 'FABDEMO_ADMIN']
    miss = [k for k in need if not c.get(k)]
    if miss: raise SystemExit(f'missing in config.env: {", ".join(miss)} (copy config.example.env to config.env)')
    c.setdefault('FABDEMO_REGION', 'francecentral'); c.setdefault('FABDEMO_SKU', 'F8')
    c.setdefault('FABDEMO_WORKSPACE', 'fabcon-recap-demo'); c.setdefault('FABDEMO_LANG', 'en')
    return c


C = None
_tok = {}


def token(resource):
    if resource not in _tok:
        _tok[resource] = subprocess.check_output(['az', 'account', 'get-access-token', '--subscription', C['FABDEMO_SUBSCRIPTION'],
                                                  '--resource', resource, '--query', 'accessToken', '-o', 'tsv'], text=True).strip()
    return _tok[resource]


def H(resource='https://api.fabric.microsoft.com'):
    return {'Authorization': 'Bearer ' + token(resource), 'Content-Type': 'application/json'}


def say(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)


def lro(r):
    """Fabric long-running operation: 200/201 return the body, 202 polls Location until done."""
    if r.status_code in (200, 201): return r.json() if r.text else {}
    if r.status_code != 202: raise SystemExit(f'HTTP {r.status_code}: {r.text[:600]}')
    loc = r.headers['Location']
    while True:
        time.sleep(int(r.headers.get('Retry-After', '3')))
        s = requests.get(loc, headers=H()).json()
        if s.get('status') in ('Succeeded', 'Failed'):
            if s['status'] == 'Failed': raise SystemExit(f'operation failed: {json.dumps(s)[:600]}')
            res = requests.get(loc + '/result', headers=H())
            return res.json() if res.status_code == 200 and res.text else s


def b64(o): return base64.b64encode((o if isinstance(o, str) else json.dumps(o, ensure_ascii=False)).encode()).decode()


# ── capacity ─────────────────────────────────────────────────────────────────
def cap_url():
    return f"{ARM}/subscriptions/{C['FABDEMO_SUBSCRIPTION']}/resourceGroups/{C['FABDEMO_RESOURCE_GROUP']}/providers/Microsoft.Fabric/capacities/{C['FABDEMO_CAPACITY']}"


def cap_get():
    r = requests.get(cap_url(), headers=H(ARM), params={'api-version': '2023-11-01'})
    return r.json() if r.status_code == 200 else None


def cap_wait(state):
    for _ in range(60):
        c = cap_get()
        if c and c['properties'].get('provisioningState') == 'Succeeded' and c['properties'].get('state') == state:
            return say('capacity', state)
        time.sleep(10)
    raise SystemExit(f'capacity did not reach {state} in 10 minutes')


def cu_price(region):
    """Pay-as-you-go price of one capacity unit hour in EUR, from the public Azure Retail Prices API."""
    f = f"serviceName eq 'Microsoft Fabric' and armRegionName eq '{region}' and meterName eq 'Compute Pool Capacity Usage CU' and priceType eq 'Consumption'"
    try:
        items = requests.get('https://prices.azure.com/api/retail/prices', params={'currencyCode': 'EUR', '$filter': f}, timeout=20).json()['Items']
        return items[0]['retailPrice'] if items else None
    except Exception:
        return None


def capacity(action='create'):
    cu = int(re.sub(r'\D', '', C['FABDEMO_SKU']) or 0)
    if action == 'status':
        c = cap_get(); return say('capacity', (c['sku']['name'], c['properties']['state']) if c else 'none')
    if action == 'create':
        c = cap_get()
        if not c:
            body = {'location': C['FABDEMO_REGION'], 'sku': {'name': C['FABDEMO_SKU'], 'tier': 'Fabric'},
                    'properties': {'administration': {'members': [C['FABDEMO_ADMIN']]}}, 'tags': {'purpose': 'fabcon-recap demos'}}
            r = requests.put(cap_url(), headers=H(ARM), params={'api-version': '2023-11-01'}, json=body)
            if r.status_code not in (200, 201, 202): raise SystemExit(f'capacity create: {r.status_code} {r.text[:400]}')
            say('capacity create sent', C['FABDEMO_SKU'], C['FABDEMO_REGION'])
        elif c['properties']['state'] == 'Paused':
            r = requests.post(f'{cap_url()}/resume', headers=H(ARM), params={'api-version': '2023-11-01'}); say('resume', r.status_code)
        cap_wait('Active')
        p = cu_price(C['FABDEMO_REGION'])
        cost = f'about {cu * p:.2f} EUR per hour (Azure retail price, {C["FABDEMO_REGION"]})' if p else 'see azure.microsoft.com/pricing/details/microsoft-fabric'
        say(f'billing: {C["FABDEMO_SKU"]} costs {cost} while Active. Pause it with: python3 fabdemo.py capacity pause')
        return
    act = {'pause': 'suspend', 'resume': 'resume', 'delete': None}[action]
    if action == 'delete':
        r = requests.delete(cap_url(), headers=H(ARM), params={'api-version': '2023-11-01'}); return say('capacity delete', r.status_code)
    r = requests.post(f'{cap_url()}/{act}', headers=H(ARM), params={'api-version': '2023-11-01'}); say(action, r.status_code)
    cap_wait('Paused' if action == 'pause' else 'Active')


def settings(on, yes):
    if not yes:
        raise SystemExit('This changes tenant settings for the whole organization: ' + ', '.join(SETTINGS) +
                         '. Use a test tenant, then rerun with --yes.')
    for n in SETTINGS:
        r = requests.post(f'{API}/admin/tenantsettings/{n}/update', headers=H(), json={'enabled': on})
        say(n, 'on' if on else 'off', r.status_code, '' if r.ok else r.text[:200])
    say('tenant settings can take up to 15 minutes to reach the portal')


# ── workspace and items ──────────────────────────────────────────────────────
def capacity_id():
    for c in requests.get(f'{API}/capacities', headers=H()).json().get('value', []):
        if c['displayName'] == C['FABDEMO_CAPACITY']: return c['id']
    raise SystemExit('capacity not visible in Fabric yet, run: python3 fabdemo.py capacity create')


def ws_id(create=False):
    ws = next((w for w in requests.get(f'{API}/workspaces', headers=H()).json()['value'] if w['displayName'] == C['FABDEMO_WORKSPACE']), None)
    if ws: return ws['id']
    if not create: raise SystemExit(f"workspace {C['FABDEMO_WORKSPACE']} not found, run: python3 fabdemo.py workspace")
    r = requests.post(f'{API}/workspaces', headers=H(), json={'displayName': C['FABDEMO_WORKSPACE'], 'capacityId': capacity_id(),
                                                             'description': 'FabCon Europe 2026 recap demos. Synthetic data only.'})
    if not r.ok: raise SystemExit(f'workspace: {r.status_code} {r.text[:300]}')
    say('workspace created', C['FABDEMO_WORKSPACE']); return r.json()['id']


def workspace():
    ws = ws_id(create=True)
    requests.post(f'{API}/workspaces/{ws}/assignToCapacity', headers=H(), json={'capacityId': capacity_id()})
    say('workspace', C['FABDEMO_WORKSPACE'], ws); return ws


def items(ws, typ=None):
    v = requests.get(f'{API}/workspaces/{ws}/items', headers=H()).json()['value']
    return [i for i in v if typ is None or i['type'] == typ]


def item(ws, typ, name):
    return next((i for i in items(ws, typ) if i['displayName'] == name), None)


def lakehouse(ws, name=LH_NAME, schemas=False, desc='Oud house R&D demo, synthetic data'):
    lh = item(ws, 'Lakehouse', name)
    if lh: return lh['id']
    body = {'displayName': name, 'description': desc}
    if schemas: body['creationPayload'] = {'enableSchemas': True}
    lro(requests.post(f'{API}/workspaces/{ws}/lakehouses', headers=H(), json=body))
    for _ in range(10):
        lh = item(ws, 'Lakehouse', name)
        if lh: return lh['id']
        time.sleep(3)
    raise SystemExit(f'lakehouse {name} not visible')


def notebook(ws, name, cells, lh_id, lh_name, desc=''):
    ipynb = {'nbformat': 4, 'nbformat_minor': 5,
             'cells': [{'cell_type': 'code', 'execution_count': None, 'outputs': [], 'metadata': {}, 'source': [l + '\n' for l in c.strip('\n').split('\n')]} for c in cells],
             'metadata': {'language_info': {'name': 'python'}, 'kernelspec': {'name': 'synapse_pyspark', 'display_name': 'Synapse PySpark'},
                          'dependencies': {'lakehouse': {'default_lakehouse': lh_id, 'default_lakehouse_name': lh_name, 'default_lakehouse_workspace_id': ws}}}}
    definition = {'format': 'ipynb', 'parts': [{'path': 'artifact.content.ipynb', 'payload': b64(ipynb), 'payloadType': 'InlineBase64'}]}
    nb = item(ws, 'Notebook', name)
    if nb: lro(requests.post(f'{API}/workspaces/{ws}/notebooks/{nb["id"]}/updateDefinition', headers=H(), json={'definition': definition}))
    else:
        lro(requests.post(f'{API}/workspaces/{ws}/notebooks', headers=H(), json={'displayName': name, 'description': desc, 'definition': definition}))
        nb = item(ws, 'Notebook', name)
    say('notebook', name); return nb['id']


def run_job(ws, item_id, job_type, label, body=None):
    r = requests.post(f'{API}/workspaces/{ws}/items/{item_id}/jobs/instances', headers=H(), params={'jobType': job_type}, json=body or {})
    if r.status_code != 202: raise SystemExit(f'{label} run: {r.status_code} {r.text[:300]}')
    loc = r.headers['Location']; say(label, 'running')
    while True:
        time.sleep(15); s = requests.get(loc, headers=H()).json(); st = s.get('status')
        if st in ('Completed', 'Failed', 'Cancelled', 'Deduped'):
            say(label, st, (s.get('failureReason') or {}).get('message', '')[:300]); return st


# ── data: lakehouse, synthetic files, load notebook ──────────────────────────
def data():
    ws = workspace(); lid = lakehouse(ws); say('lakehouse', LH_NAME, lid)
    sh = {'Authorization': 'Bearer ' + token('https://storage.azure.com'), 'x-ms-version': '2023-11-03'}
    base = f'https://onelake.dfs.fabric.microsoft.com/{ws}/{lid}/Files/demo'
    files = [('data', p) for p in sorted((HERE / 'data').glob('*.csv'))] + [('docs', p) for p in sorted((HERE / 'docs').glob('*.pdf'))]
    for sub, p in files:
        url = f'{base}/{sub}/{p.name}'; body = p.read_bytes()
        requests.put(url, params={'resource': 'file'}, headers=sh).raise_for_status()
        requests.patch(url, params={'action': 'append', 'position': '0'}, headers={**sh, 'Content-Type': 'application/octet-stream'}, data=body).raise_for_status()
        requests.patch(url, params={'action': 'flush', 'position': str(len(body))}, headers=sh).raise_for_status()
    say('uploaded', len(files), 'files to Files/demo')
    src = (HERE / 'notebooks' / '01_load_demo.py').read_text()
    blocks, cur = [], []
    for line in src.splitlines():
        if line.startswith('# CELL'):
            if cur: blocks.append('\n'.join(cur).strip())
            cur = []
        else: cur.append(line)
    if cur: blocks.append('\n'.join(cur).strip())
    blocks = [b for b in blocks if b and not all(l.startswith('#') or not l.strip() for l in b.splitlines())]
    nb = notebook(ws, '01_load_demo', blocks, lid, LH_NAME, 'Loads the synthetic tables')
    st = run_job(ws, nb, 'RunNotebook', 'load notebook (about 4 minutes)',
                 # %pip install (pypdf, cell 2) is off in API runs unless _inlineInstallationEnabled is passed
                 {'executionData': {'parameters': {'_inlineInstallationEnabled': {'value': True, 'type': 'bool'}},
                                    'configuration': {'defaultLakehouse': {'name': LH_NAME, 'id': lid, 'workspaceId': ws}}}})
    if st != 'Completed':
        say('the load notebook did not complete. Open 01_load_demo in the workspace to see which cell failed, then rerun: python3 fabdemo.py data')


# ── semantic model (Direct Lake, TMDL) ───────────────────────────────────────
TYPES = {'string': 'string', 'double': 'double', 'integer': 'int64', 'date': 'dateTime'}
TABLES = {
    'formulas': ('Oud fragrance formulas. One row per formula, OB-101 to OB-106.',
                 [('formula_id', 'string'), ('formula_name', 'string'), ('line', 'string'), ('occasion', 'string'), ('status', 'string'), ('target_intensity', 'double'), ('created_date', 'date')]),
    'ingredients': ('Raw materials with cost in QAR per kg of concentrate and sensory indexes.',
                    [('ingredient_id', 'string'), ('ingredient_name', 'string'), ('category', 'string'), ('cost_qar_per_kg', 'integer'), ('intensity_index', 'double'), ('longevity_index', 'double'), ('freshness_index', 'double')]),
    'formula_ingredients': ('Share of each material in each formula. Inclusions of one formula sum to 100.',
                            [('formula_id', 'string'), ('ingredient_id', 'string'), ('inclusion_pct', 'double')]),
    'preference_trials': ('Paired blotter tests. first_choice_pct is the share of testers who chose the formula over the reference; above 50 means preferred.',
                          [('trial_id', 'string'), ('formula_id', 'string'), ('study_id', 'string'), ('panel_segment', 'string'), ('n_testers', 'integer'), ('first_choice_pct', 'double'), ('dwell_ratio', 'double'), ('trial_date', 'date'), ('panel_site', 'string')]),
    'formula_metrics': ('Computed cost and sensory indexes per formula.',
                        [('formula_id', 'string'), ('cost_qar_per_kg', 'double'), ('intensity_index', 'double'), ('longevity_index', 'double')]),
    'formula_optimization': ('Cost optimizer result per formula: baseline and optimized cost, saving, recommended changes.',
                             [('formula_id', 'string'), ('baseline_cost_qar_per_kg', 'double'), ('optimized_cost_qar_per_kg', 'double'), ('saving_pct', 'double'), ('baseline_intensity', 'double'), ('optimized_intensity', 'double'), ('recommended_changes', 'string'), ('method', 'string')]),
}
MEASURES = {
    'preference_trials': [('Avg first choice %', 'AVERAGE(preference_trials[first_choice_pct])', '0.0', 'Average share of testers who chose the formula first. Above 50 means preferred over the reference.'),
                          ('Testers', 'SUM(preference_trials[n_testers])', '0', 'Number of testers across trials.')],
    'formula_metrics': [('Avg cost QAR per kg', 'AVERAGE(formula_metrics[cost_qar_per_kg])', '#,0', 'Average cost of a formula in QAR per kg of concentrate.')],
    'formula_optimization': [('Avg saving %', 'AVERAGE(formula_optimization[saving_pct])', '0.0', 'Average cost saving proposed by the optimizer, in percent.')],
}
RELS = [('formula_ingredients', 'formula_id', 'formulas', 'formula_id'), ('formula_ingredients', 'ingredient_id', 'ingredients', 'ingredient_id'),
        ('preference_trials', 'formula_id', 'formulas', 'formula_id'), ('formula_metrics', 'formula_id', 'formulas', 'formula_id'),
        ('formula_optimization', 'formula_id', 'formulas', 'formula_id')]


def _q(n): return n if n.replace('_', '').isalnum() else "'" + n.replace("'", "''") + "'"


def _table_tmdl(t, desc, cols):
    L = [f'/// {desc}', f'table {_q(t)}', f'\tlineageTag: {uuid.uuid4()}', '']
    for name, dax, fmt, mdesc in MEASURES.get(t, []):
        L += [f'\t/// {mdesc}', f'\tmeasure {_q(name)} = {dax}', f'\t\tformatString: {fmt}', f'\t\tlineageTag: {uuid.uuid4()}', '']
    for c, ty in cols:
        L += [f'\tcolumn {_q(c)}', f'\t\tdataType: {TYPES[ty]}', f'\t\tlineageTag: {uuid.uuid4()}',
              f"\t\tsummarizeBy: {'none' if ty in ('string', 'date') or c.endswith('_id') else 'sum'}", f'\t\tsourceColumn: {c}', '']
    L += [f'\tpartition {_q(t)} = entity', '\t\tmode: directLake', '\t\tsource', f'\t\t\tentityName: {t}', '\t\t\texpressionSource: DatabaseQuery', '']
    return '\n'.join(L)


def model():
    ws = ws_id(); lid = lakehouse(ws)
    sql = requests.get(f'{API}/workspaces/{ws}/lakehouses/{lid}', headers=H()).json()['properties']['sqlEndpointProperties']
    parts = {
        'definition.pbism': json.dumps({'version': '4.0', 'settings': {}}),
        'definition/database.tmdl': 'database\n\tcompatibilityLevel: 1604\n',
        'definition/model.tmdl': 'model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n',
        'definition/expressions.tmdl': f'expression DatabaseQuery =\n\t\tlet\n\t\t    database = Sql.Database("{sql["connectionString"]}", "{sql["id"]}")\n\t\tin\n\t\t    database\n\tlineageTag: {uuid.uuid4()}\n',
        'definition/relationships.tmdl': '\n'.join(f'relationship {uuid.uuid4()}\n\tfromColumn: {_q(a)}.{_q(ac)}\n\ttoColumn: {_q(b)}.{_q(bc)}\n' for a, ac, b, bc in RELS),
    }
    for t, (desc, cols) in TABLES.items(): parts[f'definition/tables/{t}.tmdl'] = _table_tmdl(t, desc, cols)
    definition = {'format': 'TMDL', 'parts': [{'path': p, 'payload': b64(c), 'payloadType': 'InlineBase64'} for p, c in parts.items()]}
    sm = item(ws, 'SemanticModel', MODEL)
    if sm: lro(requests.post(f'{API}/workspaces/{ws}/semanticModels/{sm["id"]}/updateDefinition', headers=H(), json={'definition': definition}))
    else:
        lro(requests.post(f'{API}/workspaces/{ws}/semanticModels', headers=H(), json={'displayName': MODEL, 'description': 'Oud house R&D, synthetic data, Direct Lake on lh_oud_rd', 'definition': definition}))
        sm = item(ws, 'SemanticModel', MODEL)
    say('semantic model', MODEL, sm['id'])
    P = H('https://analysis.windows.net/powerbi/api'); base = f'https://api.powerbi.com/v1.0/myorg/groups/{ws}/datasets/{sm["id"]}'
    r = requests.post(f'{base}/refreshes', headers=P, json={'type': 'full'}); say('refresh', r.status_code)
    for _ in range(30):
        time.sleep(5); last = requests.get(f'{base}/refreshes?$top=1', headers=P).json().get('value', [{}])[0]
        if last.get('status') in ('Completed', 'Failed'): say('refresh', last.get('status')); break
    r = requests.post(f'{base}/executeQueries', headers=P, json={'queries': [{'query': 'EVALUATE SUMMARIZECOLUMNS(formulas[formula_name], "Avg first choice %", [Avg first choice %])'}]})
    rows = r.json()['results'][0]['tables'][0]['rows'] if r.ok else []
    say('check: average first choice by formula', {list(x.values())[0]: list(x.values())[1] for x in rows})


# ── eventhouse with synthetic blotter events ────────────────────────────────
EVENT_SCHEMA = 'event_time:datetime, study_id:string, trial_id:string, formula_id:string, tester_id:string, booth_id:string, panel_site:string, first_choice:string, dwell_test_s:real, dwell_reference_s:real'
FORMULA_SHARE = {'OB-101': .47, 'OB-102': .57, 'OB-103': .51, 'OB-104': .68, 'OB-105': .58, 'OB-106': .63}


def eventhouse():
    ws = ws_id(); eh = item(ws, 'Eventhouse', EH_NAME)
    if not eh:
        lro(requests.post(f'{API}/workspaces/{ws}/eventhouses', headers=H(), json={'displayName': EH_NAME, 'description': 'Live blotter tests, synthetic'}))
        time.sleep(5); eh = item(ws, 'Eventhouse', EH_NAME)
    uri = requests.get(f'{API}/workspaces/{ws}/eventhouses/{eh["id"]}', headers=H()).json()['properties']['queryServiceUri']
    K = {'Authorization': 'Bearer ' + token(uri), 'Content-Type': 'application/json'}
    def mgmt(csl):
        r = requests.post(f'{uri}/v1/rest/mgmt', headers=K, json={'db': EH_NAME, 'csl': csl})
        if not r.ok: raise SystemExit(f'{r.status_code} {r.text[:400]}')
    mgmt(f'.create-merge table blotter_events ({EVENT_SCHEMA})'); mgmt('.clear table blotter_events data')
    rng = random.Random(21); now = datetime.now(timezone.utc).replace(microsecond=0); rows, n = [], 0
    for f, p in FORMULA_SHARE.items():
        for _ in range(500):
            t = now - timedelta(seconds=rng.randint(0, 8 * 3600)); n += 1; test = rng.random() < p
            booth = f'BOOTH-{rng.randint(1, 4)}'; site = 'Panel A' if booth in ('BOOTH-1', 'BOOTH-2') else 'Panel C'
            ts, rs = (rng.uniform(95, 140), rng.uniform(50, 90)) if test else (rng.uniform(50, 90), rng.uniform(95, 140))
            rows.append(f"{t.isoformat().replace('+00:00', 'Z')},ST-16,TR-{2100 + list(FORMULA_SHARE).index(f)},{f},T-{n:05d},{booth},{site},{'test' if test else 'reference'},{ts:.1f},{rs:.1f}")
    for i in range(0, len(rows), 600): mgmt('.ingest inline into table blotter_events <|\n' + '\n'.join(rows[i:i + 600]))
    r = requests.post(f'{uri}/v1/rest/query', headers=K, json={'db': EH_NAME, 'csl': 'blotter_events | count'})
    say('eventhouse', EH_NAME, 'events:', r.json()['Tables'][0]['Rows'][0][0] if r.ok else r.status_code)


# ── a pipeline that fails for a realistic reason (operations agent demo) ─────
def pipeline():
    ws = ws_id(); lid = lakehouse(ws)
    code = ["# Daily load: append yesterday's preference trials from the landing zone",
            "landing = 'Files/landing/trials/2026-10-18/preference_trials_daily.csv'",
            "df = spark.read.option('header', True).option('inferSchema', True).csv(landing)",
            "df.write.mode('append').saveAsTable('preference_trials')", "print('rows appended:', df.count())"]
    nb = notebook(ws, '03_load_daily_trials', ['\n'.join(code)], lid, LH_NAME, 'Daily load, fails on purpose: the landing file never arrives')
    content = {'properties': {'activities': [{'name': 'Load daily trials', 'type': 'TridentNotebook', 'dependsOn': [],
               'policy': {'timeout': '0.01:00:00', 'retry': 0, 'retryIntervalInSeconds': 30}, 'typeProperties': {'notebookId': nb, 'workspaceId': ws}}]}}
    definition = {'parts': [{'path': 'pipeline-content.json', 'payload': b64(content), 'payloadType': 'InlineBase64'}]}
    pl = item(ws, 'DataPipeline', 'pl_daily_trials_load')
    if pl: lro(requests.post(f'{API}/workspaces/{ws}/dataPipelines/{pl["id"]}/updateDefinition', headers=H(), json={'definition': definition}))
    else:
        lro(requests.post(f'{API}/workspaces/{ws}/dataPipelines', headers=H(), json={'displayName': 'pl_daily_trials_load', 'description': 'Daily trials load (demo, fails on purpose)', 'definition': definition}))
        pl = item(ws, 'DataPipeline', 'pl_daily_trials_load')
    run_job(ws, pl['id'], 'Pipeline', 'pipeline pl_daily_trials_load (expected: Failed)')


# ── showcase items: AI functions notebook, materialized lake views, data agent ─
TXT = {
    'en': dict(c1='# Tester comments from the Doha panel (synthetic data): English, Arabic, French', rt='# Runtime 2.0: model set explicitly (Learn, temporary)',
               df='comments', res='result', c2='# One line per AI function: translation, sentiment, topic', to='english', tcol='comment_en', scol='sentiment',
               labels=['scent note', 'longevity', 'sweetness', 'no difference'], ccol='topic', done='done:', unit='comments',
               b1='# Bronze: raw preference trials and formulas from lh_oud_rd', rows='rows', s1='-- Silver: quality rules live in the view definition, bad rows are dropped',
               g1='-- Gold: preference per formula, Fabric knows to refresh silver first',
               n1='# New delivery from the panel: three rows break the quality rules (share 140, no formula, zero testers)', n2='print("appended to bronze:", bad.count(), "bad rows")',
               agent='Formula agent', adesc='Questions about oud formulas, synthetic data',
               ai='Answer in English, briefly. The data is synthetic preference trials of oud perfumes from a panel in Doha. first_choice_pct is the share of testers who picked the formula over the reference: above 50 means the formula wins. Formulas are in the formulas table, costs in formula_metrics, trials in preference_trials. Start with one sentence that names the formula and the numbers. When the question asks for a table, answer with a table and no chart. Show a chart only when the user asks for one.'),
    'pl': dict(c1='# Komentarze testerów z panelu w Doha (dane syntetyczne): angielski, arabski, francuski', rt='# Runtime 2.0: model ustawiony jawnie (Learn, tymczasowo)',
               df='komentarze', res='wynik', c2='# Jedna linijka na funkcję AI: tłumaczenie, sentyment, temat', to='polish', tcol='komentarz_pl', scol='sentyment',
               labels=['nuta zapachowa', 'trwałość', 'słodycz', 'brak różnicy'], ccol='temat', done='gotowe:', unit='komentarzy',
               b1='# Brąz: surowe testy preferencji i receptury z lh_oud_rd', rows='wierszy', s1='-- Srebro: reguły jakości w definicji widoku, błędne wiersze odpadają',
               g1='-- Złoto: preferencja per receptura, Fabric sam wie, że najpierw odświeża srebro',
               n1='# Nowa dostawa z panelu: trzy wiersze łamią reguły jakości (odsetek 140, brak receptury, zero testerów)', n2='print("dopisane do brązu:", bad.count(), "wiersze z błędami")',
               agent='Agent receptur', adesc='Pytania o receptury oud, dane syntetyczne',
               ai='Odpowiadaj po polsku, krótko. Dane to syntetyczne testy preferencji perfum oud z panelu w Doha. first_choice_pct to odsetek testerów, którzy wybrali recepturę zamiast wzorca: powyżej 50 znaczy, że receptura wygrywa. Receptury opisuje tabela formulas, koszty formula_metrics, testy preference_trials. Gdy pytanie dotyczy porównania, pokaż wykres.'),
    'de': dict(c1='# Kommentare der Testpersonen aus dem Panel in Doha (synthetische Daten): Englisch, Arabisch, Französisch', rt='# Runtime 2.0: Modell explizit gesetzt (Learn, vorübergehend)',
               df='kommentare', res='ergebnis', c2='# Eine Zeile pro KI-Funktion: Übersetzung, Stimmung, Thema', to='german', tcol='kommentar_de', scol='stimmung',
               labels=['Duftnote', 'Haltbarkeit', 'Süsse', 'kein Unterschied'], ccol='thema', done='fertig:', unit='Kommentare',
               b1='# Bronze: rohe Präferenztests und Rezepturen aus lh_oud_rd', rows='Zeilen', s1='-- Silber: Qualitätsregeln stehen in der View-Definition, fehlerhafte Zeilen fallen weg',
               g1='-- Gold: Präferenz pro Rezeptur, Fabric weiss selbst, dass zuerst Silber aktualisiert wird',
               n1='# Neue Lieferung vom Panel: drei Zeilen verletzen die Qualitätsregeln (Anteil 140, keine Rezeptur, null Testpersonen)', n2='print("an Bronze angehängt:", bad.count(), "fehlerhafte Zeilen")',
               agent='Rezeptur-Agent', adesc='Fragen zu Oud-Rezepturen, synthetische Daten',
               ai='Antworte auf Deutsch, kurz. Die Daten sind synthetische Präferenztests für Oud-Parfums aus einem Panel in Doha. first_choice_pct ist der Anteil der Testpersonen, die die Rezeptur statt der Referenz gewählt haben: über 50 heisst, die Rezeptur gewinnt. Rezepturen stehen in der Tabelle formulas, Kosten in formula_metrics, Tests in preference_trials. Beginne mit einem Satz, der die Rezeptur und die Zahlen nennt. Wenn nach einer Tabelle gefragt wird, antworte mit einer Tabelle und ohne Diagramm. Zeig ein Diagramm nur, wenn danach gefragt wird.'),
}
COMMENTS = [('OB-104', 'The opening is smoky and rich, I would wear this to a wedding.'), ('OB-101', 'Too sweet after an hour, the rose disappears.'),
            ('OB-106', 'رائحة العود قوية وثابتة، أحببتها كثيراً'), ('OB-103', 'Nice but nothing special compared to the reference.'),
            ('OB-102', 'الافتتاحية حادة جداً، تحتاج إلى نعومة أكثر'), ('OB-104', 'The saffron note is beautiful and lasts all day on the skin.'),
            ('OB-105', 'لا أشعر بأي فرق عن العطر المرجعي'), ('OB-106', 'Le bois de oud est magnifique, très élégant.')]


def showcase(what, lang):
    L = TXT[lang]; ws = ws_id(); lid = lakehouse(ws)
    if what == 'aifunc':
        rows = ',\n'.join(f'    ({json.dumps(f)}, {json.dumps(c, ensure_ascii=False)})' for f, c in COMMENTS)
        c1 = f'''{L['c1']}
import warnings; warnings.filterwarnings("ignore")
import synapse.ml.spark.aifunc as aifunc
aifunc.default_conf.set_deployment_name("gpt-5-mini")   {L['rt']}
aifunc.default_conf.set_reasoning_effort("low")
aifunc.default_conf.reset_temperature()

{L['df']} = spark.createDataFrame([
{rows}
], ["formula_id", "comment"])
display({L['df']})'''
        c2 = f'''{L['c2']}
{L['res']} = ({L['df']}
    .ai.translate(to_lang="{L['to']}", input_col="comment", output_col="{L['tcol']}")
    .ai.analyze_sentiment(input_col="comment", output_col="{L['scol']}")
    .ai.classify(input_col="comment", labels={json.dumps(L['labels'], ensure_ascii=False)}, output_col="{L['ccol']}"))

{L['res']}.select("formula_id", "{L['tcol']}", "{L['scol']}", "{L['ccol']}").show(truncate=False)
print("{L['done']}", {L['res']}.count(), "{L['unit']}")'''
        return notebook(ws, '04_ai_functions', [c1, c2], lid, LH_NAME, 'AI functions on synthetic tester comments')
    if what == 'mlv':
        mid = lakehouse(ws, LH_MLV, schemas=True, desc='Medallion with materialized lake views, synthetic')
        c1 = f'''{L['b1']}
from pyspark.sql import functions as F
src = "abfss://{ws}@onelake.dfs.fabric.microsoft.com/{lid}/Tables/"
for s in ("bronze", "silver", "gold"): spark.sql(f"CREATE SCHEMA IF NOT EXISTS {{s}}")
spark.read.format("delta").load(src + "preference_trials").write.mode("overwrite").saveAsTable("bronze.preference_trials")
spark.read.format("delta").load(src + "formulas").write.mode("overwrite").saveAsTable("bronze.formulas")
print("bronze.preference_trials:", spark.table("bronze.preference_trials").count(), "{L['rows']}")'''
        c2 = '%%sql\n' + L['s1'] + '''
CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.trials_clean
(
  CONSTRAINT pct_valid   CHECK (first_choice_pct BETWEEN 0 AND 100) ON MISMATCH DROP,
  CONSTRAINT has_formula CHECK (formula_id IS NOT NULL)             ON MISMATCH DROP,
  CONSTRAINT has_testers CHECK (n_testers > 0)                      ON MISMATCH DROP
)
AS SELECT trial_id, formula_id, panel_segment, n_testers, first_choice_pct, trial_date
FROM bronze.preference_trials'''
        c3 = '%%sql\n' + L['g1'] + '''
CREATE OR REPLACE MATERIALIZED LAKE VIEW gold.formula_preference
AS SELECT f.formula_id, f.formula_name, COUNT(*) AS trials, SUM(t.n_testers) AS testers,
          ROUND(AVG(t.first_choice_pct), 1) AS avg_first_choice_pct
FROM silver.trials_clean t JOIN bronze.formulas f ON t.formula_id = f.formula_id
GROUP BY f.formula_id, f.formula_name'''
        c4 = '%%sql\nSELECT * FROM gold.formula_preference ORDER BY avg_first_choice_pct DESC'
        c5 = L['n1'] + '''
one = spark.table("bronze.preference_trials").limit(1)
bad = (one.withColumn("first_choice_pct", F.lit(140.0))
       .unionByName(one.withColumn("formula_id", F.lit(None).cast("string")))
       .unionByName(one.withColumn("n_testers", F.lit(0).cast(one.schema["n_testers"].dataType))))
bad.write.mode("append").saveAsTable("bronze.preference_trials")
''' + L['n2']
        return notebook(ws, '05_mlv_medallion', [c1, c2, c3, c4, c5], mid, LH_MLV, 'Medallion with materialized lake views')
    if what == 'agent':
        stage = {'$schema': '1.0.0', 'aiInstructions': L['ai']}
        # the source tree as the portal writes it (Schemas > dbo > Tables > columns), five tables selected.
        # updateDefinition replaces every part, so the source travels with the definition.
        source = {'$schema': '1.0.0', 'artifactId': lid, 'workspaceId': ws, 'displayName': LH_NAME, 'type': 'lakehouse_tables',
                  'elements': [json.loads((HERE / 'agent_source.json').read_text())]}
        parts = [{'path': 'Files/Config/data_agent.json', 'payload': b64({'$schema': '2.1.0'}), 'payloadType': 'InlineBase64'},
                 {'path': 'Files/Config/draft/stage_config.json', 'payload': b64(stage), 'payloadType': 'InlineBase64'},
                 {'path': f'Files/Config/draft/lakehouse-tables-{LH_NAME}/datasource.json', 'payload': b64(source), 'payloadType': 'InlineBase64'}]
        ag = next((i for i in items(ws, 'DataAgent') if i['displayName'] in {t['agent'] for t in TXT.values()}), None)
        if ag:
            requests.patch(f'{API}/workspaces/{ws}/items/{ag["id"]}', headers=H(), json={'displayName': L['agent'], 'description': L['adesc']}).raise_for_status()
            lro(requests.post(f'{API}/workspaces/{ws}/dataAgents/{ag["id"]}/updateDefinition', headers=H(), json={'definition': {'parts': parts}}))
        else:
            lro(requests.post(f'{API}/workspaces/{ws}/dataAgents', headers=H(), json={'displayName': L['agent'], 'description': L['adesc'], 'definition': {'parts': parts}}))
        return say('data agent', L['agent'])


# ── scripted demos ───────────────────────────────────────────────────────────
def catalog_search(text, types=None):
    body = {'search': text, 'pageSize': 20}
    if types: body['filter'] = ' or '.join(f"Type eq '{t}'" for t in types.split(','))
    r = requests.post(f'{API}/catalog/search', headers=H(), json=body)
    if not r.ok: raise SystemExit(f'{r.status_code} {r.text[:400]}')
    rows = r.json().get('value', [])
    print(f'POST /v1/catalog/search  search={text!r}' + (f'  filter: {types}' if types else '') + f'  -> {len(rows)} hits')
    for e in rows: print(f"  {e['type']:<14} {e['displayName'][:30]:<30} {(e.get('description') or '')[:40]}")


def table_read(table, cols=None):
    import pyarrow as pa
    ws = ws_id(); lid = lakehouse(ws)
    B = f'https://onelake.table.fabric.microsoft.com/v1.0/workspaces/{ws}/items/{lid}/tables/{table}'
    S = H('https://storage.azure.com')
    r = requests.post(B + '/read', headers=S, json={'columns': cols.split(',')} if cols else {}); r.raise_for_status()
    streams = r.json()['streams']; parts = []
    for s in streams:
        g = requests.get(f"{B}/readStream/{s['streamId']}", headers=S, stream=True); g.raise_for_status()
        parts.append(pa.ipc.open_stream(g.raw.read()).read_all())
    t = pa.concat_tables(parts)
    print(f'POST /read -> {len(streams)} stream(s), Apache Arrow, {t.num_rows} rows, columns: {", ".join(t.column_names)}')
    for row in t.to_pylist(): print('  ' + '  '.join(f'{str(v):<16}' for v in row.values()))


def open_catalogs(mode, table=None):
    ws = ws_id(); lid = lakehouse(ws); S = H('https://storage.azure.com'); base = 'https://onelake.table.fabric.microsoft.com'
    def get(path, **params):
        r = requests.get(base + path, headers=S, params=params)
        if not r.ok: raise SystemExit(f'GET {path} -> {r.status_code} {r.text[:300]}')
        return r.json()
    if mode == 'uc':
        p = f'/delta/{ws}/{lid}/api/2.1/unity-catalog'
        if not table:
            s = get(p + '/schemas', catalog_name=lid); print(f"GET .../unity-catalog/schemas -> {[x['name'] for x in s.get('schemas', [])]}")
            t = get(p + '/tables', catalog_name=lid, schema_name='dbo'); print(f"GET .../unity-catalog/tables?schema_name=dbo -> {len(t.get('tables', []))} tables")
            for x in t.get('tables', []): print(f"  {x['name']:<22} {x.get('table_type') or '':<9} {x.get('data_source_format') or ''}")
        else:
            x = get(f'{p}/tables/{lid}.dbo.{table}')
            print(f"GET .../unity-catalog/tables/dbo.{table} -> {x.get('data_source_format')}, {len(x.get('columns', []))} columns")
            for c in x.get('columns', []): print(f"  {c['name']:<20} {c.get('type_name', c.get('type_text', ''))}")
    else:
        cfg = get('/iceberg/v1/config', warehouse=f'{ws}/{lid}')
        prefix = cfg.get('overrides', {}).get('prefix') or cfg.get('defaults', {}).get('prefix')
        print(f'GET /iceberg/v1/config -> prefix {prefix[:16]}...')
        if not table:
            print(f"GET .../namespaces -> {get(f'/iceberg/v1/{prefix}/namespaces').get('namespaces')}")
            t = get(f'/iceberg/v1/{prefix}/namespaces/dbo/tables'); print(f"GET .../namespaces/dbo/tables -> {[x['name'] for x in t.get('identifiers', [])]}")
        else:
            x = get(f'/iceberg/v1/{prefix}/namespaces/dbo/tables/{table}'); m = x.get('metadata', {})
            sch = next((s for s in m.get('schemas', []) if s.get('schema-id') == m.get('current-schema-id')), (m.get('schemas') or [{}])[-1])
            print(f"GET .../tables/{table} -> Iceberg format-version {m.get('format-version')}, {len(sch.get('fields', []))} fields, snapshots {len(m.get('snapshots', []))}")
            for f in sch.get('fields', []): print(f"  {f['id']:>2} {f['name']:<20} {f['type']}")


def _mcp(url):
    MH = {**H(), 'Accept': 'application/json, text/event-stream'}
    def rpc(method, params=None, i=1):
        r = requests.post(url, headers=MH, json={'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params or {}})
        m = re.findall(r'^data: (.*)$', r.text, re.M); return json.loads(m[-1] if m else r.text)
    init = rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'fabdemo', 'version': '1'}})
    return rpc, init


def core_mcp(cmd='tools', tool=None, args=None):
    rpc, init = _mcp(f'{API}/mcp/core')
    if cmd == 'init':
        s = init['result']['serverInfo']; print(f"{s['name']} {s['version']}  protocol {init['result']['protocolVersion']}")
    elif cmd == 'tools':
        tools = rpc('tools/list', i=2)['result']['tools']
        ro = [t['name'] for t in tools if (t.get('annotations') or {}).get('readOnlyHint')]; rw = [t['name'] for t in tools if t['name'] not in ro]
        print(f'{len(tools)} tools: {len(ro)} read-only, {len(rw)} write'); print('write:', ', '.join(rw))
    else:
        res = rpc('tools/call', {'name': tool, 'arguments': json.loads(args) if args else {}}, i=3)['result']
        txt = (res.get('content') or [{}])[0].get('text', '')
        try:
            data = json.loads(txt); rows = data.get('value', data if isinstance(data, list) else [data])
            for w in rows: print(f"  {w.get('displayName', w.get('name', '?')):<24} {w.get('type', '')}")
        except Exception: print(txt[:800])


def iq_mcp(cmd='tools', a=None, b=None):
    rpc, _ = _mcp('https://fabriciq.svc.cloud.microsoft/v1/mcp/FabricIQ')
    def call(name, args):
        txt = rpc('tools/call', {'name': name, 'arguments': args}, 3)['result']['content'][0]['text']
        try: return json.loads(txt)
        except Exception: return txt
    if cmd == 'tools':
        tools = rpc('tools/list', i=2)['result']['tools']; print(f"{len(tools)} tools, read-only server:", ', '.join(t['name'] for t in tools))
    elif cmd == 'discover':
        for x in call('DiscoverArtifacts', {'searchQuery': a})['artifacts'][:5]:
            print(f"  {x['Name']:<14} {x['ArtifactType']:<15} {x['WorkspaceName']:<24} {x['relevance']}")
    elif cmd == 'dax':
        arts = call('DiscoverArtifacts', {'searchQuery': a})['artifacts']
        mid = next(x['ArtifactId'] for x in arts if x['Name'] == a and x['ArtifactType'] == 'Semantic Model' and x['WorkspaceName'] == C['FABDEMO_WORKSPACE'])
        t = call('ExecuteQuery', {'artifactId': mid, 'daxQueries': [b]})['executionResult']['tables'][0]
        print('  ' + '  '.join(f"{c['name']:<18}" for c in t['columns']))
        for r in t['rows']: print('  ' + '  '.join(f'{str(v):<18}' for v in r))


# ── overview and teardown ────────────────────────────────────────────────────
def status():
    capacity('status')
    try: ws = ws_id()
    except SystemExit as e: return print(e)
    for i in items(ws): print(f"  {i['type']:<16} {i['displayName']}")


def down(with_capacity):
    try:
        ws = ws_id(); r = requests.delete(f'{API}/workspaces/{ws}', headers=H()); say('workspace delete', C['FABDEMO_WORKSPACE'], r.status_code)
    except SystemExit as e: print(e)
    if with_capacity: capacity('delete')
    else: say('capacity kept. Pause it with: python3 fabdemo.py capacity pause, or delete it with: python3 fabdemo.py down --capacity')


def main(argv):
    global C
    if not argv or argv[0] in ('-h', '--help', 'help'): return print(__doc__)
    lang = 'en'
    if '--lang' in argv: i = argv.index('--lang'); lang = argv[i + 1]; del argv[i:i + 2]
    flags = {a for a in argv if a.startswith('--')}; argv = [a for a in argv if not a.startswith('--')]
    C = config(); lang = lang if lang != 'en' or '--lang' in flags else C.get('FABDEMO_LANG', 'en')
    cmd, rest = argv[0], argv[1:]
    if cmd == 'up':
        capacity('create'); data(); model(); eventhouse(); pipeline()
        for w in ('aifunc', 'mlv', 'agent'): showcase(w, lang)
        say('ready. Next: open the workspace in Fabric and follow runbooks/. Pause the capacity when you are done.')
    elif cmd == 'capacity': capacity(rest[0] if rest else 'status')
    elif cmd == 'settings': settings(rest[0] == 'on', '--yes' in flags)
    elif cmd in ('workspace', 'data', 'model', 'eventhouse', 'pipeline', 'status'): globals()[cmd]()
    elif cmd == 'showcase': showcase(rest[0], lang)
    elif cmd == 'down': down('--capacity' in flags)
    elif cmd == 'catalog-search': catalog_search(*rest)
    elif cmd == 'table-read': table_read(*rest)
    elif cmd in ('uc', 'irc'): open_catalogs(cmd, *rest)
    elif cmd == 'core-mcp': core_mcp(*rest)
    elif cmd == 'iq-mcp': iq_mcp(*rest)
    else: raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
