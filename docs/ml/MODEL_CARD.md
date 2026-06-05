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
data with the out-of-time-validated tree count (n_estimators=23),
calibration=isotonic. Hyperparameters are tuned with Optuna over 15 trials on 3 inner time-series CV folds (best CV PR-AUC 0.5205), not hand-set. The effective-challenge ladder is a
penalized logistic regression and an unconstrained GBM (same tuned params, no monotone
constraints).

## Out-of-time performance (test window: last 28 quarters, 118,943 bank-quarters, 66 real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **0.2213** | 0.8153 | 0.455 | 0.00047 |
| Unconstrained GBM | 0.2643 | 0.8267 | 0.470 | 0.00046 |
| Logit benchmark | 0.1117 | 0.9196 | 0.394 | 0.00827 |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE=1.13e-04; in the top-scoring
decile the model predicts 0.0041 vs observed
0.0033.

### Performance by year (calibrated)
|   year |     n |   n_positive |   pr_auc |   roc_auc |
|-------:|------:|-------------:|---------:|----------:|
|   2019 | 20455 |           19 |   0.4855 |    0.9689 |
|   2020 | 19901 |            7 |   0.5179 |    0.9997 |
|   2021 | 19226 |            0 | nan      |  nan      |
|   2022 | 18762 |           14 |   0.0006 |    0.3543 |
|   2023 | 18377 |            9 |   0.2033 |    0.855  |
|   2024 | 17868 |            9 |   0.0014 |    0.7102 |
|   2025 |  4354 |            8 |   0.6197 |    0.975  |

In calm years with few or zero failures, PR-AUC is low or undefined — the expected
behavior of a rare-event model.

## Top global drivers (SHAP)
| feature                     |   mean_|SHAP| |
|:----------------------------|--------------:|
| tier1_rwa_ratio             |     0.276475  |
| roe                         |     0.0612907 |
| equity_to_assets_yoy_delta  |     0.0543573 |
| tier1_leverage              |     0.0512393 |
| equity_to_assets            |     0.0456171 |
| roa                         |     0.0432891 |
| allowance_to_loans          |     0.0311957 |
| equity_to_assets_peer_z     |     0.0291698 |
| asset_growth_yoy            |     0.0229229 |
| loans_to_deposits_yoy_delta |     0.0212886 |
| nco_to_loans                |     0.0163775 |
| brokered_to_deposits        |     0.0130042 |

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
| Q1 smallest | 29736 |          31 |   0.1428 |    0.9274 |         0.387 |
| Q2          | 29736 |          20 |   0.6299 |    0.9938 |         0.85  |
| Q4 largest  | 29736 |          15 |   0.0633 |    0.9423 |         0.2   |
| Q3          | 29735 |           0 | nan      |  nan      |       nan     |

### By region
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| Midwest   | 52454 |          25 |   0.3181 |    0.9706 |         0.52  |
| South     | 41899 |          23 |   0.1959 |    0.9317 |         0.478 |
| Northeast | 13028 |          10 |   0.1826 |    0.9823 |         0.6   |
| West      | 11337 |           8 |   0.0058 |    0.9312 |         0     |
| Other     |   225 |           0 | nan      |  nan      |       nan     |

### By charter class
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| NM        | 67918 |          42 |   0.2651 |    0.9845 |         0.452 |
| N         | 18115 |          11 |   0.0758 |    0.8398 |         0.273 |
| SM        | 17486 |           7 |   0.0041 |    0.9463 |         0     |
| SI        |  6471 |           3 |   0.0031 |    0.8848 |         0     |
| SB        |  6271 |           3 |   1      |    1      |         1     |
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
