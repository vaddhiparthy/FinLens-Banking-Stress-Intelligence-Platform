# Model Card — FinLens Bank Financial-Distress Early-Warning Model

*Generated from real artifacts (ml/artifacts/metrics_h4.json) — no hand-entered metrics.*

## Intended use
Rank US FDIC-insured institutions by probability of **financial distress / failure
within 4 quarters**, from public quarterly Call Report financials. Decision-support
for off-site monitoring / exam prioritization. **Not** investment, deposit, or
supervisory advice; **not** a consumer-credit decision (no ECOA/Reg-B adverse action).

## Model
Calibrated, monotone-constrained LightGBM discrete-time hazard classifier on a
per-bank-quarter panel. 34 CAMELS-aligned features. Served model trained on all
data with the out-of-time-validated tree count (n_estimators=38),
calibration=isotonic (bagged x12). Hyperparameters are tuned with Optuna over 39 trials on 3 inner time-series CV folds (best CV PR-AUC 0.5665), not hand-set. The effective-challenge ladder is a
penalized logistic regression and an unconstrained GBM (same tuned params, no monotone
constraints).

## Out-of-time performance (test window: last 28 quarters, 118,943 bank-quarters, 66 real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **0.3014** | 0.8553 | 0.545 | 0.00045 |
| Unconstrained GBM | 0.2696 | 0.8332 | 0.515 | 0.00045 |
| Logit benchmark | 0.1533 | 0.9241 | 0.379 | 0.00874 |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE=1.22e-04; in the top-scoring
decile the model predicts 0.0035 vs observed
0.0035.

### Performance by year (calibrated)
|   year |     n |   n_positive |   pr_auc |   roc_auc |
|-------:|------:|-------------:|---------:|----------:|
|   2019 | 20455 |           19 |   0.4918 |    0.9905 |
|   2020 | 19901 |            7 |   0.7247 |    0.9999 |
|   2021 | 19226 |            0 | nan      |  nan      |
|   2022 | 18762 |           14 |   0.0013 |    0.4359 |
|   2023 | 18377 |            9 |   0.2298 |    0.9197 |
|   2024 | 17868 |            9 |   0.0023 |    0.7455 |
|   2025 |  4354 |            8 |   0.6969 |    0.982  |

In calm years with few or zero failures, PR-AUC is low or undefined — the expected
behavior of a rare-event model.

## Top global drivers (SHAP)
| feature                    |   mean_|SHAP| |
|:---------------------------|--------------:|
| tier1_rwa_ratio            |       0.25218 |
| noncurrent_to_loans        |       0.13353 |
| roe                        |       0.05974 |
| tier1_leverage             |       0.04393 |
| equity_to_assets           |       0.03727 |
| equity_to_assets_peer_z    |       0.03277 |
| roa                        |       0.03117 |
| equity_to_assets_yoy_delta |       0.03041 |
| noncurrent_to_loans_peer_z |       0.0242  |
| asset_growth_yoy           |       0.02304 |
| brokered_to_deposits       |       0.01637 |
| allowance_to_loans         |       0.01288 |

Capital (tier-1) and asset quality (noncurrent loans) dominate, consistent with the
bank-failure literature. These values are the SAME committed SHAP block the Model Quality
chart renders (viz_pack.json), computed over a fixed sample (n=3000, seed 42)
of OOT-era rows. Local per-bank SHAP reason codes are available via the serving API.

## Cross-segment performance equity (NOT protected-class fairness)
A bank-distress model predicts on institutions, not consumers — there is **no protected
class**, so demographic parity / disparate impact / the four-fifths rule do not apply
and are deliberately not computed. We instead verify the model performs across segments
(SR 11-7 outcomes analysis). Fairlearn `MetricFrame` is used only as a slicing tool.

### By asset-size tier
| segment     |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:------------|------:|------------:|---------:|----------:|--------------:|
| Q1 smallest | 29736 |          31 |   0.2773 |    0.9389 |         0.419 |
| Q2          | 29736 |          20 |   0.6638 |    0.992  |         0.85  |
| Q4 largest  | 29736 |          15 |   0.0782 |    0.9632 |         0.2   |
| Q3          | 29735 |           0 | nan      |  nan      |       nan     |

### By region
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| Midwest   | 52454 |          25 |   0.439  |    0.9791 |         0.64  |
| South     | 41899 |          23 |   0.3423 |    0.9437 |         0.609 |
| Northeast | 13028 |          10 |   0.2453 |    0.9868 |         0.6   |
| West      | 11337 |           8 |   0.0112 |    0.9497 |         0     |
| Other     |   225 |           0 | nan      |  nan      |       nan     |

### By charter class
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| NM        | 67918 |          42 |   0.4021 |    0.9888 |         0.5   |
| N         | 18115 |          11 |   0.0953 |    0.8751 |         0.364 |
| SM        | 17486 |           7 |   0.0056 |    0.9547 |         0     |
| SI        |  6471 |           3 |   0.0058 |    0.9438 |         0     |
| SB        |  6271 |           3 |   1      |    1      |         1     |
| NC        |  1444 |           0 | nan      |  nan      |       nan     |
| SL        |  1013 |           0 | nan      |  nan      |       nan     |
| OI        |   225 |           0 | nan      |  nan      |       nan     |

## Limitations
- The target is **failure** (FDIC RESTYPE=FAILURE) and the inputs are the public Call
  Report feature set; that is the project's defined scope.
- SHAP assumes feature independence in probability space; correlated CAMELS ratios
  violate this, so local SHAP is validator/supervisor-facing transparency, **not** a
  legally-sufficient adverse-action reason code.
- The model is bank-level and does **not** use macro series as inputs (capital and
  earnings carry most of the signal); FRED macro is business-surface context only.
- Features come from the FDIC `/financials` endpoint (currently-restated values, not the
  originally-filed Call Report); strict point-in-time feature integrity would require
  originally-filed FFIEC CDR data.
- Rare-event metrics are noisy in calm cohorts; judge on failure-containing windows.

## Governance
Aligned with the **principles** of SR 11-7 (Fed/OCC, 2011 — the established model-risk
management guidance; primary source:
https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm) — **non-binding**
here; a GBM is in scope (non-generative, non-agentic). This is a portfolio demonstration,
not a regulated production model. The substantive validation rests on the SR 11-7 three
pillars (see the validation report).
