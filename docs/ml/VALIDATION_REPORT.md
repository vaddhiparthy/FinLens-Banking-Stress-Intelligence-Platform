# Validation Report — FinLens Bank-Distress Model (SR 11-7 three pillars)

*Effective-challenge package. Metrics computed from real out-of-time evaluation.*

## 1. Conceptual soundness
- **Theory:** discrete-time hazard (bank-quarter panel) is the established framing for
  time-to-failure with time-varying covariates (BIS two-step; literature consensus).
- **Features:** 31 CAMELS-aligned ratios with economically-signed **monotone
  constraints** (more capital -> lower risk; higher noncurrent/NCO -> higher risk),
  preventing perverse relationships a validator would reject.
- **Benchmark / effective challenge:** penalized logistic regression (the SCOR/SEER
  regulatory reference). The GBM must and does beat it on the rare-event metric
  (PR-AUC 0.2183 vs 0.1078).
- **No leakage:** rolling-origin out-of-time split with a reporting-lag embargo
  (train q + H < test start), enforced at runtime (assert_no_temporal_overlap), grouped
  by event window; ALFRED-vintage macro committed (no latest-vintage look-ahead);
  labels strictly forward-looking with merger/end-of-data censoring. OOT ROC-AUC
  0.8156 is below the >0.98 leakage-suspicion threshold.

## 2. Ongoing monitoring (plan)
- **Drift:** Evidently data-drift + prediction-drift on inputs/scores each quarter
  (prediction drift is the earliest signal since labels arrive late).
- **Freshness / schema:** Pydantic v2 input validation at serving; feature null-rate
  and freshness checks.
- **Retraining triggers:** scheduled quarterly retrain + drift-threshold trigger;
  champion/challenger via MLflow aliases; instant rollback by repointing the alias.
- **Stability:** OMP_NUM_THREADS=1, bounded memory, last-known-good artifact cached.

## 3. Outcomes analysis (back-testing)
- Out-of-time backtest on 118,943 bank-quarters / 66 real
  failures (2019-2026, includes the 2023 SVB/Signature/First-Republic cluster).
- Reported by-year cohorts (crisis vs calm) — the model is not a single-period fit.
- Calibration verified on the OOT set (ECE + top-decile observed-vs-predicted), not
  just an uninformative all-rows Brier.
- Served-model provenance recorded (trained on all data with the OOT-validated tree
  count); reproducible (fixed seed, pinned feature set, $0 CI import-guard).

## Effective challenge
This report + the benchmark comparison + the adversarial phase reviews constitute the
independent challenge. Failing any metric gate (PR-AUC / recall@k / calibration /
champion-vs-challenger) blocks promotion in CI.
