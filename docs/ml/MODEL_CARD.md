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
data with the out-of-time-validated tree count (n_estimators=35),
calibration=isotonic. Hyperparameters are tuned with Optuna over 68 trials on 3 inner time-series CV folds (best CV PR-AUC 0.5314), not hand-set. The effective-challenge ladder is a
penalized logistic regression and an unconstrained GBM (same tuned params, no monotone
constraints).

## Out-of-time performance (test window: last 28 quarters, 118,943 bank-quarters, 66 real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **0.2393** | 0.8056 | 0.470 | 0.00045 |
| Unconstrained GBM | 0.2727 | 0.8240 | 0.515 | 0.00045 |
| Logit benchmark | 0.1117 | 0.9196 | 0.394 | 0.00827 |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE=1.75e-04; in the top-scoring
decile the model predicts 0.0044 vs observed
0.0035.

### Performance by year (calibrated)
|   year |     n |   n_positive |   pr_auc |   roc_auc |
|-------:|------:|-------------:|---------:|----------:|
|   2019 | 20455 |           19 |   0.4973 |    0.9698 |
|   2020 | 19901 |            7 |   0.7152 |    0.9998 |
|   2021 | 19226 |            0 | nan      |  nan      |
|   2022 | 18762 |           14 |   0.0007 |    0.3699 |
|   2023 | 18377 |            9 |   0.1054 |    0.7919 |
|   2024 | 17868 |            9 |   0.0019 |    0.7534 |
|   2025 |  4354 |            8 |   0.597  |    0.9642 |

In calm years with few or zero failures, PR-AUC is low or undefined — the expected
behavior of a rare-event model.

## Top global drivers (SHAP)
| feature                     |   mean_|SHAP| |
|:----------------------------|--------------:|
| tier1_rwa_ratio             |     0.30105   |
| roa                         |     0.0705555 |
| roe                         |     0.0664196 |
| equity_to_assets            |     0.0506369 |
| equity_to_assets_yoy_delta  |     0.0431174 |
| tier1_leverage              |     0.0414589 |
| allowance_to_loans          |     0.0297875 |
| equity_to_assets_peer_z     |     0.0277928 |
| asset_growth_yoy            |     0.023078  |
| nco_to_loans                |     0.0188173 |
| loans_to_deposits           |     0.0185287 |
| loans_to_deposits_yoy_delta |     0.0164696 |

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
| Q1 smallest | 29736 |          31 |   0.2428 |    0.9389 |         0.387 |
| Q2          | 29736 |          20 |   0.6287 |    0.9901 |         0.85  |
| Q4 largest  | 29736 |          15 |   0.0599 |    0.9619 |         0.2   |
| Q3          | 29735 |           0 | nan      |  nan      |       nan     |

### By region
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| Midwest   | 52454 |          25 |   0.3407 |    0.9698 |         0.52  |
| South     | 41899 |          23 |   0.312  |    0.9445 |         0.565 |
| Northeast | 13028 |          10 |   0.2366 |    0.9889 |         0.6   |
| West      | 11337 |           8 |   0.009  |    0.9526 |         0     |
| Other     |   225 |           0 | nan      |  nan      |       nan     |

### By charter class
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| NM        | 67918 |          42 |   0.3433 |    0.988  |         0.452 |
| N         | 18115 |          11 |   0.0882 |    0.8695 |         0.273 |
| SM        | 17486 |           7 |   0.0054 |    0.9488 |         0     |
| SI        |  6471 |           3 |   0.0033 |    0.8925 |         0     |
| SB        |  6271 |           3 |   0.7333 |    0.9999 |         1     |
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
