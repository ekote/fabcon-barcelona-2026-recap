"""Build the synthetic demo dataset for the Fabric IQ and Real-Time Intelligence community session.

Everything here is SYNTHETIC. No customer data. The house, the formulas, the
materials, and all numbers are invented. Output: data/*.csv, docs/*.pdf,
EXPECTED-ANSWERS.md.

Domain: an oud fragrance house. Six oud formulas, twelve raw materials priced in
QAR per kg of concentrate, paired blotter tests with consumer panels, five study
reports (three English, two French), and a deterministic cost optimizer.

Usage:
    python build_demo_assets.py
"""
from pathlib import Path
import itertools

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).parent
DATA, DOCS, TMP = ROOT / "data", ROOT / "docs", ROOT / "_tmp"
for d in (DATA, DOCS, TMP):
    d.mkdir(exist_ok=True)

# ---------------------------------------------------------------- structured
# Indices are 0 to 100 and unit free. intensity = projection, longevity = hours on skin,
# freshness = brightness of the opening. Cost is QAR per kg of material.
ingredients = pd.DataFrame(
    [
        ("ING-01", "Assam oud oil", "oud", 14500, 65.0, 12.0, 2.0),
        ("ING-02", "Cambodian oud oil", "oud", 21000, 68.0, 10.0, 1.0),
        ("ING-03", "Synthetic oud accord", "oud", 10500, 78.0, 2.0, 3.0),
        ("ING-04", "Plantation oud oil", "oud", 32000, 58.0, 14.0, 7.0),
        ("ING-05", "Musk base", "base", 4200, 7.0, 1.0, 1.0),
        ("ING-06", "Amber accord", "base", 2800, 8.0, 4.0, 2.0),
        ("ING-07", "Bergamot oil", "top", 3500, 9.0, 1.0, 18.0),
        ("ING-08", "Sandalwood base", "fixative", 9500, 0.0, 99.0, 0.0),
        ("ING-09", "Labdanum absolute", "fixative", 26000, 0.0, 99.0, 0.0),
        ("ING-10", "Saffron absolute S-7", "booster", 48000, 14.0, 6.0, 0.0),
        ("ING-11", "Cardamom extract S-3", "booster", 31000, 45.0, 2.0, 1.0),
        ("ING-12", "Ambergris tincture", "precious", 55000, 0.0, 0.0, 0.0),
    ],
    columns=["ingredient_id", "ingredient_name", "category", "cost_qar_per_kg",
             "intensity_index", "longevity_index", "freshness_index"],
)

formulas = pd.DataFrame(
    [
        ("OB-101", "Oud Classic", "gulf", "evening", "commercial", 23.0, "2025-03-10"),
        ("OB-102", "Oud Rose", "gulf", "evening", "commercial", 22.5, "2025-06-02"),
        ("OB-103", "Oud Amber", "export", "evening", "commercial", 31.0, "2025-04-18"),
        ("OB-104", "Oud Saffron S-7", "export", "evening", "pilot", 32.0, "2026-01-22"),
        ("OB-105", "Oud Plantation", "gulf", "evening", "pilot", 24.0, "2026-02-14"),
        ("OB-106", "Oud Daylight", "gulf", "daytime", "concept", 22.0, "2026-05-05"),
    ],
    columns=["formula_id", "formula_name", "line", "occasion", "status",
             "target_intensity", "created_date"],
)

comp = {
    "OB-101": {"ING-01": 28, "ING-05": 38, "ING-06": 14, "ING-07": 5, "ING-08": 10, "ING-11": 2, "ING-12": 3},
    "OB-102": {"ING-02": 27, "ING-05": 36, "ING-06": 14, "ING-07": 5, "ING-09": 6, "ING-08": 6, "ING-10": 1.5, "ING-12": 4.5},
    "OB-103": {"ING-01": 42, "ING-05": 28, "ING-06": 8, "ING-07": 4, "ING-08": 13, "ING-11": 2, "ING-12": 3},
    "OB-104": {"ING-02": 30, "ING-01": 13, "ING-05": 27, "ING-06": 8, "ING-07": 4, "ING-09": 5, "ING-08": 8, "ING-10": 2, "ING-12": 3},
    "OB-105": {"ING-04": 22, "ING-03": 10, "ING-05": 36, "ING-06": 12, "ING-07": 6, "ING-08": 9, "ING-11": 2, "ING-12": 3},
    "OB-106": {"ING-01": 20, "ING-03": 6, "ING-05": 40, "ING-06": 14, "ING-07": 10, "ING-08": 5, "ING-11": 2, "ING-12": 3},
}
formula_ingredients = pd.DataFrame(
    [(f, i, p) for f, d in comp.items() for i, p in d.items()],
    columns=["formula_id", "ingredient_id", "inclusion_pct"],
)
assert all(abs(sum(d.values()) - 100) < 1e-6 for d in comp.values()), "inclusions must sum to 100"

trials = pd.DataFrame(
    [
        ("TR-2001", "OB-101", "ST-11", "gulf", 36, 48.0, 0.49, "2025-09-12", "Panel A"),
        ("TR-2002", "OB-102", "ST-11", "gulf", 36, 57.0, 0.58, "2025-09-12", "Panel A"),
        ("TR-2003", "OB-103", "ST-12", "export", 40, 51.0, 0.52, "2025-11-03", "Panel B"),
        ("TR-2004", "OB-104", "ST-12", "export", 40, 68.0, 0.71, "2026-02-20", "Panel B"),
        ("TR-2005", "OB-105", "ST-13", "gulf", 32, 44.0, 0.45, "2026-03-15", "Panel A"),
        ("TR-2006", "OB-105", "ST-14", "gulf", 32, 61.0, 0.63, "2026-06-09", "Panel A"),
        ("TR-2007", "OB-106", "ST-15", "gulf", 30, 53.0, 0.54, "2026-07-01", "Panel C"),
    ],
    columns=["trial_id", "formula_id", "study_id", "panel_segment", "n_testers",
             "first_choice_pct", "dwell_ratio", "trial_date", "panel_site"],
)

ing = ingredients.set_index("ingredient_id")


def metrics(d):
    cost = sum(p * ing.loc[i, "cost_qar_per_kg"] for i, p in d.items()) / 100
    inten = sum(p * ing.loc[i, "intensity_index"] for i, p in d.items()) / 100
    longv = sum(p * ing.loc[i, "longevity_index"] for i, p in d.items()) / 100
    return round(cost, 0), round(inten, 2), round(longv, 2)


formula_metrics = pd.DataFrame(
    [(f, *metrics(d)) for f, d in comp.items()],
    columns=["formula_id", "cost_qar_per_kg", "intensity_index", "longevity_index"],
)

# ------------------------------------------------- deterministic optimizer
# Rule set v1: only oud materials and bases may move, in 1-point steps,
# total stays 100, intensity must stay >= target, boosters, precious, fixatives, top notes fixed.
OUDS = ["ING-01", "ING-02", "ING-03", "ING-04"]
BASES = ["ING-05", "ING-06"]


def optimize(fid):
    base = comp[fid]
    target = float(formulas.set_index("formula_id").loc[fid, "target_intensity"])
    movable = [i for i in OUDS + BASES if i in base] + [i for i in ("ING-03",) if i not in base]
    budget = sum(base.get(i, 0) for i in movable)
    fixed = {i: p for i, p in base.items() if i not in movable}
    best = (metrics(base)[0], dict(base))
    ranges = []
    for i in movable:
        lo = max(0, base.get(i, 0) - 8)
        hi = base.get(i, 0) + 8
        ranges.append(range(int(lo), int(hi) + 1))
    for combo in itertools.product(*ranges[:-1]):
        last = budget - sum(combo)
        if last < ranges[-1].start or last > ranges[-1].stop - 1 or last != int(last):
            continue
        cand = dict(fixed)
        cand.update({i: v for i, v in zip(movable, list(combo) + [last]) if v > 0})
        cost, inten, _ = metrics(cand)
        if inten >= target and cost < best[0] - 1e-9:
            best = (cost, cand)
    return best


rows = []
for fid in comp:
    b_cost, b_int, _ = metrics(comp[fid])
    o_cost, o_comp = optimize(fid)
    _, o_int, _ = metrics(o_comp)
    changes = []
    for i in sorted(set(comp[fid]) | set(o_comp)):
        delta = o_comp.get(i, 0) - comp[fid].get(i, 0)
        if abs(delta) > 1e-9:
            changes.append(f"{ing.loc[i, 'ingredient_name']} {delta:+.0f} pts")
    rows.append((fid, b_cost, o_cost, round(100 * (b_cost - o_cost) / b_cost, 1), b_int, o_int,
                 "; ".join(changes) or "no change", "grid-search-v1"))
optimization = pd.DataFrame(rows, columns=[
    "formula_id", "baseline_cost_qar_per_kg", "optimized_cost_qar_per_kg", "saving_pct",
    "baseline_intensity", "optimized_intensity", "recommended_changes", "method"])

# -------------------------------------------------------------- documents
T = {  # study_id -> text blocks. The recommendation sentences exist ONLY in the documents.
    "ST-11": dict(lang="en", conf="internal", team="Fragrance R&D", date="2025-09-30",
        title="Study ST-11: Paired blotter test, gulf panel, classic vs rose base",
        summary="Paired blotter test over two days with 36 testers at Panel A. Formula OB-102 (rose line, saffron absolute S-7 at 1.5 percent) was compared with OB-101 (classic oud, cardamom extract S-3).",
        finding="OB-102 reached 57 percent first choice against 48 percent for OB-101. The dwell ratio followed the same direction. Skin longevity scores were unchanged between the two formulas.",
        reco="Recommendation: keep OB-102 as the reference for the rose line. The gain is attributed to saffron absolute S-7, not to the rose base itself. Repeat with S-7 on the classic base before any reformulation.",
        note="Limitation: single site, two-day exposure. Dilution in alcohol differed by 4 percent between the two samples."),
    "ST-12": dict(lang="fr", conf="internal", team="Fragrance R&D", date="2026-02-28",
        title="Étude ST-12 : Préférence du panel export, dosage du safran S-7",
        summary="Test en paire sur blotters avec 40 testeurs au Panel B. La formule OB-104 (ligne export, safran absolu S-7 à 2 pour cent) a été comparée à OB-103 (ligne export, extrait de cardamome S-3).",
        finding="OB-104 atteint 68 pour cent de premier choix contre 51 pour cent pour OB-103. Le ratio de tenue en main confirme l'écart. Aucun rejet n'a été observé.",
        reco="Recommandation : passer OB-104 en essai pilote industriel. Le niveau de S-7 ne doit pas descendre sous 1,5 pour cent, seuil sous lequel le gain de préférence disparaît sur le panel export.",
        note="Limite : l'absolu de labdanum à 5 pour cent augmente le coût matière. Une optimisation du coût est demandée avant le lancement."),
    "ST-13": dict(lang="en", conf="restricted", team="Sustainable Sourcing Programme", date="2026-03-28",
        title="Study ST-13: Plantation oud acceptance, gulf panel, first screening",
        summary="First screening of OB-105 (plantation oud oil 22 percent, synthetic oud accord 10 percent) with 32 testers at Panel A, against the commercial reference OB-101.",
        finding="OB-105 reached 44 percent first choice. Testers pulled back at the first sniff, and interest recovered in the dry-down on day two. The opening was described by the panel leader as harsh and smoky.",
        reco="Recommendation: do not proceed with OB-105 as blended. Test a four-week maceration step before bottling and increase cardamom extract S-3 from 2 to 3 percent.",
        note="Restricted: contains supplier pricing for plantation oud oil under negotiation."),
    "ST-14": dict(lang="en", conf="restricted", team="Sustainable Sourcing Programme", date="2026-06-20",
        title="Study ST-14: Plantation oud acceptance after process change",
        summary="Repeat of ST-13 after the process change. OB-105 was produced with a four-week maceration after blending. Formula percentages were unchanged. 32 testers at Panel A.",
        finding="OB-105 reached 61 percent first choice, up from 44 percent in ST-13. The harsh opening was no longer reported.",
        reco="Recommendation: the maceration step, not the formula, drives acceptance of plantation oud. Approve OB-105 for a consumer wear test at home. Cost remains the open issue because plantation oud oil is the most expensive oud material in the portfolio.",
        note="Restricted: contains supplier pricing for plantation oud oil under negotiation."),
    "ST-15": dict(lang="fr", conf="internal", team="Fragrance R&D", date="2026-07-12",
        title="Étude ST-15 : Panel de jour, formule allégée OB-106",
        summary="Test monadique puis en paire sur 30 testeurs du panel de jour au Panel C. OB-106 contient 10 pour cent de bergamote et une part réduite de bois de santal.",
        finding="OB-106 atteint 53 pour cent de premier choix face à la référence. La tenue sur peau reste stable sur cinq jours de port.",
        reco="Recommandation : conserver le niveau de bergamote. Tester un dosage de safran S-7 à 1 pour cent pour compenser la base allégée, qui réduit la préférence sur le panel de jour.",
        note="Limite : panel de petite taille, port de jour uniquement."),
}

styles = getSampleStyleSheet()
doc_rows, chunk_rows = [], []
name_of = formulas.set_index("formula_id")["formula_name"]
for sid, t in T.items():
    doc_id = "DOC-" + sid.split("-")[1]
    fname = f"{sid}_{'fr' if t['lang'] == 'fr' else 'en'}_preference-report.pdf"
    st_trials = trials[trials.study_id == sid]
    fids = list(st_trials.formula_id) + (["OB-101"] if sid in ("ST-13", "ST-15") else [])
    fids = list(dict.fromkeys(fids))
    # chart
    fig, ax = plt.subplots(figsize=(5, 2.6))
    ax.bar(st_trials.formula_id, st_trials.first_choice_pct, color="#8a2432")
    ax.axhline(50, color="grey", lw=0.8, ls="--")
    ax.set_ylabel("Premier choix (%)" if t["lang"] == "fr" else "First choice (%)")
    ax.set_ylim(0, 100)
    fig.tight_layout()
    png = TMP / f"{sid}.png"
    fig.savefig(png, dpi=150)
    plt.close(fig)
    # composition table
    head = ["Matière" if t["lang"] == "fr" else "Material"] + fids
    body = []
    for iid in ing.index:
        vals = [comp[f].get(iid, 0) for f in fids]
        if any(vals):
            body.append([ing.loc[iid, "ingredient_name"]] + [f"{v:g} %" if v else "-" for v in vals])
    tbl = Table([head] + body, hAlign="LEFT")
    tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                             ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    labels = (("Résumé", "Résultats", "Composition des formules", "Recommandation", "Remarques")
              if t["lang"] == "fr" else
              ("Summary", "Results", "Formula composition", "Recommendation", "Notes"))
    story = [Paragraph("SYNTHETIC DEMO DOCUMENT. No customer data. All names and numbers are invented.", styles["Italic"]),
             Paragraph(t["title"], styles["Title"]),
             Paragraph(f"{t['team'].replace('&', '&amp;')} · {t['date']} · Classification: {t['conf']}", styles["Normal"]),
             Spacer(1, 0.4 * cm),
             Paragraph(labels[0], styles["Heading2"]), Paragraph(t["summary"], styles["Normal"]),
             Paragraph(labels[1], styles["Heading2"]), Paragraph(t["finding"], styles["Normal"]),
             Image(str(png), width=11 * cm, height=5.7 * cm),
             Paragraph(labels[2], styles["Heading2"]), tbl, Spacer(1, 0.3 * cm),
             Paragraph(labels[3], styles["Heading2"]), Paragraph(t["reco"], styles["Normal"]),
             Paragraph(labels[4], styles["Heading2"]), Paragraph(t["note"], styles["Normal"])]
    SimpleDocTemplate(str(DOCS / fname), pagesize=A4, title=t["title"]).build(story)
    doc_rows.append((doc_id, sid, t["title"], t["lang"], "preference study report", t["conf"],
                     t["team"], t["date"], fname))
    for n, (section, text) in enumerate([("summary", t["summary"]), ("results", t["finding"]),
                                         ("recommendation", t["reco"]), ("notes", t["note"])], 1):
        chunk_rows.append((f"{doc_id}-C{n}", doc_id, sid, section, t["lang"], t["conf"], text))

documents = pd.DataFrame(doc_rows, columns=["doc_id", "study_id", "title", "language", "doc_type",
                                            "confidentiality", "owner_team", "doc_date", "file_name"])
doc_chunks = pd.DataFrame(chunk_rows, columns=["chunk_id", "doc_id", "study_id", "section",
                                               "language", "confidentiality", "chunk_text"])

# Joined tables. The SQL endpoint the agent uses does not see notebook views, so these ship as tables.
formula_overview = (formulas.merge(formula_metrics, on="formula_id")
                    .merge(trials[["formula_id", "study_id", "first_choice_pct", "dwell_ratio",
                                   "trial_date", "panel_site"]], on="formula_id", how="left"))
study_recommendations = (doc_chunks[doc_chunks.section == "recommendation"]
                         .merge(documents[["doc_id", "title", "file_name"]], on="doc_id")
                         [["study_id", "title", "language", "confidentiality", "file_name", "chunk_text"]]
                         .rename(columns={"chunk_text": "recommendation"}))

for name, df in dict(ingredients=ingredients, formulas=formulas, formula_ingredients=formula_ingredients,
                     preference_trials=trials, formula_metrics=formula_metrics,
                     formula_optimization=optimization, documents=documents, doc_chunks=doc_chunks,
                     formula_overview=formula_overview, study_recommendations=study_recommendations).items():
    df.to_csv(DATA / f"{name}.csv", index=False)

# ------------------------------------------------------- expected answers
m = formula_metrics.merge(formulas[["formula_id", "formula_name", "status"]])
best = trials.sort_values("first_choice_pct", ascending=False).iloc[0]
over60 = trials[trials.first_choice_pct > 60].merge(m)
lines = ["# Expected answers", "",
         "Generated by `build_demo_assets.py` from the synthetic data. Check the agent against these.", "",
         "## Tables behind the answers", "", "### Cost and profile per formula", "",
         m[["formula_id", "formula_name", "status", "cost_qar_per_kg", "intensity_index", "longevity_index"]].to_markdown(index=False), "",
         "### Trials", "", trials.to_markdown(index=False), "",
         "### Deterministic optimizer output", "", optimization.to_markdown(index=False), "",
         "## Question by question", "",
         f"- **Q1** Highest first choice: {best.formula_id} in {best.study_id}, {best.first_choice_pct:g}%.",
         "- **Q2** Formulas above 60% first choice, with cost: "
         + "; ".join(f"{r.formula_id} {r.first_choice_pct:g}% at {r.cost_qar_per_kg:,.0f} QAR/kg ({r.study_id})" for r in over60.itertuples()) + ".",
         "  Recommendation text must come from the documents: ST-12 says move OB-104 to the industrial pilot and keep S-7 at or above 1.5%. ST-14 says the maceration step drives acceptance and approves OB-105 for a wear test at home.",
         "- **Q3** French: ST-12 recommends the industrial pilot for OB-104, S-7 not below 1.5%.",
         "- **Q4** Optimizer row for OB-104: "
         + optimization.set_index("formula_id").loc["OB-104"].to_json() + ". The agent must return these numbers unchanged.",
         "- **Q5** Why OB-105 moved from 44% to 61%: process change, four-week maceration after blending, formula unchanged (ST-13 vs ST-14). The formula table alone cannot answer this.",
         "- **Q6** Restricted user: ST-13 and ST-14 documents are hidden, so Q5 cannot be answered from documents.", ""]
(ROOT / "EXPECTED-ANSWERS.md").write_text("\n".join(lines), encoding="utf-8")
print("ok", {p.name: len(list(p.iterdir())) for p in (DATA, DOCS)})
print(optimization[["formula_id", "baseline_cost_qar_per_kg", "optimized_cost_qar_per_kg", "saving_pct", "recommended_changes"]].to_string(index=False))
