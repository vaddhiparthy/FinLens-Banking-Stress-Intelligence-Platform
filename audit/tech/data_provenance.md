# Ceiling B: data provenance (each served value traces to real data)

Goal: confirm no UI value is fabricated or stale. Every number the website shows traces back
through a committed artifact to the Gold layer to a public source.

## The chain

Public sources (free, no key)
  - FDIC BankFind financials API (per-bank quarterly Call Report fields) -> `ingestion/fdic_institutions.py`
  - FDIC failed-bank list (failure labels + resolution type) -> `ingestion/fdic.py`
  - FFIEC CDR (originally-filed Call Reports, point-in-time) -> `ml/finlens_ml/ffiec_pit.py`
  - FRED (macro context) -> `ingestion/fred.py`
  - NIC (parent metadata) -> `ingestion/nic.py`
        |
        v
Bronze/Silver/Gold in one DuckDB file `.duckdb/finlens.duckdb`
  - raw schema (bronze) -> dbt staging views (silver) -> dbt marts (gold)
  - ML feature panel: `ml.training_dataset` built by `ml/scripts/build_dataset.py`
    (448,661 bank-quarters, ~8,800 banks, 2008Q1-2026Q1, 34 CAMELS-aligned ratios)
  - dbt gold mart `bank_quarterly_risk_facts` (cert, quarter grain) selects from `ml.training_dataset`
        |
        v
Committed artifacts (the numbers the UI reads)
  - ml/artifacts/metrics_h4.json (served OOT metrics), viz_pack.json (charts),
    failure_decomposition.json, pooled_vs_addressable.json, cblr_robustness.json,
    sequence_challenger.json, competing_risks.json, fine_gray.json, calibration_bakeoff.json,
    g0_power_sim.json, b1_compare.json, rag/eval_report.json
        |
        v
UI (Streamlit) reads ONLY those committed artifacts (auto-synced, not hardcoded)

## Headline values and their source

| UI value | Artifact | Built from |
|---|---|---|
| OOT PR-AUC 0.301, ROC 0.855, recall@200 0.545 | metrics_h4.json `oot_test.calibrated_lgbm` | `ml.training_dataset` OOT split, served bagged model |
| Addressable PR-AUC 0.382 [0.250,0.530] | failure_decomposition.json | OOT scores + regulator failure-cause labels |
| Cross-model lift (5 families) | pooled_vs_addressable.json | OOT split, logit/RF/XGBoost/2 GBMs |
| 66 OOT failures / 19 banks | failure_decomposition.json, metrics_h4.json | FDIC failed-bank list joined to the panel |
| Failure causes (SVB, Heartland, etc.) | ml/finlens_ml/failure_cause_labels.py | FDIC OIG / OCC / Fed / Treasury OIG docs (URL + quote per bank) |
| RAG retrieval hit@4 1.0, MRR 0.92 | rag/eval_report.json | local Chroma index over the cited corpus |
| Bank-quarter risk facts (DE gold mart) | DuckDB marts.bank_quarterly_risk_facts | `ml.training_dataset` |

## Checks

- The wiki/AI surfaces read metrics via `_load_metric_values()` at import, so numbers cannot go
  stale relative to the artifacts.
- No fabricated/placeholder values are reachable: the prior "fabricated demo" surfaces were
  removed; the served model is frozen at commit 7473608.
- Reconciliation that passes: dbt build SUCCESS on the gold mart, Great Expectations 20/20 on
  bank_quarterly_risk_facts, and 82 passing tests including artifact-reconciliation tests in
  ml/tests/test_failure_decomposition.py (counts sum to 66, addressable >= pooled, CIs present).
