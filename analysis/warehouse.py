"""
Single place that knows how to connect to the warehouse with SQLAlchemy.

    WAREHOUSE=duckdb   (default)  -> data/warehouse/olist.duckdb
    WAREHOUSE=bigquery            -> needs GCP_PROJECT_ID and `gcloud auth application-default login`
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_SCHEMA = "olist_analytics"


def get_engine() -> Engine:
    backend = os.environ.get("WAREHOUSE", "duckdb").lower()
    if backend == "bigquery":
        project = os.environ["GCP_PROJECT_ID"]
        return create_engine(f"bigquery://{project}")  # pip install sqlalchemy-bigquery
    db_path = os.environ.get("DUCKDB_PATH", str(REPO_ROOT / "data" / "warehouse" / "olist.duckdb"))
    # SQLAlchemy URLs do not tolerate Windows backslashes; as_posix() keeps the
    # drive letter (C:/...) and works identically on POSIX.
    db_url = Path(db_path).expanduser().resolve().as_posix()
    return create_engine(f"duckdb:///{db_url}", connect_args={"read_only": True})  # pip install duckdb-engine


def query(sql: str, engine: Engine | None = None) -> pd.DataFrame:
    """Run a SQL string and return a DataFrame."""
    engine = engine or get_engine()
    with engine.connect() as con:
        df = pd.read_sql(text(sql), con)
    # Normalise date columns (DuckDB returns datetime.date, BigQuery returns db-dtypes)
    for col in df.columns:
        if df[col].dtype == object and df[col].map(lambda v: hasattr(v, "year")).any():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def table(name: str, engine: Engine | None = None) -> pd.DataFrame:
    return query(f"select * from {ANALYTICS_SCHEMA}.{name}", engine)
