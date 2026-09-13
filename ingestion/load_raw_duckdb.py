"""
Load the raw Olist CSV files into a local DuckDB warehouse (schema: olist_raw).

Every column is loaded as VARCHAR on purpose. This mirrors what Meltano's
tap-csv delivers to BigQuery (strings only), so the dbt staging layer is
the single place where types are cast and the models behave identically
on DuckDB and BigQuery.

Usage:
    python ingestion/load_raw_duckdb.py [--db data/warehouse/olist.duckdb] [--raw data/raw]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb

log = logging.getLogger("load_raw_duckdb")

# CSV file -> raw table name. The table names match the Meltano entities in
# ingestion/meltano.yml so dbt sources are identical on both targets.
RAW_TABLES: dict[str, str] = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_translation",
}


def load(db_path: Path, raw_dir: Path, schema: str = "olist_raw") -> dict[str, int]:
    """Create/replace every raw table from its CSV and return row counts."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(f"create schema if not exists {schema}")
    counts: dict[str, int] = {}
    for filename, table in RAW_TABLES.items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing raw file: {path}")
        con.execute(
            f"""
            create or replace table {schema}.{table} as
            select *, current_timestamp as _loaded_at, '{filename}' as _source_file
            from read_csv(?, header=true, all_varchar=true)
            """,
            [str(path)],
        )
        counts[table] = con.execute(f"select count(*) from {schema}.{table}").fetchone()[0]
        log.info("loaded %-30s %10d rows", table, counts[table])
    con.close()
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/warehouse/olist.duckdb")
    parser.add_argument("--raw", default="data/raw")
    args = parser.parse_args()
    load(Path(args.db), Path(args.raw))
