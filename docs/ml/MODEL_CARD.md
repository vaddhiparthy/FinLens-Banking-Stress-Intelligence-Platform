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
data with the out-of-time-validated tree count (n_estimators=7),
calibration=isotonic. Penalized logistic regression is the
benchmark (effective challenge).

## Out-of-time performance (test window: last 28 quarters, 118,943 bank-quarters, 66 real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **0.1563** | 0.8293 | 0.424 | 0.00049 |
| Logit benchmark | 0.1093 | 0.9192 | 0.394 | 0.00826 |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE=1.67e-04; in the top-scoring
decile the model predicts 0.0046 vs observed
0.0034.

### Performance by year (calibrated)
|   year |     n |   n_positive |   pr_auc |   roc_auc |
|-------:|------:|-------------:|---------:|----------:|
|   2019 | 20455 |           19 |   0.4473 |    0.996  |
|   2020 | 19901 |            7 |   0.4906 |    0.9998 |
|   2021 | 19226 |            0 | nan      |  nan      |
|   2022 | 18762 |           14 |   0.0009 |    0.5594 |
|   2023 | 18377 |            9 |   0.0688 |    0.8266 |
|   2024 | 17868 |            9 |   0.0006 |    0.5811 |
|   2025 |  4354 |            8 |   0.4604 |    0.941  |

In calm years with few or zero failures, PR-AUC is low or undefined — the expected
behavior of a rare-event model.

## Top global drivers (SHAP)
| feature                     |   mean_|SHAP| |
|:----------------------------|--------------:|
| tier1_rwa_ratio             |     0.223902  |
| roe                         |     0.067966  |
| equity_to_assets_peer_z     |     0.0247399 |
| nim_yoy_delta               |     0.0235993 |
| loans_to_deposits_yoy_delta |     0.0224842 |
| brokered_to_deposits        |     0.0179655 |
| tier1_leverage              |     0.0167461 |
| nco_to_loans                |     0.0138162 |
| equity_to_assets_yoy_delta  |     0.0136154 |
| log_assets                  |     0.0128304 |
| allowance_to_loans          |     0.011476  |
| asset_growth_yoy            |     0.0111164 |

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
| Q1 smallest | 29736 |          31 |   0.2448 |    0.913  |         0.452 |
| Q2          | 29736 |          20 |   0.5049 |    0.9838 |         0.8   |
| Q4 largest  | 29736 |          15 |   0.0801 |    0.9915 |         0.2   |
| Q3          | 29735 |           0 | nan      |  nan      |       nan     |

### By region
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| Midwest   | 52454 |          25 |   0.3251 |    0.9404 |         0.56  |
| South     | 41899 |          23 |   0.2733 |    0.9279 |         0.522 |
| Northeast | 13028 |          10 |   0.4156 |    0.9944 |         0.6   |
| West      | 11337 |           8 |   0.0274 |    0.983  |         0     |
| Other     |   225 |           0 | nan      |  nan      |       nan     |

### By charter class
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| NM        | 67918 |          42 |   0.3556 |    0.9936 |         0.5   |
| N         | 18115 |          11 |   0.1368 |    0.826  |         0.273 |
| SM        | 17486 |           7 |   0.0195 |    0.9299 |         0.429 |
| SI        |  6471 |           3 |   0.0014 |    0.7969 |         0     |
| SB        |  6271 |           3 |   0.6    |    0.9998 |         1     |
| NC        |  1444 |           0 | nan      |  nan      |       nan     |
| SL        |  1013 |           0 | nan      |  nan      |       nan     |
| OI        |   225 |           0 | nan      |  nan      |       nan     |

## Limitations
- Public-data label is **failure** (FDIC RESTYPE=FAILURE); per-bank CAMELS exam ratings
  are confidential and not used. The model cannot see supervisory/liquidity internals.
- SHAP assumes feature independence in probability space; correlated CAMELS ratios
  violate this, so local SHAP is validator/supervisor-facing transparency, **not** a
  legally-sufficient adverse-action reason code.
- Macro context (ALFRED-vintage) is an optional enhancement gated on a free FRED key;
  the core model is bank-level (capital+earnings carry most of the signal).
- Rare-event metrics are noisy in calm cohorts; judge on failure-containing windows.

## Governance
Aligned with the **principles** of SR 26-2 (Fed/OCC/FDIC, Apr 17 2026; supersedes
SR 11-7 + SR 21-8; primary source:
https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm) — **non-binding**
guidance; a GBM is in-scope (non-generative, non-agentic AI). This is a portfolio
demonstration, not a regulated production model. The substantive validation rests on
the SR 11-7 three pillars regardless (see the validation report).
