"""
Great Expectations quality gate for the analytics layer.

The same suite runs against DuckDB (default) or BigQuery: tables are read through
SQLAlchemy into pandas, then validated with GX 1.x. Exit code 1 on failure so the
script works as a gate in Dagster or GitHub Actions.

    python quality/run_great_expectations.py                 # DuckDB
    WAREHOUSE=bigquery GCP_PROJECT_ID=... python quality/run_great_expectations.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import great_expectations as gx
import pandas as pd
from great_expectations import expectations as gxe

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from warehouse import get_engine, ANALYTICS_SCHEMA  # noqa: E402

REPORT_PATH = Path(__file__).resolve().parent / "gx_results.json"

# table -> list of expectations. Kept declarative so it reads like a data contract.
SUITES: dict[str, list] = {
    "fact_orders": [
        gxe.ExpectColumnValuesToBeUnique(column="order_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="order_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="customer_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="purchased_at"),
        gxe.ExpectColumnValuesToBeInSet(
            column="order_status",
            value_set=["delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "created", "approved"],
        ),
        gxe.ExpectColumnValuesToBeBetween(column="order_total_value", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="review_score", min_value=1, max_value=5),
        # 8 rows in the public dataset are 'delivered' with no date; tolerate <0.1%
        gxe.ExpectColumnValuesToNotBeNull(column="delivered_to_customer_at", mostly=0.95),
        gxe.ExpectColumnValuesToBeBetween(column="actual_delivery_days", min_value=0, max_value=250),
        gxe.ExpectTableRowCountToBeBetween(min_value=90_000, max_value=120_000),
    ],
    "fact_order_items": [
        gxe.ExpectCompoundColumnsToBeUnique(column_list=["order_id", "order_item_id"]),
        gxe.ExpectColumnValuesToNotBeNull(column="product_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="seller_id"),
        gxe.ExpectColumnValuesToBeBetween(column="price", min_value=0, strict_min=True),
        gxe.ExpectColumnValuesToBeBetween(column="freight_value", min_value=0),
        gxe.ExpectColumnPairValuesAToBeGreaterThanB(column_A="total_item_value", column_B="price", or_equal=True),
    ],
    "dim_customers": [
        gxe.ExpectColumnValuesToBeUnique(column="customer_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="customer_unique_id"),
        gxe.ExpectColumnValueLengthsToEqual(column="state", value=2),
        gxe.ExpectColumnValuesToBeBetween(column="lat", min_value=-34, max_value=6, mostly=0.99),
    ],
    "dim_products": [
        gxe.ExpectColumnValuesToBeUnique(column="product_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="category"),
    ],
    "monthly_sales": [
        gxe.ExpectColumnValuesToBeUnique(column="month_start"),
        gxe.ExpectColumnValuesToBeBetween(column="total_revenue", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="late_delivery_rate", min_value=0, max_value=1),
    ],
    "customer_metrics": [
        gxe.ExpectColumnValuesToBeUnique(column="customer_unique_id"),
        gxe.ExpectColumnValuesToBeInSet(column="customer_segment", value_set=["gold", "silver", "repeat", "lapsed", "standard"]),
        gxe.ExpectColumnValuesToBeBetween(column="order_count", min_value=1),
    ],
}


def main() -> int:
    engine = get_engine()
    context = gx.get_context(mode="ephemeral")
    datasource = context.data_sources.add_pandas("olist_analytics")

    results: dict[str, dict] = {}
    all_ok = True
    for table, expectations in SUITES.items():
        df = pd.read_sql(f"select * from {ANALYTICS_SCHEMA}.{table}", engine)
        asset = datasource.add_dataframe_asset(name=table)
        batch_def = asset.add_batch_definition_whole_dataframe(f"{table}_batch")
        suite = context.suites.add(gx.ExpectationSuite(name=f"{table}_suite"))
        for exp in expectations:
            suite.add_expectation(exp)
        vd = context.validation_definitions.add(
            gx.ValidationDefinition(name=f"{table}_validation", data=batch_def, suite=suite)
        )
        res = vd.run(batch_parameters={"dataframe": df})
        failed = [r.expectation_config.type for r in res.results if not r.success]
        results[table] = {"rows": len(df), "success": res.success, "n_expectations": len(res.results), "failed": failed}
        all_ok &= res.success
        print(f"{'PASS' if res.success else 'FAIL'}  {table:32s} rows={len(df):7d}  expectations={len(res.results)}  failed={failed}")

    REPORT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}  (report: {REPORT_PATH})")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
