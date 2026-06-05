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
calibration=isotonic. Hyperparameters are tuned with Optuna over 39 trials on 3 inner time-series CV folds (best CV PR-AUC 0.5665), not hand-set. The effective-challenge ladder is a
penalized logistic regression and an unconstrained GBM (same tuned params, no monotone
constraints).

## Out-of-time performance (test window: last 28 quarters, 118,943 bank-quarters, 66 real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **0.2728** | 0.8170 | 0.545 | 0.00045 |
| Unconstrained GBM | 0.2696 | 0.8332 | 0.515 | 0.00045 |
| Logit benchmark | 0.1533 | 0.9241 | 0.379 | 0.00874 |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE=1.15e-04; in the top-scoring
decile the model predicts 0.0034 vs observed
0.0034.

### Performance by year (calibrated)
|   year |     n |   n_positive |   pr_auc |   roc_auc |
|-------:|------:|-------------:|---------:|----------:|
|   2019 | 20455 |           19 |   0.4766 |    0.9692 |
|   2020 | 19901 |            7 |   0.7357 |    0.9999 |
|   2021 | 19226 |            0 | nan      |  nan      |
|   2022 | 18762 |           14 |   0.0011 |    0.371  |
|   2023 | 18377 |            9 |   0.1451 |    0.8864 |
|   2024 | 17868 |            9 |   0.0015 |    0.7342 |
|   2025 |  4354 |            8 |   0.6744 |    0.9581 |

In calm years with few or zero failures, PR-AUC is low or undefined — the expected
behavior of a rare-event model.

## Top global drivers (SHAP)
| feature                       |   mean_|SHAP| |
|:------------------------------|--------------:|
| tier1_rwa_ratio               |     0.279822  |
| noncurrent_to_loans           |     0.139644  |
| roe                           |     0.0598917 |
| tier1_leverage                |     0.0476549 |
| equity_to_assets              |     0.0384824 |
| equity_to_assets_peer_z       |     0.034269  |
| equity_to_assets_yoy_delta    |     0.0315959 |
| roa                           |     0.0308507 |
| noncurrent_to_loans_peer_z    |     0.0249119 |
| asset_growth_yoy              |     0.0223168 |
| allowance_to_loans            |     0.0145932 |
| noncurrent_to_loans_yoy_delta |     0.0142737 |

Capital (tier-1) and earnings (ROA) dominate, consistent with the bank-failure
literature. Computed as mean |SHAP| over a fixed reservoir sample (n=1500, seed 42)
of OOT-era rows. Local per-bank SHAP reason codes are available via the serving API.

## Cross-segment performance equity (NOT protected-class fairness)
A bank-distress model predicts on institutions, not consumers — there is **no protected
class**, so demographic parity / disparate impact / the four-fifths rule do not apply
and are deliberately not computed. We instead verify the model performs across segments
(SR 11-7 outcomes analysis). Fairlearn `MetricFrame` is used only as a slicing tool.

### By asset-size tier
| segment     |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:------------|------:|------------:|---------:|----------:|--------------:|
| Q1 smallest | 29736 |          31 |   0.2199 |    0.9297 |         0.419 |
| Q2          | 29736 |          20 |   0.68   |    0.9893 |         0.85  |
| Q4 largest  | 29736 |          15 |   0.0435 |    0.9165 |         0.2   |
| Q3          | 29735 |           0 | nan      |  nan      |       nan     |

### By region
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| Midwest   | 52454 |          25 |   0.3484 |    0.97   |         0.64  |
| South     | 41899 |          23 |   0.3014 |    0.9383 |         0.609 |
| Northeast | 13028 |          10 |   0.1953 |    0.9688 |         0.6   |
| West      | 11337 |           8 |   0.0042 |    0.9006 |         0     |
| Other     |   225 |           0 | nan      |  nan      |       nan     |

### By charter class
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| NM        | 67918 |          42 |   0.3599 |    0.9799 |         0.5   |
| N         | 18115 |          11 |   0.0617 |    0.8621 |         0.273 |
| SM        | 17486 |           7 |   0.0027 |    0.9165 |         0     |
| SI        |  6471 |           3 |   0.0023 |    0.8911 |         0     |
| SB        |  6271 |           3 |   0.5    |    0.9997 |         1     |
| NC        |  1444 |           0 | nan      |  nan      |       nan     |
| SL        |  1013 |           0 | nan      |  nan      |       nan     |
| OI        |   225 |           0 | nan      |  nan      |       nan     |

## Limitations
- Public-data label is **failure** (FDIC RESTYPE=FAILURE); per-bank CAMELS exam ratings
  are confidential and not used. The model cannot see supervisory/liquidity internals.
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
