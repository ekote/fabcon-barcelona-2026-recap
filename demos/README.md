# Run the FabCon Europe 2026 demos in your own Fabric tenant

This folder rebuilds the demo environment behind the 18 product recordings in this repo, in a Microsoft Fabric tenant you control. One script creates the capacity, the workspace, and every item the demos use. One page per demo tells you what to type or click and what you should see.

Everything is synthetic: an invented oud perfume house in Doha with six formulas, twelve raw materials priced in QAR, paired blotter tests, and five study reports in English and French. No real company, person, or customer data.

## What `up` builds

| Item | Type | Used by |
|---|---|---|
| `lh_oud_rd` | Lakehouse with 10 tables and the raw CSV and PDF files | D05, D10, D14, D17, D18 |
| `01_load_demo` | Notebook that loads the tables | setup |
| `Oud RnD` | Direct Lake semantic model, 6 tables, 5 relationships, 4 measures | D02, D03, D08 |
| `eh_oud_trials` | Eventhouse with 3,000 blotter test events | D09 |
| `pl_daily_trials_load` | Pipeline that fails on purpose | D07 |
| `04_ai_functions` | Notebook with AI functions | D15 |
| `05_mlv_medallion`, `lh_oud_mlv` | Notebook and schema-enabled lakehouse for materialized lake views | D16 |
| Formula agent | Data agent on `lh_oud_rd` | D17 |

D01, D04, D06, D11, D12, and D13 work on any tenant and need no extra items.

## Before you start

- **A test tenant.** Five demos need preview tenant settings. Turn them on only where that is allowed.
- **A Fabric administrator** to turn on the settings, or someone who does it for you. See the table below.
- **An Azure subscription** where you can create a Fabric capacity, with quota for 8 capacity units in your region.
- **Python 3.9 or later** and the **Azure CLI**, signed in with `az login` to the same tenant.
- **Copilot and AI in Fabric.** The setting "Users can use Copilot, AI Agents and other AI experiences powered by Azure OpenAI" must be on. It is on by default. Capacities outside the US and the EU Data Boundary also need the cross-geo processing settings.

## What it costs

The demos run on an F8 capacity. In France Central, the Azure retail price was 0.176 EUR per capacity unit hour on October 21, 2026, so F8 costs about 1.41 EUR per hour while it runs. `up` prints the current price for your region. A paused capacity costs nothing, but OneLake storage is billed separately. The data here is under 1 MB.

## Quick start

```bash
cd demos
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.env config.env      # then edit: subscription, resource group, capacity name, your sign-in
az login

python3 fabdemo.py settings on --yes  # test tenant only, see the table below
python3 fabdemo.py up                 # about 10 minutes, unattended
python3 fabdemo.py status

# ... run the demos from runbooks/ ...

python3 fabdemo.py capacity pause     # stop paying for compute
```

`up --lang pl` or `up --lang de` builds the notebooks and the data agent in Polish or German, like the Polish and German recordings. Rerun one step with `python3 fabdemo.py showcase agent --lang de`.

## The demos

| ID | Demo | Slide | How |
|---|---|---|---|
| [D01](runbooks/D01.md) | The "Fabric data in Microsoft Copilot" setting | 8 | portal |
| [D02](runbooks/D02.md) | The AI setting on a semantic model | 8 | portal |
| [D03](runbooks/D03.md) | Fabric IQ MCP server | 11 | script |
| [D04](runbooks/D04.md) | Fabric Core MCP server | 11 | script |
| [D05](runbooks/D05.md) | OneLake Table Read API | 12 | script |
| [D06](runbooks/D06.md) | Project Osmos, the data engineering agent | 13 | coding agent |
| [D07](runbooks/D07.md) | Operations agent investigates a failed pipeline | 14 | portal |
| [D08](runbooks/D08.md) | Ontology agent in Fabric IQ | 15 | portal |
| [D09](runbooks/D09.md) | Copilot generates a Real-Time Dashboard | 16 | portal |
| [D10](runbooks/D10.md) | OneLake security roles | 17 | portal |
| [D11](runbooks/D11.md) | Outbound access protection | 17 | portal |
| [D12](runbooks/D12.md) | Policies in Fabric | 18 | portal |
| [D13](runbooks/D13.md) | OneLake catalog Govern | 18 | portal |
| [D14](runbooks/D14.md) | OneLake catalog search API | 26 | script |
| [D15](runbooks/D15.md) | AI functions in a PySpark notebook | 27 | portal |
| [D16](runbooks/D16.md) | Materialized lake views with data quality rules | 28 | portal |
| [D17](runbooks/D17.md) | Fabric data agent answers from a lakehouse | 29 | portal |
| [D18](runbooks/D18.md) | OneLake table APIs: Unity Catalog and Iceberg REST | 30 | script |

Not reproducible here: Fabric IQ in Microsoft 365 Copilot Chat (needs a Microsoft 365 Copilot license), the data agent in Copilot Studio (needs Copilot Studio), database agents (not shipped yet), and agentic apps in Power BI Desktop (not shipped yet).

## Tenant settings

`settings on --yes` turns these on, `settings off --yes` turns them off again. They apply to the whole tenant and can take 15 minutes to reach the portal.

| Setting in the admin portal | API name | Needed by |
|---|---|---|
| Users can create Ontology (preview) items | `OntologyPreview` | D08 |
| Policies (preview) | `PolicySetTenantSwitch` | D12 |
| Users can use the Power BI Model Context Protocol server endpoints (preview) | `PowerBIMCP` | D03 |
| Users can create Monitoring items (preview) | `MonitoringTenant` | D07 |
| Configure workspace-level outbound network rules | `WorkspaceBlockOutboundAccess` | D11 |

## Clean up

```bash
python3 fabdemo.py down              # deletes the workspace, keeps the capacity
python3 fabdemo.py down --capacity   # also deletes the capacity
python3 fabdemo.py settings off --yes
```

## Files

| Path | What |
|---|---|
| `fabdemo.py` | The command line: environment, demo commands, teardown |
| `config.example.env` | Settings template, copy to `config.env` |
| `data/`, `docs/` | Synthetic tables as CSV and five study reports as PDF |
| `build_demo_assets.py` | Regenerates `data/`, `docs/`, and `EXPECTED-ANSWERS.md` |
| `notebooks/01_load_demo.py` | The load notebook, one `# CELL` block per notebook cell |
| `agent_source.json` | The data agent's table selection, as the Fabric portal writes it |
| `EXPECTED-ANSWERS.md` | The numbers behind every answer, to check agents against |
| `runbooks/` | One page per demo |

## Verified

On October 21, 2026, a clean copy of this folder ran against a new workspace:

- `up` finished in 9 minutes with every item in the table above.
- All scripted demos (D03, D04, D05, D14, D18) printed the outputs shown in their runbooks.
- The load, AI functions, and materialized lake view notebooks completed as jobs.
- The pipeline failed as designed, on the missing landing file.
- The data agent answered the first D17 question correctly in 18 seconds.

The portal-only steps match the recordings, which were made on the same items. Fabric changes fast, so portal labels can move. When a step stops matching, the Learn link on each runbook has the current wording.

## License

The code in this folder (`fabdemo.py`, `build_demo_assets.py`, `notebooks/`) is under the [MIT License](LICENSE). The runbooks and the synthetic data follow the rest of the repo: [CC BY 4.0](../LICENSE), with credit as described in [NOTICE.md](../NOTICE.md).
