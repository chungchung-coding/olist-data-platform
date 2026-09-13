# Executive Presentation — 10 minutes + 5 Q&A

Audience: CEO/CFO/COO and CTO/Engineering Director. Every slide has one message; the number is the headline, the chart is the evidence.

| # | Slide | Headline | Visual | Notes (≈ time) |
|---|---|---|---|---|
| 1 | Title | Olist Data Platform: sales and delivery readiness | — | 0:15 |
| 2 | Executive summary | We built a tested, automated warehouse from Olist's raw files; it says: plan the campaign for November around gold members in SP/RJ/MG, and fix the carrier leg in the North-East. | three-box summary | 1:30 — problem, solution, so-what |
| 3 | The business questions | Two cases, seven questions | `images/business_case.png` | 0:30 |
| 4 | Business value | Decisions this enables: stock the 21 always-top products by September; target 12 k gold members who are 30 % of revenue; pre-book carrier capacity for November | KPI tiles | 1:00 |
| 5 | When demand peaks | Nov 2017 = R$ 1.17 m, the peak; 2018 already ahead of 2017 | `outputs/01_monthly_revenue.png` | 0:45 |
| 6 | What sells | Health & beauty and watches & gifts lead; SP = 38 % of revenue | `outputs/03_categories_and_states.png` | 0:45 |
| 7 | Who buys | Gold = 13 % of customers, 30 % of revenue; only 3 % ever re-order | `outputs/04_segment_revenue_share.png` | 0:45 |
| 8 | Delivery: where | North/North-East take 2–3× longer; AL/MA/PI are 15–24 % late | `outputs/05_delivery_days_by_state.png` | 0:45 |
| 9 | Delivery: why | Seller handling is 2.7 d everywhere — the gap is the carrier; late orders score 2.6 vs 4.3 | `outputs/07_volume_vs_late_rate.png` | 0:45 |
| 10 | Technical overview | CSV → warehouse → dbt star schema → tests → analysis, orchestrated by Dagster, runs in CI | `images/architecture.png` | 1:15 — for the CTO: one codebase, two warehouses, 124 automated checks |
| 11 | Data quality | 96 dbt tests + 28 expectations; two known source defects surfaced, not hidden | small table | 0:30 |
| 12 | Risks | Cost, drift, heuristic segments, dataset age — each with a mitigation | table | 0:45 |
| 13 | Recommendations & next steps | 1) November campaign for gold, SE region 2) regional carrier/hub for NE 3) retention programme 4) monthly monitoring from the pipeline | list | 0:45 |
| 14 | Q&A | — | — | 5:00 |

## Likely questions and short answers

- *Why DuckDB and BigQuery both?* One dbt codebase; DuckDB for free local dev and CI, BigQuery for shared production scale. Switching is one environment variable.
- *How do we know the numbers are right?* 124 automated checks run on every build; the pipeline fails rather than publish bad data. The two warnings are documented source defects.
- *Why dbt rather than Python transforms?* SQL runs where the data is, is version-controlled, and comes with tests, lineage and docs for free.
- *What does "gold" mean?* Top quartile of lifetime spend and bought recently (RFM). Thresholds sit in one model and can be aligned with marketing in minutes.
- *What would it cost to run on BigQuery?* The full dataset is < 200 MB; a daily rebuild is well inside the free tier. Marts are pre-aggregated so dashboards do not rescan the facts.
- *Can it handle live data?* Yes — the pipeline is date-agnostic; point Meltano at the live export and schedule Dagster.
