"""
Alternative to Meltano: load the raw Olist CSVs straight into BigQuery
(dataset: olist_raw) with the official client library. All columns are
loaded as STRING so the dbt staging layer does the typing, exactly as in
the DuckDB loader.

Prereqs:
    pip install google-cloud-bigquery
    gcloud auth application-default login
    export GCP_PROJECT_ID=<your-project>

Usage:
    python ingestion/load_raw_bigquery.py
"""
from __future__ import annotations

import csv
import logging
import os
from pathlib import Path

from google.cloud import bigquery

from load_raw_duckdb import RAW_TABLES  # reuse the same file -> table mapping

log = logging.getLogger("load_raw_bigquery")


def load(project: str, dataset: str = "olist_raw", raw_dir: Path = Path("data/raw"), location: str = "US") -> None:
    client = bigquery.Client(project=project)
    ds_ref = bigquery.Dataset(f"{project}.{dataset}")
    ds_ref.location = location
    client.create_dataset(ds_ref, exists_ok=True)

    for filename, table in RAW_TABLES.items():
        path = raw_dir / filename
        with path.open(newline="", encoding="utf-8") as fh:
            header = next(csv.reader(fh))
        schema = [bigquery.SchemaField(col, "STRING") for col in header]
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            allow_quoted_newlines=True,  # review comments contain line breaks
        )
        with path.open("rb") as fh:
            job = client.load_table_from_file(fh, f"{project}.{dataset}.{table}", job_config=job_config)
        job.result()
        rows = client.get_table(f"{project}.{dataset}.{table}").num_rows
        log.info("loaded %-30s %10d rows", table, rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load(project=os.environ["GCP_PROJECT_ID"])
