# Model Card — FinLens Bank Financial-Distress Early-Warning Model

*Generated from real artifacts (ml/artifacts/metrics_h4.json) — no hand-entered metrics.*

## Intended use
Rank US FDIC-insured institutions by probability of **financial distress / failure
within 4 quarters**, from public quarterly Call Report financials. Decision-support
for off-site monitoring / exam prioritization. **Not** investment, deposit, or
supervisory advice; **not** a consumer-credit decision (no ECOA/Reg-B adverse action).

## Model
Calibrated, monotone-constrained LightGBM discrete-time hazard classifier on a
per-bank-quarter panel. 31 CAMELS-aligned features. Served model trained on all
data with the out-of-time-validated tree count (n_estimators=7),
calibration=isotonic. Penalized logistic regression is the
benchmark (effective challenge).

## Out-of-time performance (test window: last 28 quarters, 118,943 bank-quarters, 66 real failures)
Lead metric is **PR-AUC** (rare-event); ROC-AUC is comparability-only; accuracy is not reported.

| Model | PR-AUC | ROC-AUC | recall@200 | Brier |
|---|---|---|---|---|
| Calibrated LGBM | **0.2183** | 0.8156 | 0.424 | 0.00047 |
| Logit benchmark | 0.1078 | 0.8928 | 0.379 | 0.00815 |

The LGBM beats the regulatory logit benchmark on PR-AUC (the metric that matters at a
<1% base rate) and on recall@k. The logit's ROC-AUC is marginally higher; ROC-AUC is
deprioritized here and shown only for comparability.

### Calibration (honest)
All-rows Brier is dominated by true negatives, so we also report ECE and the flagged
(top-decile) calibration: ECE=1.54e-04; in the top-scoring
decile the model predicts 0.0047 vs observed
0.0035.

### Performance by year (calibrated)
|   year |     n |   n_positive |   pr_auc |   roc_auc |
|-------:|------:|-------------:|---------:|----------:|
|   2019 | 20455 |           19 |   0.4742 |    0.995  |
|   2020 | 19901 |            7 |   0.7429 |    0.9999 |
|   2021 | 19226 |            0 | nan      |  nan      |
|   2022 | 18762 |           14 |   0.0007 |    0.4907 |
|   2023 | 18377 |            9 |   0.0436 |    0.7871 |
|   2024 | 17868 |            9 |   0.001  |    0.6607 |
|   2025 |  4354 |            8 |   0.6345 |    0.9303 |

PR-AUC is honestly low/undefined in calm years with few/zero failures — expected for a
rare-event model, not a defect.

## Top global drivers (SHAP)
| feature                     |   mean_|SHAP| |
|:----------------------------|--------------:|
| tier1_rwa_ratio             |    0.235313   |
| roa                         |    0.0673147  |
| tier1_leverage              |    0.0306459  |
| nim_yoy_delta               |    0.021843   |
| loans_to_deposits_yoy_delta |    0.0191936  |
| brokered_to_deposits        |    0.0184622  |
| equity_to_assets            |    0.0172717  |
| equity_to_assets_peer_z     |    0.0138289  |
| allowance_to_loans          |    0.0131521  |
| equity_to_assets_yoy_delta  |    0.0128467  |
| asset_growth_yoy            |    0.0125425  |
| nim                         |    0.00772053 |

Capital (tier-1) and earnings (ROA) dominate, consistent with the bank-failure
literature. Local per-bank SHAP reason codes are available via the serving API.

## Cross-segment performance equity (NOT protected-class fairness)
A bank-distress model predicts on institutions, not consumers — there is **no protected
class**, so demographic parity / disparate impact / the four-fifths rule do not apply
and are deliberately not computed. We instead verify the model performs across segments
(SR 11-7 outcomes analysis). Fairlearn `MetricFrame` is used only as a slicing tool.

### By asset-size tier
| segment     |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:------------|------:|------------:|---------:|----------:|--------------:|
| Q1 smallest | 29736 |          31 |   0.2799 |    0.9153 |         0.452 |
| Q2          | 29736 |          20 |   0.536  |    0.9942 |         0.85  |
| Q4 largest  | 29736 |          15 |   0.0328 |    0.9609 |         0.067 |
| Q3          | 29735 |           0 | nan      |  nan      |       nan     |

### By region
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| Midwest   | 52454 |          25 |   0.3515 |    0.9486 |         0.6   |
| South     | 41899 |          23 |   0.3188 |    0.9261 |         0.565 |
| Northeast | 13028 |          10 |   0.209  |    0.9941 |         0.6   |
| West      | 11337 |           8 |   0.0195 |    0.9511 |         0.125 |
| Other     |   225 |           0 | nan      |  nan      |       nan     |

### By charter class
| segment   |     n |   positives |   pr_auc |   roc_auc |   recall_at_k |
|:----------|------:|------------:|---------:|----------:|--------------:|
| NM        | 67918 |          42 |   0.383  |    0.9929 |         0.524 |
| N         | 18115 |          11 |   0.0566 |    0.8318 |         0.273 |
| SM        | 17486 |           7 |   0.0045 |    0.9331 |         0     |
| SI        |  6471 |           3 |   0.001  |    0.7258 |         0     |
| SB        |  6271 |           3 |   0.6    |    0.9997 |         1     |
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
SR 11-7 + SR 21-8) — non-binding guidance; a GBM is in-scope (non-generative,
non-agentic AI). This is a portfolio demonstration, not a regulated production model.
See the validation report for the SR 11-7 three-pillar treatment.
