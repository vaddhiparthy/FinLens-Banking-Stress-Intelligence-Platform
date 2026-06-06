# Ceiling B: pipeline state, freshness, reconciliation

## Orchestration (Airflow DAGs, airflow/dags/)
- dag_ingest_fdic (daily), dag_ingest_fred (hourly), dag_ingest_qbp (quarterly),
  dag_ingest_nic (quarterly) -> bronze.
- dag_transform_and_quality (daily): ingest + `dbt build` + platform probe + control-plane sync.
- dag_ml_retrain (quarterly): build dataset -> train (horizon 4) -> metric gate (blocks
  promotion on regression/leakage) -> export.
- dag_sync_control_plane (every 30 min).

## Data layer
- One DuckDB file: `.duckdb/finlens.duckdb` (~245 MB).
- ML feature panel `ml.training_dataset`: 448,661 bank-quarters, ~8,800 banks, 2008Q1-2026Q1,
  34 features. Out-of-time holdout = last 28 quarters with reporting-lag embargo, 66 real
  failures across 19 distinct banks.
- dbt gold mart `bank_quarterly_risk_facts` (cert, quarter): `dbt build` SUCCESS, grain tests
  pass (not_null cert/quarter + composite-unique singular test).

## Quality gates (reconciliation that passes, with numbers)
- Great Expectations suite `bank_quarterly_risk_facts`: 20/20 expectations pass
  (audit via great_expectations/validate.py), covering schema, freshness (max quarter >= 2024Q4),
  and null-rate (tier1_rwa: ~10% null across the full 2008-2026 panel, rising to ~37% post-2020
  as small banks elect the CBLR framework and stop reporting risk-weighted assets; GX threshold
  mostly=0.55 passes either way).
- dbt tests: pass on the mart.
- Test suite: 82 passed, 0 failed (audit/tech/test_results.txt), incl. artifact-reconciliation
  tests (decomposition counts sum to 66; addressable >= pooled; CIs present; GRU inside GBM CI).
- CI metric gate (ml/scripts/metric_gate.py): PR-AUC must beat the logit benchmark by a margin,
  OOT ROC below the leakage-suspicion ceiling, calibration ECE within bound.

## Served model
- Frozen at commit 7473608 (calibrated, monotone, 12-seed bagged LightGBM hazard model).
- Resolution: MLflow champion alias `models:/finlens_bank_distress@champion`, with the pinned
  local skops artifact as offline fallback; loaded via skops trusted-type allow-list (not pickle).

## Freshness note
- Panel runs to 2026Q1. Two failures (Metropolitan Capital, Community B&T West Georgia) close at
  or just past the panel end and are labelled via the forward failure feed (failure_year 2026).

## Reproducibility
- Fixed seeds, pinned feature set, committed metrics. `$0` enforced by the CI import-guard
  (ml/tests/test_no_billable_imports.py). The served numbers reproduce from the committed
  artifacts; the offline pipeline reproduces them from `ml.training_dataset`.
