# One-command reproduction on DuckDB. Run `make all` from the repo root.
PY ?= python3
export DBT_PROFILES_DIR := $(CURDIR)/dbt/olist_dbt

.PHONY: install ingest transform test quality analysis all dagster docs clean

install:
	pip install -r requirements.txt

ingest:
	$(PY) ingestion/load_raw_duckdb.py

transform:
	cd dbt/olist_dbt && dbt run --target duckdb

test:
	cd dbt/olist_dbt && dbt test --target duckdb

quality:
	$(PY) quality/run_great_expectations.py

analysis:
	cd analysis && $(PY) run_analysis.py

all: ingest transform test quality analysis

dagster:
	cd orchestration && dagster dev -f olist_dagster/definitions.py

docs:
	cd dbt/olist_dbt && dbt docs generate --target duckdb && dbt docs serve

clean:
	rm -rf dbt/olist_dbt/target data/warehouse/*.duckdb quality/gx_results.json
