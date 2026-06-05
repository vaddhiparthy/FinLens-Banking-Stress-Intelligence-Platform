# B1 - Originally-Filed Point-in-Time Features (findings)

**Status: feasible and validated for 2014+, and it surfaced a FinLens feature-mapping
bug (noncurrent built from the wrong field, now fixed), but the full-history
point-in-time retrain currently UNDERPERFORMS the restated panel. The
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

## Real finding: a FinLens feature-mapping bug (now fixed)
This is NOT an FDIC data bug; it is a FinLens field-selection error that the
point-in-time path surfaced. FinLens's `noncurrent_to_loans` was built from FDIC
`P9LNLS`, which is **loans 90+ days past due AND STILL ACCRUING only** - not total
noncurrent. P9LNLS is zero for **49.7%** of bank-quarters, which is economically NORMAL:
sound banks place troubled loans on nonaccrual, removing them from the accruing-90+
bucket, so a zero in a given quarter is expected. **Total noncurrent = nonaccrual +
90+-days-past-due = FDIC `NCLNLS`** (zero-rate **10.8%**), which FDIC publishes and the
codebase already fetched (`ingestion/fdic_institutions.py`). The point-in-time RC-N
path summed nonaccrual (1403) + 90+ (1407) - the correct total-noncurrent definition -
which is what exposed the mismatch (`b1_compare.json` -> `noncurrent_field_audit`).

**Fix applied:** `ml/finlens_ml/features.py` now builds `noncurrent_to_loans` from
NCLNLS, and the served model is retrained on the corrected feature (OOT PR-AUC
0.221 -> 0.273, recall@200 47% -> 54.5%), so the FDIC and point-in-time noncurrent
definitions are now apples-to-apples.

## Why the full retrain underperforms (honest)
Same recipe, same OOT protocol, only the data source differs
(`ml/scripts/b1_compare.py`):

(Same recipe with default params on both panels, to isolate the data-source effect;
the served model is separately tuned to 0.273.)

| panel | OOT PR-AUC | 95% CI |
|---|---|---|
| FDIC restated (shipped, NCLNLS noncurrent) | 0.176 | [0.100, 0.281] |
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
- Independent of point-in-time, the FinLens noncurrent feature-mapping bug
  (P9LNLS instead of NCLNLS) it surfaced has been fixed in the served model.
