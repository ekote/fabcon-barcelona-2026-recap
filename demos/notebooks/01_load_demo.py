# Fabric notebook, PySpark. Attach the lakehouse "lh_oud_rd" as default, then Run all.
# Paste each "# CELL" block into its own cell. Runtime: about 2 minutes on a warm session.
# Input:  Files/demo/data/*.csv  and  Files/demo/docs/*.pdf  (upload both folders first)
# Output: 10 Delta tables, plus 1 table extracted live from the PDFs.
# formula_overview and study_recommendations ship as CSV from build_demo_assets.py and load as
# tables on purpose. Views made in a notebook do not show in the SQL endpoint the agent uses.

# CELL 1 ---------------------------------------------------------------- load tables
tables = ["ingredients", "formulas", "formula_ingredients", "preference_trials",
          "formula_metrics", "formula_optimization", "documents", "doc_chunks",
          "formula_overview", "study_recommendations"]
for t in tables:
    df = (spark.read.option("header", True).option("inferSchema", True)
          .option("multiLine", True).option("escape", '"')
          .csv(f"Files/demo/data/{t}.csv"))
    df.write.mode("overwrite").option("overwriteSchema", True).format("delta").saveAsTable(t)
    print(t, df.count())

# CELL 2 ------------------------------------------- extract text from the PDFs, live
# Shows the documents are really read from files, not only from the prepared CSV.
# If pip is blocked or slow, skip this cell. The agent works from doc_chunks alone.
%pip install pypdf --quiet

# CELL 3
from pypdf import PdfReader
import os, re
rows = []
base = "/lakehouse/default/Files/demo/docs"
for f in sorted(os.listdir(base)):
    if not f.endswith(".pdf"):
        continue
    study_id = f.split("_")[0]
    lang = f.split("_")[1]
    for n, page in enumerate(PdfReader(f"{base}/{f}").pages, 1):
        text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        rows.append((f, study_id, lang, n, text))
pdf_df = spark.createDataFrame(rows, "file_name string, study_id string, language string, page int, page_text string")
pdf_df.write.mode("overwrite").format("delta").saveAsTable("doc_pages_extracted")
display(pdf_df.selectExpr("file_name", "page", "substring(page_text, 1, 160) as preview"))

# CELL 4 ------------------------------------------------------------- sanity check
# Must match EXPECTED-ANSWERS.md: OB-104 68% in ST-12 on top, OB-105 61% in ST-14 second.
display(spark.sql("SELECT formula_id, formula_name, study_id, first_choice_pct, cost_qar_per_kg FROM formula_overview ORDER BY first_choice_pct DESC"))
display(spark.sql("""
SELECT o.formula_id, o.baseline_cost_qar_per_kg, o.optimized_cost_qar_per_kg, o.saving_pct, o.recommended_changes
FROM formula_optimization o ORDER BY o.formula_id
"""))
