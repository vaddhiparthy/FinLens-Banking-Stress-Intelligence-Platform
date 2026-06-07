# Fact-check: AI Engineering page

Scope: `streamlit_app/pages/7_AI_Engineering.py` + `streamlit_app/lib/ml_charts.py`.
Sources of truth verified: `ml/artifacts/*.json` and DuckDB `ml.training_dataset`.

DuckDB (live): `count=448661`, `distinct cert=8803`, `min quarter=2008Q1`, `max quarter=2026Q1`.

Legend: PASS = matches source; STALE = hardcoded literal that has drifted or could silently drift; WRONG = disagrees with source now.

## Pipeline flow-diagram

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Pipeline | "448,661 bank-quarters" | DuckDB count = 448661 | PASS (but fragile) | YES (literal) | Matches today. Not loaded from DB; will silently drift on next panel refresh. Replace with a `SELECT count(*)` or bake into viz_pack. |
| Pipeline | "~8,800 banks" | DuckDB distinct cert = 8803 | PASS | YES (literal) | "~8,800" ≈ 8803. Approximate so low drift risk, still hardcoded. |
| Pipeline | "2008–2026Q1" | DuckDB min/max quarter = 2008Q1 / 2026Q1 | PASS | YES (literal) | Matches. Hardcoded; drifts when panel extends. |
| Pipeline | "{N_FEATURES} features" | `FEATURE_COLUMNS` (live import) = 34 | PASS | NO | Computed live. |
| Pipeline | "point-in-time", "monotone-signed" | descriptive | PASS | YES (text) | Descriptive labels, accurate. |
| Pipeline | "{_nfail} OOT failures" → 66 | `viz.n_oot_failures` = 66 | PASS | NO (fallback 66) | Loaded; fallback literal `66` if viz missing matches current. |
| Pipeline | "leakage-free", "forward-looking" | descriptive | PASS | YES (text) | Accurate. |
| Pipeline | "28-quarter holdout" | `metrics_h4.eval_window_quarters` = 28 | PASS | YES (literal) | Matches 28 but hardcoded in flow tile (the caption below uses the loaded value). Drifts if window changes. |
| Pipeline | "embargoed", "no leakage" | descriptive | PASS | YES (text) | Accurate. |
| Pipeline | "PR-AUC {_pr:.3f}" → 0.301 | `metrics_h4.oot_test.calibrated_lgbm.pr_auc` = 0.30136 | PASS | NO | Loaded. |
| Pipeline | "ECE {_ece:.0e}" → 1e-04 | `metrics_h4.oot_calibration.ece` = 0.0001217 | PASS | NO | Loaded; `1e-04`. |
| Pipeline | "/predict-failure-risk", "calibrated prob", "drift-watched" | descriptive | PASS | YES (text) | Accurate. |
| Pipeline | bullet list (ingest/features/label/split/train/serve) | descriptive | PASS | mixed | N_FEATURES live; rest descriptive. |
| Pipeline | success box: trees, tree_count_source, calibration_method, n_train | `metrics_h4.final_model` (38, eval-model OOT early stopping, isotonic x12, 416095) | PASS | NO | All from `final_model`. |

## Model Quality hero

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Quality | PR-AUC (OOT) 0.301 + 95% CI [0.19, 0.44] | `oot_test.calibrated_lgbm.pr_auc`, `oot_test_ci.pr_auc_ci` [0.1908,0.4380] | PASS | NO | Loaded. |
| Quality | ROC-AUC (OOT) 0.855 | `oot_test.calibrated_lgbm.roc_auc` = 0.85527 | PASS | NO | Loaded. |
| Quality | Recall@200 54.5% + CI [42%,66%] | `recall_at_k`=0.5455, `recall_at_k_ci` [0.4189,0.6572] | PASS | NO | Loaded. "@200" comes from `k`=200 in artifact (label hardcodes 200; matches). |
| Quality | Calibration ECE 1.2e-04 | `oot_calibration.ece` = 0.0001217 | PASS | NO | Loaded. |
| Quality | caption: window quarters, n_oot, n_oot_failures, base rate | `eval_window_quarters`=28, `viz.n_oot`=118943, `n_oot_failures`=66, `curves.base_rate`=0.00055 | PASS | NO | All loaded. |
| Quality | "beat benchmark" paired bootstrap: median +0.142, CI [+0.070,+0.222], P=100.0% | `lgbm_vs_logit_ap_diff` (0.1420, [0.0696,0.2223], prob 1.0) | PASS | NO | Loaded. |
| Quality | rolling backtest: 10 folds, mean 0.2128, std 0.2128, range 0.0002–0.5152 | `rolling_backtest.aggregate` | PASS | NO | Loaded. mean==std==0.2128 (real, bimodal folds). |

## Challenger ladder + tuning + G0

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Ladder | Calibrated LGBM 0.3014 / 0.8553 / 0.545 | `oot_test.calibrated_lgbm` | PASS | NO | Loaded. |
| Ladder | Unconstrained GBM 0.2696 / 0.8332 / 0.515 | `challengers.unconstrained_gbm` | PASS | NO | Loaded. |
| Ladder | Penalized logit 0.1533 / 0.9241 / 0.379 | `oot_test.logit_benchmark` | PASS | NO | Loaded. |
| Ladder caption | gap 0.032 / ~11%, "66 OOT positives", "see G0" | computed from artifacts; `test_positives`=66 | PASS | "66" literal in caption | gap = 0.2696−0.3014 → wrong-sign guard: code uses `gap=u−t` (negative), so it takes the `else` branch (monotone matches/beats). Wait: u(0.2696) < t(0.3014) so gap<0 → else-branch caption shown ("matches or beats"). Correct branch fires. PASS. The "66" and ">0.01" thresholds are literals but consistent with data. |
| Ablation forest | rungs (logit .153, single .188, tuned .259, bagged .301, stacked .273, unconstr .270) + shipped line | `viz.ablation.rungs`, shipped from `viz.curves.pr_auc` | PASS | NO | All loaded; shipped reference is loaded not hardcoded. n_pos≈66 in caption is a fixed annotation. |
| Tuning | Optuna 39 trials, 3 inner folds, best CV PR-AUC 0.5665, best_params | `hyperparameter_tuning` (n_trials 39, n_inner_folds 3, cv_mean_pr_auc 0.5665, best_params) | PASS | NO | Loaded. |
| Tuning study | optimism ratio 1.9×, inner 0.5665 vs OOT 0.3014 | `study.optimism` (ratio 1.88, inner 0.5665, oot 0.3014) | PASS | NO | Loaded. |
| G0 | MDE statement (power 6% at delta 0.02) | `viz.g0.gate_power.mde_statement` | PASS | NO | Loaded. |
| G0 | interval coverage: chosen_method "bca", nominal 95%, by_dgp cells, recall note | `viz.g0.interval_coverage_sim` (chosen_method=bca, by_dgp surrogate_subsample/parametric_planted, recall_jeffreys_coverage=null→recall_note used) | PASS | NO | Loaded; recall clause falls back to `recall_note` since jeffreys coverage is null. |

## Failure-type decomposition

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Decomp | "The 66 out-of-time failures" (heading copy) | `failure_decomposition.n_oot_positives`=66 | PASS | YES (literal in heading text) | "66" written into the section description string, not interpolated. Matches now; will drift if positives change. |
| Decomp | credit_visible 40, rate_liquidity 12, invisible 14 | `type_counts` (40/12/14) | PASS | NO | Loaded via `tc.get(...)`. |
| Decomp | invisible_positives count in caption | `invisible_positives`=14 | PASS | NO | Loaded. |
| Decomp | PR-AUC full 0.3014 (CI .191–.438) → addressable 0.3819 (CI .250–.530) on 52 addressable | `pr_auc_full`, `_ci`, `pr_auc_addressable`, `_ci`, `addressable_positives`=52 | PASS | NO | Loaded. |
| Decomp | "G0 ~6% power" in caption | `g0.gate_power` power_at_delta 0.02 = 0.055 | PASS | YES (literal "~6%") | Matches G0 (~5.5–6%). Hardcoded phrase. |
| Decomp | named banks (SVB, Signature, First Republic; Enloe, Heartland, Lindsay, Pulaski) | `failure_decomposition.mode_examples` | PASS | YES (names in copy) | Names match artifact's rate_liquidity/invisible lists. |

## Pooled-vs-addressable

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| PVA | lifts per family, count of families, lift_min/max | `pooled_vs_addressable` (5 models, lift_min 0.0406, lift_max 0.0805) | PASS | NO | Loaded; `len(models)`=5. |
| PVA | label-source sensitivity: addressable_external vs threshold, agreement | `decomp.external_labels` (0.3885 ext vs 0.3819, agreement 0.9242) | PASS | NO | Loaded. |

## GRU sequence challenger

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| GRU | GRU 0.2073 vs GBM 0.3014, delta -0.094 | `sequence_challenger` | PASS | NO | Loaded. |
| GRU | inner-val 0.6072, n_oot_positives 66 | `best_inner_val_pr_auc`, `n_oot_positives` | PASS | NO | Loaded. |
| GRU | robustness sweep: 6 configs, 0.1886–0.2458 | `robustness_sweep` | PASS | NO | Loaded. |
| GRU fig | GBM bootstrap CI band | `seq.gbm_pr_auc_ci` [0.1908,0.4380] | PASS | NO | Loaded. |

## Drift monitoring

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Drift | heading "Reference 2008-18 vs current 2019-26" | `viz.oot_window_start_year`=2019 | PASS | YES (literal years) | Hardcoded date span in heading; matches the panel era now, would drift. |
| Drift | 13/32 drifted (share 0.406); pred-drift 0.110 | `viz.drift_summary` (n_drifted 13, n_features 32, share 0.40625, pred_drift 0.1102) | PASS | NO | Loaded. |
| Drift | top-drifted features bar | `viz.drift_top_features` (5 entries) | PASS | NO | Loaded. |

## Robustness & validation cross-checks

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Maxout | caption: holdout {28}q, {66} positives | `maxout_experiment.holdout_quarters`=28, `test_positives`=66 | PASS | NO (fallback literals 28/66 match) | Loaded with `.get(...,28)/.get(...,66)` defaults that match. |
| Maxout | light baseline 0.1879 → bagged 0.2939 ("the served config") | `maxout.results.baseline_light.pr_auc`=0.1879, `bagged.pr_auc`=0.2939 | PASS (value); see note | NO | Values loaded correctly. NOTE: maxout's bagged=0.294 differs from the headline served 0.301 (different run/eval); copy calls bagged "the served config." Internally consistent with the artifact, but the two "served" numbers (0.294 vs 0.301) can read as a discrepancy to a careful viewer. Not a fact-check failure, a coherence caveat. |
| Calib bake-off | isotonic ECE 1.9e-04, platt 2.7e-04, venn-abers 6.6e-04; winner isotonic; flip rate 24% | `calibration_bakeoff.json` (0.00019/0.00027/0.00066, winner isotonic, flip 0.243) | PASS | NO | Loaded. |
| CBLR | mechanism, null rates 37% vs 0.3%, conclusion | `cblr_robustness.json` (null_2020plus 0.37, null_2019 0.003) | PASS | NO | Loaded. |
| CBLR fig | variants 0.250/0.250/0.085 | `cblr.variants[*].pr_auc_addressable_threshold` (0.2503/0.2503/0.0849) | PASS | NO | Loaded. |
| Competing risks | cause-specific 0.176 (CI .100–.281), Fine-Gray 0.182 (CI .102–.294) | `fine_gray.json` cause_specific 0.1755, fine_gray 0.1824 + CIs | PASS | NO | Loaded. |
| Competing risks | CIF failure 18.5%, merger 73.9% | `competing_risks.cumulative_incidence` (failure 0.18478, merger 0.73867) | PASS | NO | Loaded. NOTE page copy says "mergers ~4x more common" — 0.739/0.185 ≈ 4.0x, matches artifact note. |
| B1 | restated 0.176 (CI .100–.281), point-in-time 0.131 (CI .065–.230) | `b1_compare.json` fdic_restated.oot 0.1755, point_in_time.oot 0.1307 | PASS | NO | Loaded. |
| B1 | noncurrent field audit note, reconstruction corr 0.968 | `b1.noncurrent_field_audit.note`, `noncurrent_reconstruction.category_sum_vs_official_corr`=0.968 | PASS | NO | Loaded. |

## Static stack / decisions / administration / contracts

| Section | Displayed item | Source of truth | Current? | Hardcoded? | Evidence / fix |
|---|---|---|---|---|---|
| Stack | tool table (LightGBM, sklearn, SHAP, MLflow 3.x, skops, FastAPI, Evidently 0.7.x, DuckDB) | code reality / repo | PASS | YES (table literals) | Descriptive stack; version strings (MLflow 3.x, Evidently 0.7.x) are hardcoded and could drift from installed versions, low risk. |
| Contracts | "Feature contract (34 features)" | `len(MONOTONE_CONSTRAINTS)`=34 | PASS | NO | Computed live. |
| Contracts | SHAP importance + correlation figs, monotone table | `viz.shap_importance`, `viz.correlation`, live `MONOTONE_CONSTRAINTS` | PASS | NO | Loaded/live. |
| Decisions | bullet list of modeling choices, SR 11-7 framing | descriptive + MODEL_CARD.md | PASS | YES (text) | Descriptive, accurate to design. |
| Decisions | methodology doc expanders (6 docs) | `docs/ml/*.md` rendered live | PASS | NO | Read from files at render. |
| Admin | registry/promotion/retrain/rollback/$0 bullets + live code | descriptive + `registry` source via inspect | PASS | YES (text) | Code pulled live via `inspect.getsource`. |
| Notebook | embedded HTML | `ml/notebooks/bank_distress_analysis.html` | PASS | NO | Rendered from file. |

## Hardcoded literals inventory (drift risk)

Every hardcoded numeric/date literal in the displayed copy (the staleness surface):

1. **"448,661 bank-quarters"** — flow tile. Matches DB (448661) today. Highest drift risk: not derived from DB.
2. **"~8,800 banks"** — flow tile. DB=8803. Approximate, low risk.
3. **"2008–2026Q1"** — flow tile. Matches DB. Drifts when panel extends.
4. **"28-quarter holdout"** — flow tile literal (caption below uses loaded value). Matches `eval_window_quarters`=28.
5. **"66"** in failure-decomposition section heading string ("The 66 out-of-time failures..."). Matches `n_oot_positives`=66.
6. **"66 OOT positives"** in challenger-ladder caption (gap branch). Matches.
7. **"G0 ~6% power"** phrase in decomposition caption. Matches `gate_power` power_at_delta 0.02 ≈ 0.055.
8. **"Reference 2008-18 vs current 2019-26"** — drift section heading date span. Matches era; would drift.
9. **fallback literals**: `_nfail` fallback `66`, maxout `holdout_quarters` default `28`, `test_positives` default `66` — all currently match their artifacts (used only if key missing).
10. **Stack table version strings** "MLflow 3.x", "Evidently 0.7.x" — descriptive, could drift from installed versions.

No WRONG values found. No STALE (drifted) values found — every hardcoded literal currently matches its source of truth.
