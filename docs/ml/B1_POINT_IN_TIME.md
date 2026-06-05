# B1 - Originally-Filed Point-in-Time Features (findings)

**Status: feasible and validated for 2014+, surfaced a real FDIC data bug, but the
full-history point-in-time retrain currently UNDERPERFORMS the restated panel. The
shipped model therefore stays on the FDIC-restated panel + Tier A; the point-in-time
feed is a validated capability and the remaining accuracy lever, not yet integrated.**

This is the honest outcome of the committee-certified plan's B1 line item (the one it
ranked as the only true accuracy lever). We do not claim a win we did not measure.

## What B1 is
The shipped features come from the FDIC `/financials` endpoint, which serves
currently-RESTATED values. B1 sources the ORIGINALLY-FILED FFIEC Call Reports (CDR
Public Data Distribution) so each quarter's features are as the bank actually filed
them, removing restatement look-ahead.

## Feasibility (GO)
- The FFIEC CDR bulk "Call Reports -- Single Period" downloads at $0 via a 3-step
  ASP.NET postback (`ml/scripts/b1_download.py`). 73 quarters 2008Q1-2026Q1 pulled
  (544 MB). The POR schedule carries `IDRSSD` + `FDIC Certificate Number`, so the
  RSSD->CERT crosswalk ships inside the bulk file.
- Parser: `ml/finlens_ml/ffiec_pit.py` maps MDRM codes (RC, RI, RC-N, RC-R, RC-K,
  RC-B, RC-E, RC-O) to the existing feature schema, preferring consolidated (RCFD/
  RCFA) with domestic (RCON/RCOA) fallback, and re-derives FDIC ratios (ROA, NIM,
  efficiency, NCO) with transparent formulas (YTD income annualized over RC-K average
  assets); capital ratios use the bank-reported RC-R values.

## Validation (2014+: near-exact)
Reconciled against the FDIC panel for 2025Q4 (4,393 banks). Correlations:
equity_to_assets 1.000, tier1_rwa_ratio 1.000, tier1_leverage 1.000, HTM/AFS 1.000,
roa 0.991, efficiency 0.998, allowance 0.992, loans_to_deposits 0.987, brokered
1.000, uninsured 0.943. (roe/nim slightly lower by transparent avg-equity/avg-earning-
assets convention.)

## Real finding: FDIC's stored noncurrent is broken
The FDIC `/financials` `P9LNLS` (noncurrent loans) used by the shipped panel is **zero
for 48.1% of bank-quarters** - implausibly high for "no noncurrent loans." The
point-in-time RC-N values (nonaccrual + 90-days-past-due) populate it far more fully:
zero-rate **14.8%** (`ml/artifacts/b1_compare.json`: `fdic_frac_zero` 0.481 vs
`pit_frac_zero` 0.148). Where FDIC does report a non-zero value the two rank-agree.
This is a genuine data-quality gap in the shipped panel that B1 exposes.

## Why the full retrain underperforms (honest)
Same recipe, same OOT protocol, only the data source differs
(`ml/scripts/b1_compare.py`):

| panel | OOT PR-AUC | 95% CI |
|---|---|---|
| FDIC restated (shipped) | 0.194 | [0.106, 0.320] |
| point-in-time (full history) | 0.100 | [0.050, 0.174] |

Two causes, both real:
1. **Pre-2014 schema drift.** The Basel-III RC-R ratios and the RC-N total-noncurrent
   codes only exist 2014+. Pre-2014 capital is recoverable (RCON fallback, now ~98%
   filled), but pre-2014 noncurrent has NO total line; a label-based per-category sum
   is rank-correct (corr 0.968 vs the 2014+ official total) but **magnitude-light
   (~0.40x; `ml/artifacts/b1_compare.json` `noncurrent_reconstruction`)**, creating a
   level shift across the 2014 boundary. Since 88% of the
   failures are 2008-2012, training on a feature-sparse / level-shifted crisis era
   collapses OOT performance.
2. **Restated data is cleaner.** Restatements fix filing errors, so originally-filed
   values are noisier and train a slightly worse model even where complete.

## Decision and remaining work
- The served model stays on the FDIC-restated panel + Tier A improvements.
- B1 is a validated capability and the documented remaining lever. To realize it:
  complete the pre-2014 noncurrent MAGNITUDE reconstruction (per-category MDRM mapping
  across schema vintages, validated to the 2014+ official total within tolerance), and
  re-run `b1_compare`. Until that closes the 2014 level shift, point-in-time does not
  beat restated and is not shipped.
- Independent of the model, the FDIC-noncurrent bug finding is reported as-is.
