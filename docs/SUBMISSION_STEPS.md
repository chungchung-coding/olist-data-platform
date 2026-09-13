# Submission steps (follow in order)

> **On Windows?** Use `docs/RUNBOOK_WINDOWS.md` instead — it is the same four steps with PowerShell-native commands and `run_all.ps1` in place of `make`.

## A. Get the project onto your machine

1. Unzip `olist-data-platform.zip` somewhere convenient, e.g. `~/olist-data-platform`.
2. Copy the nine Olist CSVs into `data/raw/` (the same files you uploaded: `olist_*.csv` and `product_category_name_translation.csv`). They are git-ignored, so they will not be pushed.
3. Open a terminal in the project folder and create the environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

## B. Run the pipeline once locally (proves everything works before you push)

```bash
make all
```

Expected console tail: `Done. PASS=20 ... TOTAL=20`, then `Done. PASS=74 WARN=2 ERROR=0`, then `Overall: PASS`. Charts appear in `analysis/outputs/`.

If `make` is not installed (Windows), run the five commands listed under "Quick start" in `README.md` instead.

Optional but worth a screenshot for the slides:

```bash
cd orchestration && dagster dev -f olist_dagster/definitions.py
```

Open http://localhost:3000, click **Assets → Materialize all**, screenshot the lineage graph, save it as `docs/images/dagster_lineage.png`.

## C. Create the GitHub repository (single `main` branch)

1. On github.com → **New repository** → name `olist-data-platform`, Public, **do not** tick "Add a README" (the project already has one). Create.
2. Back in the terminal, in the project folder:

   ```bash
   git init -b main
   git add .
   git status                       # confirm data/raw/*.csv and *.duckdb are NOT listed
   git commit -m "Olist data platform: ingestion, dbt star schema, quality gates, analysis, Dagster"
   git remote add origin https://github.com/<your-username>/olist-data-platform.git
   git push -u origin main
   ```

3. Refresh the repository page. The README renders with the architecture image; `docs/schema_design.md` renders the ERD (GitHub draws Mermaid natively).

## D. Enable CI (optional, but it demonstrates orchestration/automation)

1. On kaggle.com → your profile → **Settings → API → Create New Token**; this downloads `kaggle.json`.
2. In the GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:
   - `KAGGLE_USERNAME` = the `username` value from `kaggle.json`
   - `KAGGLE_KEY` = the `key` value
3. Go to the **Actions** tab → `pipeline-ci` → **Run workflow**. It should finish green in a few minutes and attach the charts as a downloadable artifact. Screenshot the green run for the deck.

## E. Slide deck

Build the deck from `docs/presentation_outline.md` (14 slides, timings and speaker notes included). Use the PNGs in `analysis/outputs/` and `docs/images/`. Export as PDF and commit it:

```bash
cp ~/Downloads/olist_executive_presentation.pdf docs/
git add docs/olist_executive_presentation.pdf
git commit -m "Add executive presentation"
git push
```

## F. Final checklist against the brief

| Brief section | Where it is satisfied |
|---|---|
| 1 Data ingestion | `ingestion/meltano.yml`, `ingestion/load_raw_duckdb.py`, `ingestion/load_raw_bigquery.py` |
| 2 Warehouse design (star schema) | `dbt/olist_dbt/models/marts/core/`, `docs/schema_design.md` |
| 3 ELT pipeline, cleaning, derived totals | `models/staging/` (cleaning), `fact_orders.order_total_value`, `customer_metrics.lifetime_value` |
| 4 Data quality testing | `dbt test` (96), `quality/run_great_expectations.py` (28) |
| 5 Python analysis with SQLAlchemy + pandas | `analysis/warehouse.py`, `analysis/notebooks/*.ipynb`, `analysis/run_analysis.py` |
| 6 Orchestration | `orchestration/olist_dagster/definitions.py` (daily schedule), `.github/workflows/ci.yml` (nightly) |
| 7 Documentation & diagrams | `README.md`, `docs/report.md`, `docs/schema_design.md`, `docs/images/architecture.png` |
| 8 Executive presentation | `docs/presentation_outline.md` → your deck |
| Deliverable: single-branch GitHub repo | step C |
| Deliverable: Jupyter notebooks | `analysis/notebooks/` (executed, with outputs) |
| Deliverable: slide deck | step E |
