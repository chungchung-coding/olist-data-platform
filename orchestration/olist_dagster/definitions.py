"""
Dagster orchestration for the Olist pipeline.

Asset graph:   raw_olist_tables  ->  (dbt models, one asset each)  ->  quality_gate  ->  analysis_outputs

    cd orchestration
    dagster dev -f olist_dagster/definitions.py      # UI on http://localhost:3000
    dagster job execute -f olist_dagster/definitions.py -j olist_daily_job

Set WAREHOUSE=bigquery / DBT_TARGET=bigquery to run the same graph on BigQuery.
"""

import os
import subprocess
import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSelection,
    AssetSpec,
    Definitions,
    MaterializeResult,
    ScheduleDefinition,
    asset,
    define_asset_job,
    multi_asset,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ingestion"))
from load_raw_duckdb import RAW_TABLES  # noqa: E402  (file -> raw table name)

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DIR = REPO_ROOT / "dbt" / "olist_dbt"
PYTHON = sys.executable

dbt_project = DbtProject(project_dir=DBT_DIR, profiles_dir=DBT_DIR)
dbt_project.prepare_if_dev()  # builds manifest.json when running `dagster dev`


# 1. Ingestion -----------------------------------------------------------------
# One asset key per raw table, e.g. olist_raw/orders. These keys are exactly what
# dagster-dbt derives from the dbt sources, so the lineage graph is fully connected.
RAW_ASSET_SPECS = [AssetSpec(key=AssetKey(["olist_raw", t]), group_name="ingestion", kinds={"python"}) for t in RAW_TABLES.values()]


@multi_asset(specs=RAW_ASSET_SPECS)
def raw_olist_tables(context: AssetExecutionContext):
    """Land the raw CSVs in the warehouse (schema olist_raw), all columns as strings."""
    script = "ingestion/load_raw_bigquery.py" if os.environ.get("WAREHOUSE", "duckdb") == "bigquery" else "ingestion/load_raw_duckdb.py"
    context.log.info("running %s", script)
    subprocess.run([PYTHON, script], cwd=REPO_ROOT, check=True)
    for spec in RAW_ASSET_SPECS:
        yield MaterializeResult(asset_key=spec.key, metadata={"loader": script})


# 2. Transformation: every dbt model becomes its own Dagster asset --------------
@dbt_assets(manifest=dbt_project.manifest_path)
def olist_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()  # build = run + test


# 3. Quality gate -----------------------------------------------------------------
@asset(group_name="quality", compute_kind="great_expectations", deps=[olist_dbt_assets])
def quality_gate(context: AssetExecutionContext) -> MaterializeResult:
    """Great Expectations suite over the analytics layer; fails the run on any breach."""
    subprocess.run([PYTHON, "quality/run_great_expectations.py"], cwd=REPO_ROOT, check=True)
    return MaterializeResult(metadata={"report": str(REPO_ROOT / "quality" / "gx_results.json")})


# 4. Analysis outputs ------------------------------------------------------------
@asset(group_name="analysis", compute_kind="pandas", deps=[quality_gate])
def analysis_outputs(context: AssetExecutionContext) -> MaterializeResult:
    """Charts and KPI tables for the executive report (analysis/outputs/)."""
    subprocess.run([PYTHON, "run_analysis.py"], cwd=REPO_ROOT / "analysis", check=True)
    return MaterializeResult(metadata={"outputs_dir": str(REPO_ROOT / "analysis" / "outputs")})


olist_daily_job = define_asset_job("olist_daily_job", selection=AssetSelection.all())
olist_daily_schedule = ScheduleDefinition(job=olist_daily_job, cron_schedule="0 6 * * *")  # 06:00 daily

defs = Definitions(
    assets=[raw_olist_tables, olist_dbt_assets, quality_gate, analysis_outputs],
    jobs=[olist_daily_job],
    schedules=[olist_daily_schedule],
    resources={"dbt": DbtCliResource(project_dir=dbt_project, profiles_dir=str(DBT_DIR))},
)
