# Fact-check: Data Engineering page (`streamlit_app/pages/4_Data_Engineering.py`)

Audited 2026-06-06 against live `.duckdb/finlens.duckdb`, `dbt/target/run_results.json` (Jun 6), committed `great_expectations/validation_result.json` (Jun 6), and `data/state/*.json` snapshots (mostly Apr 27, file-rewritten Jun 3).

Live truth captured:
- DuckDB: 17 base tables. raw.fdic_failed_banks_raw=573, raw.fdic_qbp_raw=41 (max quarter 2025Q4), raw.fred_observations_raw=31205, raw.nic_current_parent_raw=4289, marts.bank_quarterly_risk_facts=448661 (max quarter 2026Q1), ml.training_dataset=448661, snapshots.dim_bank_snapshot=573.
- Live `dbt/target/run_results.json` = a **partial** ML-targeted build: 1 model (`bank_quarterly_risk_facts`) + 3 tests = 4 nodes only. Generated 2026-06-06.
- `dbt_build_report.json` snapshot: captured_at **2026-04-27**, claims 10 models / 4 tests / 15 nodes.
- gitignored (absent in a fresh deploy): all `data/state/*`, `.duckdb`, `dbt/target/*`, GX `uncommitted/*`. Only `great_expectations/validation_result.json` is committed.

| Section | Displayed item | Source of truth | Current? | Evidence / fix |
|---|---|---|---|---|
| Live Pipeline (cards) | FDIC/FRED/Gold/Dashboards status + note | `pipeline_status_rows()` ← `pipeline_status.json` | STALE | last_run/updated_at all 2026-04-25 / 2026-04-27. FRED note "0 series updated", "6 series". QBP "16,854 bytes", NIC "2,039,028 bytes" frozen from April. File mtime Jun 6 but timestamps inside still April. |
| Live Pipeline (FDIC card "Rows/units") | FDIC rows = "—" (U+2014, shows as mojibake `�` in some renders) | pipeline_status.json | STALE/cosmetic | rows is em-dash, not a real count; DuckDB has 573 FDIC rows that are never surfaced here. |
| Infra cards | AWS S3 / Airflow / dbt / Snowflake status | `platform_stack_frame()` ← `platform_probe_report.json` | STALE | Snapshot 2026-04-27. S3 "Ready", Snowflake "Ready" (account GC15571), Airflow runtime "Unavailable", Postgres "Failed"→shown Deferred. All probe results are 6 weeks old; not re-run. In a deploy these probes are absent (Scaffolded fallback). |
| Pipeline status table | All 7 flows "Success", QBP/NIC landed | pipeline_status.json | STALE + INCONSISTENT | QBP/NIC marked Success (overriding DEFERRED defaults), but `stress_pulse_source_mode()` returns "pending" (no resolvable QBP artifact), so Reconciliation says QBP "Deferred". Table and reconciliation disagree. |
| Reconciliation Controls | Status = "Deferred", "QBP aggregate not activated", "No QBP source URL configured" | `stress_pulse_source_mode()` (live) | INCONSISTENT/WRONG-ish | Returns "pending" because data_mode=live and latest qbp manifest's artifact_path does not resolve → maps to non-live → "Deferred". But DuckDB raw.fdic_qbp_raw has 41 rows (max 2025Q4) and pipeline table claims QBP landed. Self-contradicting surface. |
| dbt Data Quality Summary | Build status Success, **Models passed 11, Tests passed 7, Total nodes 19**, Captured at **2026-04-27** | `dbt_artifact_summary()` merges live run_results.json + stale snapshot report_summary | WRONG | Counts are a double-count: stale snapshot 10/4/15 + live partial run 1/3/4 = 11/7/19. Neither figure is a real single build. captured_at is 6 weeks stale. The live build actually produced only 1 model + 3 tests. Fix: stop seeding summary from stale `report_summary` when live run_results.json exists; derive captured_at from run_results `generated_at`. |
| dbt Node-Level Results | model + 3 tests rows for `bank_quarterly_risk_facts` | `dbt_result_rows()` ← live run_results.json (Jun 6) | PASS | Matches live partial build (4 nodes). Honest. Note mismatch vs the summary above (4 here vs 19 there). |
| Great Expectations Suite | PASS, 20/20, table marts.bank_quarterly_risk_facts, row count 448,661, max quarter 2026Q1 | `validation_result.json` (committed) + `uncommitted/...json` | PASS | Both files identical, mtime Jun 6. Row count 448,661 matches live DuckDB exactly; max quarter 2026Q1 matches. Committed copy makes this the one section that stays correct in a fresh deploy. |
| Warehouse Classification (inventory) | Layer/Schema/Table/Rows/Columns | `warehouse_table_rows()` (live DuckDB) | PARTIAL/WRONG-LABEL | Row counts correct (573/41/31205/4289/448661/352). BUT layer logic is `raw→Bronze/raw else Gold mart`, so `ml.training_dataset` and `snapshots.dim_bank_snapshot` are mislabeled "Gold mart". Also excludes all VIEWs (dim_date, dim_state, stg_*, int_*) since it filters BASE TABLE only, so staging/intermediate layers are invisible here yet appear in the data browser. |
| Source Classification (activation) | FDIC/FRED/QBP/NIC all "ready: true" | `connector_report.json` (Apr 27) + runtime aliases | STALE | Snapshot 2026-04-27. All four "ready". In deploy the report is absent → "No connector report". |
| Source Freshness | label/freshness/SLA/status/required+missing env | `connector_report.json` | STALE | Same Apr 27 snapshot; "Success" freshness for all is frozen, not recomputed. |
| Source Landing Artifacts | raw files, latest artifact, record count, ingested_at, storage path | `source_landing_rows()` (live filesystem) | STALE (data) / PASS (logic) | Logic reads live files, but newest ingestion_date for every source is 2026-04-27 (fdic 16 files, fred 6, nic 9, qbp 9). "Ingested at" will show April. No new landings since. |
| Engineering Stack — tool_evidence | dbt "Success build on local at 2026-04-27...", Pipeline run ledger run_id `20260427T115453Z-...` | `dbt_build_report.json` + `latest_pipeline_run()` | STALE | dbt captured_at 2026-04-27; latest_pipeline_run finished_at 2026-04-27, duration 43.346s. Both 6 weeks old, presented as current state. |
| Engineering Stack — platform readiness | S3 buckets, Snowflake role/db, Airflow note, Postgres schema | `platform_probe_report.json` + settings | STALE | Probe report Apr 27. Detail strings (e.g. "Raw bucket reachable") are frozen probe output, not live. |
| Airflow Run Results | DAG runs | `airflow_run_report` state (absent) | PASS (honest) | No `airflow_run_report.json` exists → "No run artifact / Pending". Honest empty state. |
| Latest Pipeline Run | steps, durations, details | `latest_pipeline_run.json` | STALE | Run from 2026-04-27, 5 steps. Durations (18.021s ingest, 8.484s dbt, 15.87s probes) are April values shown as latest. |
| Warehouse Activation Checklist | Snowflake/dbt/Airflow status | `platform_probe_report.json` | STALE | Derived from Apr 27 probes. |
| Code Excerpts | static Python/DAG/SQL/serving snippets | hardcoded in page | PASS (illustrative) | Explicitly representative excerpts, not live metrics. The dbt SQL excerpt references `stg_fdic_failures` which doesn't exist (real model is `stg_fdic_failed_banks`); cosmetic. |
| Service Endpoint Catalog | /health, /healthz, /telemetry/*, /predict*, /ready, /failures, /banks/{id}, /metrics/{series_id} | `api/main.py`, `api/routers/*`, `ml/finlens_ml/serve.py` | PASS | All verified: serve.py has /health,/ready,/predict,/predict-failure-risk,/predict/batch (:8077). api/main.py has /health,/healthz; routers have /failures,/banks/{id},/metrics/{series_id},/telemetry/events,/telemetry/summary. URLs default to 127.0.0.1:8010 / :8501 when env unset. |
| Control Sync (Postgres) | status, "{event_count} local events captured", schema | `platform_probe_report` (Failed→Deferred) + `telemetry_summary()` (live) | MIXED | Postgres status from Apr 27 probe (Failed→shown Deferred, honest). event_count is LIVE (telemetry_events.json mtime Jun 6, 230KB) — this one number is fresh while the status around it is stale. |
| Containerization & K8s deploy | ml/Dockerfile, api/Dockerfile, Dockerfile.streamlit, airflow/Dockerfile, docker-compose.prod.yml, deploy/k8s/kind-config.yaml, deploy/k8s/ml-serve.yaml | filesystem | PASS | All 7 artifacts exist. ml-serve.yaml (Jun 6) and kind-config.yaml present under deploy/k8s/. NodePort/probe caption matches recipe. |
| Deploy caption | image name `fulllens-ml-serve`, svc `fulllens-ml-serve`, NodePort 30077 | hardcoded string | CHECK | "fulllens" likely a typo for "finlens"; verify against ml-serve.yaml service name (not re-read here). Cosmetic but visible. |

## Worst offenders (stale snapshots presented as current)
1. **dbt Data Quality Summary** — captured_at 2026-04-27 + double-counted 11 models / 7 tests / 19 nodes (real live build = 1 model + 3 tests). This is the single most misleading row: wrong numbers, not just stale.
2. **Pipeline status + cards** — every flow frozen at Apr 25/27 with frozen rows/notes; QBP/NIC shown Success while reconciliation shows them Deferred (internal contradiction).
3. **Latest Pipeline Run / tool_evidence / platform readiness / activation checklist** — all driven by Apr 27 `latest_pipeline_run.json` + `platform_probe_report.json`.
4. **connector_report / freshness / source landing** — Apr 27 snapshot + April-only raw files.
5. **Warehouse inventory layer mislabel** — ml + snapshots schemas tagged "Gold mart"; views omitted entirely.

## Deploy-environment caveat
All `data/state/*`, `.duckdb`, and `dbt/target/*` are gitignored. On a fresh Streamlit Cloud deploy these are absent, so most of the page renders "Pending / No run / Scaffolded" fallbacks. Only `great_expectations/validation_result.json` is committed and renders real numbers (448,661 rows, 20/20, 2026Q1). The locally-shown "Success/Ready" metrics above will NOT appear in deploy.

## Tally
- PASS: 6 (GX suite, dbt node-level rows, service endpoints, deploy artifacts, airflow empty-state, code excerpts as illustrative)
- STALE: 11 (pipeline cards, infra cards, pipeline table, dbt tool_evidence, platform readiness, source activation, freshness, source landing, latest pipeline run, activation checklist, control-sync status portion)
- WRONG: 3 (dbt Data Quality Summary counts+date, warehouse layer mislabel, reconciliation vs pipeline contradiction)
- MIXED/COSMETIC: deploy caption typo, FDIC em-dash row, excerpt model-name typo
