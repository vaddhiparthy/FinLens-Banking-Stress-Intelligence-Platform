# Ceiling B sign-off: ML / model-risk

VERDICT: PASS

ARTIFACTS REVIEWED:
- audit/tech/test_results.txt
- audit/tech/coverage.txt
- audit/tech/data_provenance.md
- audit/tech/pipeline_state.md
- audit/tech/findings.md (B-001..B-005)
- ml/artifacts/metrics_h4.json
- ml/artifacts/failure_decomposition.json
- ml/artifacts/pooled_vs_addressable.json
- ml/artifacts/sequence_challenger.json
- ml/artifacts/g0_power_sim.json
- ml/artifacts/calibrated_h4.skops (served model artifact, present on disk)
- docs/ml/FINAL_SIGNOFF.md
- docs/ml/MODEL_CARD.md
- docs/ml/VALIDATION_REPORT.md
- ml/finlens_ml/splits.py, features.py, config.py, train.py (source verified, not just attested)

BLOCKING ISSUES: none

NOTES:
1. Tests independently re-run, not trusted from the file. Clean full run of `tests/ ml/tests/`
   reproduces the committed claim: 82 passed, 0 failed. One interim run showed 2 failures
   (test_monitor::test_drift_report, test_model_card::test_generate_model_card) but both were a
   transient external DuckDB file lock (a stray python process held .duckdb open); both pass in
   isolation and the lock-free full re-run is 82/82. Not a code defect.

2. Embargoed out-of-time split is real and correct in code. splits.final_holdout_split applies
   train_cutoff = test_start - horizon_q - reporting_lag_q - 1, and assert_no_temporal_overlap
   enforces max(train_q)+horizon < min(test_q) STRICTLY at runtime. reporting_lag_q defaults to 1
   (config.py), so the embargo genuinely accounts for the Call Report filing lag, not just the
   label horizon. This is a clean time split, not a random or grouped split.

3. No leakage signal. Served GBM OOT ROC-AUC 0.855 sits well below the >0.98 leakage-suspicion
   ceiling; notably the logit benchmark posts a HIGHER ROC (0.924) than the served model, which is
   the opposite of what feature leakage would produce. Reported optimism is honest: inner-CV
   PR-AUC 0.5665 collapses to OOT 0.301 (gap 0.265, ratio 1.88) and is disclosed in the artifact
   rather than hidden. GRU challenger shows the same in-sample-to-OOT collapse (0.607 -> 0.207),
   consistent with regime/cohort shift, not leakage.

4. Calibration verified from the artifact, not just the all-rows Brier. OOT ECE 1.22e-04; top
   decile predicted 0.00347 vs observed 0.00353. The model card correctly flags that all-rows
   Brier is dominated by true negatives and reports the flagged-decile calibration instead.
   Isotonic, bagged x12.

5. Monotonicity is economically signed and validator-defensible. MONOTONE_CONSTRAINTS:
   tier1_rwa_ratio -1 (more capital lowers risk), noncurrent_to_loans +1 (more bad loans raises
   risk), and consistent signs on deltas/peer-z. Constraints cost nothing measurable here: the
   monotone model (0.3014) beats the unconstrained GBM (0.2696), so the served model is both the
   most defensible and the strongest point estimate.

6. Headline metrics are backed and arithmetically reconcile. PR-AUC 0.3014 [0.191, 0.438] and
   addressable 0.3819 [0.250, 0.530] match metrics_h4.json / failure_decomposition.json. Type
   counts 14+40+12 = 66; addressable+invisible 52+14 = 66. Pooled-to-addressable lift positive in
   all 5 model families (+0.041 to +0.081). GRU 0.2073 falls inside the served CI [0.191, 0.438].
   The lgbm-vs-logit edge is a paired bootstrap (diff CI [+0.070, +0.222], P=1.0), not a bare
   point comparison.

7. Limitations are honestly caveated and trace to data/physics, not unfinished work. Every
   document states the 66-OOT-failure power wall: g0_power_sim.json confirms ~6% paired power at
   delta 0.02 and tier_a_oot_shippable=false, and the docs explicitly say no single number is
   individually separable and claims are about direction across models/label sources. The
   invisible (fraud/run) cohort is correctly framed as structurally unpredictable from Call Report
   financials by construction, and pre-2001 Call Reports are documented as non-existent in
   machine-readable form. These are data-existence and statistical-power walls.

8. Coverage gap is genuinely non-material and does not hide model logic. The served decision path
   is well covered (serve 90%, scenario 92%, splits 91%, explain 94%, features 94%, model_card
   91%, scenario/monitor 85%+). The 0-to-33% modules are offline orchestration/warehouse plumbing
   (train.py 11%, warehouse 33%, evidence/pipeline_runs 0%, ffiec_pit/data 0%, registry 27%).
   train.py low coverage is acceptable because its OUTPUT (the frozen served artifact + committed
   metrics) is what is validated, and the splits/evaluate/calibration logic it calls IS covered by
   unit tests. No untested model-scoring code is masked by the 52% total. One residual: ffiec_pit.py
   (point-in-time feature integrity) is 0% covered and the restated-vs-originally-filed feature
   caveat is openly disclosed in the model card and validation report as a known gap, not claimed
   as solved. Recorded as a note, not a blocker, because the served model does not depend on it.

9. Provenance and freshness reconcile: served model frozen at commit 7473608 (verified to exist in
   git history), artifact calibrated_h4.skops present, panel to 2026Q1, dbt build SUCCESS / GX
   20/20 per pipeline_state.md, CI metric gate active. The two 2026-closing failures are disclosed
   as labelled via the forward failure feed.
