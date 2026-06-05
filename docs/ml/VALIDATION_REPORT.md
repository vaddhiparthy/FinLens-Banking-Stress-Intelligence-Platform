# Validation Report — FinLens Bank-Distress Model (SR 11-7 three pillars)

*Effective-challenge package. Metrics computed from real out-of-time evaluation.*

## 1. Conceptual soundness
- **Theory:** discrete-time hazard (bank-quarter panel) is the established framing for
  time-to-failure with time-varying covariates (BIS two-step; literature consensus).
- **Features:** 34 CAMELS-aligned ratios with economically-signed **monotone
  constraints** (more capital -> lower risk; higher noncurrent/NCO -> higher risk),
  preventing perverse relationships a validator would reject.
- **Benchmark / effective challenge:** a ladder of a penalized logistic regression (a
  regulatory-style linear reference) and an unconstrained GBM (same tuned params, no
  monotone constraints). The constrained GBM beats the logit on the rare-event metric
  (PR-AUC 0.2728 vs 0.1533); because that margin sits on
  66 positives it is reported with a paired bootstrap (see §3),
  not as a bare point comparison. The monotone constraints cost nothing measurable here: the constrained model (0.2728) matches or beats the unconstrained GBM (0.2696), so the economically-signed, validator-defensible model is also the strongest and is the one served.
- **Hyperparameters:** tuned with Optuna over inner time-series CV folds (not hand-set
  magic numbers); the search is recorded in the metrics artifact.
- **No leakage:** the embargo guarantees a training row's label window (q, q+H] ends
  strictly before the test start (train q <= test_start - H - reporting_lag - 1),
  enforced at runtime (`assert_no_temporal_overlap`); labels are strictly forward-looking
  with merger / end-of-data censoring. OOT ROC-AUC 0.8170 is well below the
  >0.98 leakage-suspicion threshold.
- **Honest data caveats:** the bank-level model does **not** join macro series (FRED is
  business-surface context, not a model input), so no macro-vintage question arises here.
  FDIC `/financials` returns currently-restated values, not the originally-filed Call
  Report; feature values are as-served, and originally-filed FFIEC data is the path to
  strict point-in-time feature integrity.

## 2. Ongoing monitoring (plan)
- **Drift:** Evidently data-drift + prediction-drift on inputs/scores each quarter
  (prediction drift is the earliest signal since labels arrive late).
- **Freshness / schema:** Pydantic v2 input validation at serving; feature null-rate
  and freshness checks.
- **Retraining:** quarterly Airflow DAG (`dag_ml_retrain`: build -> train+register -> metric
  gate -> export); the gate blocks promotion. Serving resolves the MLflow champion alias
  (`models:/finlens_bank_distress@champion`), so rollback is a real alias repoint, with the
  pinned local artifact as offline fallback.
- **Stability:** OMP_NUM_THREADS=1, bounded memory, last-known-good artifact cached.
- **Audit:** every served request is logged (request id, inputs, version, probability, flag,
  reason codes) for outcomes analysis and prediction-drift on real traffic.

## 3. Outcomes analysis (back-testing)
- **Headline holdout:** 118,943 bank-quarters / 66 real
  failures (2019-2026, includes the 2023 SVB/Signature/First-Republic cluster).
- **Uncertainty (the point estimates are not the result):** 95% stratified-bootstrap CIs —
  PR-AUC [0.163, 0.408], recall@k [0.400, 0.636]. The PR-AUC
  edge over the logit is a paired bootstrap: difference 95% CI
  [+0.038, +0.195], P(LGBM > logit) = 99.8%.
- **Multi-origin rolling backtest:** 10 embargoed out-of-time folds,
  PR-AUC mean 0.2128 (std 0.2128, range
  0.0002-0.5152); strong in failure-containing windows,
  near-floor in calm years.
- Reported by-year cohorts (crisis vs calm) — the model is not a single-period fit.
- Calibration verified on the OOT set (ECE + top-decile observed-vs-predicted), not just
  an uninformative all-rows Brier.
- Served-model provenance recorded; reproducible (fixed seed, pinned feature set, $0 CI
  import-guard).

## Known gaps (honest, on the path to production)
- Competing risks (merger vs failure) are handled by right-censoring, not a formal
  Fine-Gray subdistribution model. The informative-censoring bias this could introduce is
  now QUANTIFIED, not assumed (see docs/ml/COMPETING_RISKS.md): mergers are ~4x more
  common than failures (Aalen-Johansen CIF 0.74 vs 0.18), but only 2.2% of merger-exit
  banks were elevated-distress at exit, so the downward recall bias is small and bounded.
  A full Fine-Gray model would move the estimate marginally; it remains the next refinement.
- Features come from the FDIC `/financials` endpoint, which serves currently-restated
  values rather than the originally-filed Call Report. The leakage embargo handles label
  timing, not feature restatement; sourcing originally-filed FFIEC CDR data is the path to
  strict point-in-time feature integrity.
- The data is U.S. public Call Report financials only; it cannot see confidential
  supervisory information, intraday liquidity, or deposit-flow data.

## Effective challenge
This report + the benchmark comparison + the adversarial phase reviews constitute the
independent challenge. The CI metric gate (PR-AUC must beat the logit benchmark by a
margin, OOT ROC below the leakage ceiling, calibration ECE bound) blocks promotion.
