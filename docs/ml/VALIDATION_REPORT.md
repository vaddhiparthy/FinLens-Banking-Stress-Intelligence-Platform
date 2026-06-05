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
  (PR-AUC 0.2213 vs 0.1117); because that margin sits on
  66 positives it is reported with a paired bootstrap (see §3),
  not as a bare point comparison. The unconstrained GBM scores higher on PR-AUC
  (0.2643 vs 0.2213, a 0.0431 / 16% gap); that gap is the
  deliberate cost of the monotone constraints. A free model can buy a little in-window
  PR-AUC by learning a perverse relationship (e.g. more capital raising predicted risk),
  which is precisely what conceptual-soundness review rejects, so the constrained,
  economically-signed model is the one served.
- **Hyperparameters:** tuned with Optuna over inner time-series CV folds (not hand-set
  magic numbers); the search is recorded in the metrics artifact.
- **No leakage:** the embargo guarantees a training row's label window (q, q+H] ends
  strictly before the test start (train q <= test_start - H - reporting_lag - 1),
  enforced at runtime (`assert_no_temporal_overlap`); labels are strictly forward-looking
  with merger / end-of-data censoring. OOT ROC-AUC 0.8153 is well below the
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
  PR-AUC [0.127, 0.343], recall@k [0.345, 0.577]. The PR-AUC
  edge over the logit is a paired bootstrap: difference 95% CI
  [+0.040, +0.177], P(LGBM > logit) = 100.0%.
- **Multi-origin rolling backtest:** 10 embargoed out-of-time folds,
  PR-AUC mean 0.2332 (std 0.2384, range
  0.0008-0.6707); strong in failure-containing windows,
  near-floor in calm years.
- Reported by-year cohorts (crisis vs calm) — the model is not a single-period fit.
- Calibration verified on the OOT set (ECE + top-decile observed-vs-predicted), not just
  an uninformative all-rows Brier.
- Served-model provenance recorded; reproducible (fixed seed, pinned feature set, $0 CI
  import-guard).

## Known gaps (honest, on the path to production)
- Competing risks (merger vs failure) are handled by right-censoring, not a formal
  Fine-Gray / cause-specific hazard model. Informative censoring (a stressed bank acquired
  instead of failing) could bias the failure hazard down; a cause-specific treatment is the
  next refinement.
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
