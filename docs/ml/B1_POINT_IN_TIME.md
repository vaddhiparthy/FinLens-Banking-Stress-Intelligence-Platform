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

This was retested AFTER the noncurrent feature was made correct on BOTH panels (so the
comparison is clean, not confounded by the field bug):

| panel | OOT PR-AUC | 95% CI |
|---|---|---|
| FDIC restated (shipped, NCLNLS noncurrent) | 0.176 | [0.100, 0.281] |
| point-in-time (corrected noncurrent) | 0.131 | [0.065, 0.230] |

Fixing noncurrent narrowed the gap (point-in-time rose 0.10 -> 0.131) but did **not**
close it. The CIs overlap heavily, so the difference is not itself significant, but the
point estimate consistently favours restated. Two real causes remain:
1. **Pre-2017 noncurrent has no originally-filed total.** The RC-N total-noncurrent
   codes (1403 nonaccrual + 1407 90+) exist only from 2017Q1; a pre-2017 per-category
   sum double-counts RC-N's hierarchical sub-lien and memoranda items (verified: it
   over- or under-counts vs the 2017+ official total, corr ~0.93-0.97 but wrong scale,
   with NO FFIEC ground truth to calibrate against). So pre-2017 noncurrent is filled
   from FDIC's published `NCLNLS` total - the one feature that is not pure
   point-in-time pre-2017 (see `noncurrent_field_audit` / `noncurrent_reconstruction`
   in `b1_compare.json`). Forward (live) scoring is unaffected: the current quarter is
   2017+ and uses the originally-filed FFIEC total.
2. **Restated data is cleaner.** Restatements fix filing errors, so originally-filed
   values are inherently noisier and train a slightly worse model even where complete.
   This is a fundamental property, not a bug, and is why point-in-time may never beat
   restated as a *training* source.

## Decision (after a fair retest)
- The served TRAINING model stays on the FDIC-restated panel + Tier A. The fair retest
  (noncurrent corrected on both sides) shows point-in-time still underperforms as a
  training source (0.131 vs 0.176), and the residual gap is the fundamental
  originally-filed-is-noisier effect, which more ETL will not remove. So shipping the
  point-in-time panel as the training source would knowingly ship a worse model.
- **But B1 is not shelved - it is used where it is genuinely correct:** forward (live)
  scoring of the current quarter MUST use originally-filed values (no restatement
  exists yet), which is exactly the FFIEC point-in-time path. The Early Warning "Live
  forward score" tab is the realisation of B1 for the one place point-in-time is not
  optional.
- B1 also already paid off once: it surfaced the noncurrent field bug (P9LNLS vs
  NCLNLS), and fixing that lifted the shipped model 0.221 -> 0.273.
- Genuinely remaining (honest): a pure originally-filed pre-2017 total-noncurrent does
  not exist in FFIEC (no total line, no ground truth to validate a reconstruction);
  pre-2017 noncurrent therefore uses FDIC's restated total. Closing that would require
  an external originally-filed source we do not have at $0.
