# Ceiling B (technical) findings ledger

Evidence-backed. CLOSED only when a new artifact proves it.

| ID | Category | Component | Severity | Evidence | Status | Description |
|----|----------|-----------|----------|----------|--------|-------------|
| B-001 | Tests | full suite | (info) | audit/tech/test_results.txt | CLOSED | 82 passed, 0 failed across tests/ + ml/tests/. |
| B-002 | Coverage | offline pipeline/infra modules | Minor | audit/tech/coverage.txt | ACCEPTED (non-material) | Total coverage 52%. The served decision path is well covered (scenario 92%, serve 90%, splits 91%, evaluate high). The low-coverage modules are offline orchestration/warehouse plumbing (train.py 11%, warehouse 33%, evidence/pipeline_runs 0%) whose correctness is verified by running the pipeline (dbt build SUCCESS, GX 20/20, the 82 tests), not by unit tests. Unit-testing orchestration glue is low value vs the passing end-to-end run; accepted as non-material. |
| B-003 | Data provenance | all served values | (info) | audit/tech/data_provenance.md | CLOSED | Every UI value traces artifact -> Gold (ml.training_dataset) -> public source; no fabricated/placeholder values reachable; numbers auto-synced not hardcoded; served model frozen at 7473608. |
| B-004 | Pipeline state / reconciliation | DuckDB + dbt + GX + model | (info) | audit/tech/pipeline_state.md | CLOSED | dbt build SUCCESS; GX 20/20; metric gate active; 448,661 bank-quarters to 2026Q1; 66 OOT failures; reproducible from committed state. |
| B-005 | Unavoidable limit | model / paper tier | (info) | docs/ml/FINAL_SIGNOFF.md, g0_power_sim.json | ACCEPTED (physical) | 66 out-of-time failures cap paired power at ~6%; no single metric is individually separable. Data-existence wall (failures that did not happen cannot be created; pre-2001 Call Reports not machine-readable). Not unfinished work. |

## Reviewer sign-offs (audit/signoffs/)

| Reviewer | Verdict | File | Method |
|----------|---------|------|--------|
| tech_ml-model-risk | PASS | audit/signoffs/tech_ml-model-risk.md | reproduced 82/82 tests; verified embargo (splits.py assert_no_temporal_overlap), no-leakage (served ROC 0.855 < logit 0.924), calibration ECE 1.2e-4, monotone beats unconstrained, headline arithmetic reconciles, limits trace to 66-failure data wall |
| tech_data-engineering | PASS | audit/signoffs/tech_data-engineering.md | live re-ran dbt build (+3 grain tests), GX validate.py 20/20, pytest 82, DuckDB reconciliation 448,661 rows / 8,803 banks; confirmed GX-engine shadowing is disclosed in validate.py |
| tech_data-integrity | PASS | audit/signoffs/tech_data-integrity.md | spot-checked every UI value to its committed artifact (PR-AUC 0.301, addressable 0.382 [0.250,0.530], 66/19, cross-model lift, RAG hit@4 1.0); no served number is a code literal; 18/19 failure causes cite a regulator source |

All three Ceiling-B reviewers PASS with zero blocking issues. Non-blocking notes addressed:
- RAG metrics on the Analyst Assistant page were static copy -> now read from rag/eval_report.json (auto-sync).
- tier1_rwa null-rate wording clarified (~10% full-panel, ~37% post-2020 CBLR).
