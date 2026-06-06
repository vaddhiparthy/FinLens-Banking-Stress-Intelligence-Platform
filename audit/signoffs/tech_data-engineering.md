# Ceiling B sign-off: data-engineering
VERDICT: PASS

ARTIFACTS REVIEWED:
- audit/tech/pipeline_state.md, data_provenance.md, test_results.txt, findings.md
- dbt/models/marts/bank_quarterly_risk_facts.sql, dbt/models/marts/schema.yml, dbt/tests/assert_bank_quarterly_risk_facts_unique_grain.sql, dbt/models/staging/sources.yml, dbt/dbt_project.yml, dbt/target/run_results.json
- dbt staging/marts: stg_fdic_qbp.sql, fct_stress_pulse.sql (silver->gold chain spot-check)
- great_expectations/expectations/bank_quarterly_risk_facts.json, great_expectations/validate.py, great_expectations/README.md, uncommitted/validation_bank_quarterly_risk_facts.json
- airflow/dags/*.py (all 8: ingest_fdic/fred/qbp/nic, transform_and_quality, ml_retrain, sync_control_plane, common)
- ingestion/fdic.py (+ fred/nic/qbp/fdic_institutions present), src/finlens/warehouse.py
- Live re-runs against .duckdb/finlens.duckdb (245 MB)

BLOCKING ISSUES: none

NOTES:
1. dbt build re-run live (dbt 1.11.8, duckdb adapter 1.10.1): bank_quarterly_risk_facts model built OK and all 3 grain tests PASS (composite-unique singular test + not_null cert + not_null quarter). PASS=4 WARN=0 ERROR=0. Matches the "dbt build SUCCESS + grain tests" claim. Note the gold mart is materialized as a table sourced from ml.training_dataset (the Python-built ML panel in the same DuckDB), NOT through the dbt staging layer; the SQL header and sources.yml document this explicitly, and the provenance table states "Built from: ml.training_dataset". The provenance chain diagram is slightly idealized (shows raw->staging->marts as the universal path) but the mart-specific lineage is stated honestly. Not a blocker.
2. Great Expectations suite re-run live: 20/20 expectations pass (1 row_count + 8 column_to_exist + 7 not_null + 3 range + 1 max-freshness). Observed row count 448,661; max quarter 2026Q1; exit 0. Matches the "20/20 via validate.py" claim. The committed uncommitted/validation_*.json reconciles with the live run.
3. GX engine shadowing is real and confirmed: `import great_expectations` resolves to the repo's top-level great_expectations/ dir (namespace package, __file__ None); the PyPI engine is not importable. validate.py is a self-contained evaluator of the same GX v3 suite JSON that queries the actual materialized mart and exits non-zero on failure. This is a real quality gate, not a stub, and is prominently disclosed in validate.py's docstring. Acceptable for a $0 portfolio. Caveat (note, not blocker): the GX README.md is a stale one-line stub ("will live here") and does NOT carry the shadowing disclosure; the disclosure lives only in the runner. Worth fixing the README for completeness.
4. DuckDB layer reconciles: ml.training_dataset and the gold mart both = 448,661 rows, 8,803 distinct banks, 2008Q1-2026Q1; schemas raw/ml/marts/snapshots all present; bronze raw tables populated (fdic_qbp_raw 41, fred_observations_raw 31,205, fdic_failed_banks_raw 573). Matches the documented "~8,800 banks, 448,661 bank-quarters".
5. Documentation overstates the tier1_rwa_ratio null rate. pipeline_state.md and the GX suite meta say "~37% post-2020 CBLR null"; actual observed non-null fraction in the mart is 0.90 (i.e. ~10% null overall). The GX threshold is set permissively at mostly=0.55 so it passes regardless, but the "~37%" figure is inaccurate. Cosmetic doc fix, not a blocker.
6. Full pytest suite re-run live: 82 passed, 0 failed (46s), matching audit/tech/test_results.txt. Coverage 52% total accepted as non-material per B-002 (low-coverage modules are offline orchestration/warehouse plumbing; served decision path well covered).
7. DAGs are coherent and reference real scripts. dag_ml_retrain wires build_dataset -> train (horizon 4) -> metric_gate -> export_web_data with the gate gating promotion (champion alias stays on failure). dag_transform_and_quality runs ingest + dbt build + probe + sync. All referenced scripts exist (ml/scripts/*, scripts/run_local_pipeline.py). Ingestion modules are real (fdic.py fetches a live public CSV and writes bronze JSON; no stubs).

Every load-bearing claim (dbt build SUCCESS, grain tests pass, GX 20/20, 82 tests, 448,661 bank-quarters to 2026Q1, provenance chain) verified by live re-execution, not just committed artifacts. Zero blocking issues.
