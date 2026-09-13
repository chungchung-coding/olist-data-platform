# Olist Data Platform — Technical Report

## 1. Problem and scope

Olist is a Brazilian marketplace connecting small sellers to large online storefronts. The dataset (Kaggle, ~100 k orders, Sept 2016 – Aug 2018, nine CSVs) is transactional and normalised: orders, items, payments, reviews, customers, sellers, products and geolocation are all separate files. The business asked two questions (see `docs/images/business_case.png`):

1. **Sales readiness** — when is demand strongest, which products, categories and regions drive it, who are the customer segments (and specifically the "gold" audience), and which sellers must be prepared.
2. **Delivery readiness** — which regions get long or late deliveries, where fulfilment attention should go, and what would shorten delivery.

The deliverable is a reproducible pipeline that lands the raw data in a warehouse, models it as a star schema, tests it, and exposes it to analysts through SQLAlchemy and pandas.

## 2. Architecture

![architecture](images/architecture.png)

| Stage | Tool | Why this and not the alternative |
|---|---|---|
| Source | Kaggle CSVs | Required by the brief; the richest of the three options for a two-sided marketplace question. |
| Ingestion | **Meltano `tap-csv` → `target-bigquery`**, or the two Python loaders | Meltano gives declarative, repeatable EL with a plugin ecosystem; the Python loaders keep the project runnable with zero cloud setup. Both land identical all-string raw tables. Airbyte was considered but is heavier to self-host for nine files. |
| Warehouse | **BigQuery** (cloud) and **DuckDB** (local) | BigQuery is serverless and scales past this dataset without ops; DuckDB is in-process, free, and runs the 1.5 M-row workload in ~3 s — the "out-of-core / scalability" leg in the diagram, and what CI runs on. One dbt project targets both. |
| Transformation | **dbt** | Version-controlled SQL with lineage, tests and docs. A pure-Python transform layer would duplicate what the warehouse does best and lose the test framework. |
| Quality | **dbt tests + Great Expectations** | dbt tests guard keys, relationships and accepted values at build time; GE adds distribution/range expectations and a machine-readable report, and reads through SQLAlchemy so the same suite runs on either warehouse. |
| Analysis | **SQLAlchemy + pandas + matplotlib** in Jupyter | As specified; `analysis/warehouse.py` hides the connection so notebooks are backend-agnostic. |
| Orchestration | **Dagster** | Asset-based: every dbt model is an asset with lineage, and the raw load, GE gate and analysis are assets in the same graph. Airflow is task-based and heavier for a small team; a cron job gives no lineage or UI. GitHub Actions additionally runs the whole pipeline in CI and nightly. |
| Supporting | Docker (optional Postgres), GitHub | Reproducibility and source control. |

Data flows: CSV → `olist_raw` (strings) → `olist_staging` (typed views) → `olist_analytics` (star + marts) → notebooks / GE / Dagster.

## 3. Warehouse design

See `docs/schema_design.md` for the ERD and the full justification. Summary: four dimensions (customers, products, sellers, date), two facts at two grains (order line and order), six business marts built on top, natural keys, all derived measures computed once in dbt.

## 4. Data cleaning and validation

Cleaning applied in staging:

- all types cast from string; timestamps parsed; zip prefixes left-padded to 5 chars;
- city/state normalised (`lower`/`upper`, trimmed);
- product categories translated to English with `unknown` for the 610 uncategorised products;
- reviews deduplicated to one per order (latest answered) — the raw file has 99 224 rows for 98 673 orders;
- geolocation filtered to Brazil's bounding box and averaged to one centroid per zip prefix (1 000 163 → 19 015 rows).

Validation: 96 dbt tests (unique, not-null, relationships, accepted values, composite uniqueness, five singular logic tests) and 28 Great Expectations across six analytics tables. Two tests are configured to **warn**, because they detect genuine defects in the public dataset that should be surfaced rather than silently dropped:

| Check | Result | Interpretation |
|---|---|---|
| Delivered orders must have a delivery date | 8 rows | Status set to `delivered` before the carrier scan was recorded. Excluded from delivery KPIs. |
| Payments ≈ items + freight (± R$1) | 246 rows (0.25 %) | Vouchers and partial refunds; `payment_value` is kept separately from `order_total_value` so analysts can choose. |

Everything else passes. `quality/gx_results.json` is written on every run.

## 5. Findings — sales readiness

Charts are in `analysis/outputs/`; KPIs in `analysis/outputs/kpis.json`.

- **Timing.** Revenue peaks in **November 2017 (R$ 1.17 m)**, the Black Friday month, and November is the strongest month-of-year on average. 2018 is running well ahead of 2017 (R$ 8.59 m Jan–Aug 2018 vs R$ 7.09 m for all of 2017). The campaign should be planned for November with seller stock built from September.
- **Products.** 635 distinct products reach a monthly top-50, but only 21 do so in six or more months — that short list is the always-stock core; the rest of the top-50 is seasonal and should be managed month by month from `top_products_monthly`.
- **Categories.** Overall revenue leaders: health & beauty (R$ 1.26 m), watches & gifts (R$ 1.20 m), bed/bath/table, sports & leisure, computer accessories. Within the top-50 lists, watches & gifts and health & beauty dominate.
- **Regions.** São Paulo alone is 38 % of revenue; SP + RJ + MG = 63 %. The southeast is where inventory should be positioned.
- **Segments.** An RFM segmentation on `customer_unique_id` gives: gold 12 082 customers (13 %) → 30 % of revenue, avg LTV R$ 392; silver 24 k → 31 %; lapsed 23 k → 24 %; standard 35 k → 14 %. Only **3 % of customers ever buy twice** — retention, not acquisition, is the largest untapped lever.
- **Gold audience.** Gold members live in the same SP/RJ/MG geography and over-index on watches & gifts (R$ 478 k) and health & beauty (R$ 471 k), then sports & leisure. That defines the campaign assortment.
- **Sellers.** 540 of 3 053 active sellers generate 80 % of revenue; `seller_performance` ranks them with handling time, late rate and review score so the ones to brief and stock are explicit.

## 6. Findings — delivery readiness

- National averages: **12.5 days** to deliver, **8.1 % late** against the promised date, with a very generous promise (24.4 days estimated vs 12.5 actual).
- **Where it is slow:** Roraima 29 d, Amapá 27 d, Amazonas 26 d, Alagoas 25 d, Pará 24 d — versus São Paulo 8.7 d. **Where it is late:** Alagoas 24 %, Maranhão 20 %, Piauí 16 %, Ceará 15 %, Sergipe 15 %.
- **Which leg:** seller handling is flat at ~2.7 days in every state; approval is 0.5 days. **The entire regional gap is carrier transit** (9.3 days nationally, 20+ in the North/North-East). Fulfilment attention belongs in carrier contracts and regional cross-docks for the North and North-East, not in seller processes.
- **Capacity, not just distance:** the late rate spikes with volume — 21 % in March 2018 and elevated in November 2017 — so carrier capacity must be pre-booked for the campaign month.
- **It matters commercially:** on-time orders average a 4.29 review score; late ones 2.57.

Recommendations: (1) negotiate a regional carrier or hub for AL/MA/PI/CE/SE where lateness, not distance, is the problem; (2) pre-book carrier capacity for November; (3) tighten the estimated-delivery promise for SP/MG/PR where actuals are far inside it, and hold it for the North; (4) monitor `delivery_performance_by_state` monthly from the pipeline.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Data drift / schema change in the source | Raw layer is string-typed and dbt tests fail loudly; GE report is machine-readable. |
| Cloud cost on BigQuery | Marts are pre-aggregated; partition/cluster the facts; DuckDB path for dev and CI. |
| Single-branch, single-maintainer repo | CI on every push; `make all` reproduces from scratch in under a minute. |
| Segment definitions are heuristic (RFM quartiles) | Thresholds are in one dbt model and documented; easy to align with marketing. |
| Dataset is 2016–2018 | Pipeline is date-agnostic; the same run works on a live export. |

## 8. Reproduction

```bash
pip install -r requirements.txt
# put the Kaggle CSVs in data/raw/
make all            # ingest → dbt run → dbt test → Great Expectations → charts
make dagster        # orchestrated run with lineage UI
```
