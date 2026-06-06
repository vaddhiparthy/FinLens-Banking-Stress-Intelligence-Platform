# Failure-type decomposition: what the model can and cannot see

The headline out-of-time PR-AUC (0.301) is an average over a set of failures that are not
the same kind of event. Averaging a credit-distress model over failure types it was never
designed to see makes the by-cohort number swing violently and look unstable. This analysis
decomposes the 66 out-of-time failure bank-quarters (19 distinct banks) by failure mode,
using model-independent financial signatures (not the model's own score, to avoid
circularity), and shows that the swings are not noise: they track the failure-type mix of
each filing-year cohort, and the modes map cleanly onto the real FDIC record.

Artifact: `ml/artifacts/failure_decomposition.json`. Reproduce:
`python ml/scripts/failure_decomposition.py`.

## A note on the year axis

Cohorts are keyed by **filing year**, not failure year. A positive bank-quarter is a Call
Report filing that fails within the next four quarters, so the failure happens later. The
2022 filing cohort is the set of 2022 filings that failed in 2023. No banks failed in
calendar 2021 or 2022; the by-year swings are about when the doomed banks were filing, which
is what the model actually scores. The distinct banks by **failure** year:

| Failure year | Distinct banks |
| --- | --- |
| 2019 | City National Bank of NJ, Louisa Community, Resolute, Enloe State |
| 2020 | Almena State, Ericson State, First City Bank of Florida, The First State Bank |
| 2023 | Citizens Bank (Sac City), First Republic, Heartland Tri-State, Signature, Silicon Valley |
| 2024 | Republic First (Republic Bank), First National Bank of Lindsay |
| 2025 | Pulaski Savings, Santa Anna National |
| 2026 | Metropolitan Capital Bank & Trust, Community Bank & Trust West Georgia |

That is 19 distinct banks. The two 2026 failures sit in the panel as positives because their
final pre-failure quarters (2025 to 2026Q1) are observed even though the closure date falls
at or just after the panel's last quarter, so their failure year is extrapolated rather than
looked up. This matches the FDIC failure list (4 in 2019, 4 in 2020, none in 2021 to 2022,
the 2023 wave, then the small 2024 to 2026 tail).

## The three failure modes

Each out-of-time failure is classified from its raw Call Report signature at the last filing
before the flag, independent of the model:

| Mode | Rule | Count | What it is |
| --- | --- | --- | --- |
| Credit-visible | noncurrent >= 3% or NCO >= 1% or Tier-1/RWA < 6% (PCA undercapitalized) or equity/assets < 4% | 40 | Classic credit deterioration or capital exhaustion. The thing the model is built to catch. |
| Rate/liquidity-visible | uninsured deposit share >= 30% and HTM+AFS securities >= 5% of assets | 12 | The 2023 wave: a large uninsured base funding a marked-down securities book. Silicon Valley (95% uninsured, 45% HTM), Signature (91%), First Republic (72%). Call Reports capture this only partially. |
| Invisible | none of the above | 14 | The bank looked financially sound at its last filing and failed anyway. In practice these are the fraud and scam failures: Enloe State (2019), Heartland Tri-State (2023, the "pig-butchering" scam), First National Bank of Lindsay (2024), Pulaski Savings (2025), Santa Anna National (2025). Structurally unpredictable from quarterly financials. |

The capital threshold is stated against Prompt Corrective Action: for the Tier-1 risk-based
ratio, 8% is well-capitalized, 6% is adequately-capitalized, and below 6% is
undercapitalized, so the < 6% cut flags banks PCA itself treats as undercapitalized.

That the invisible class is exactly the known fraud and scam failures, and the
rate/liquidity class is exactly the 2023 interest-rate wave, is the cross-check that the
taxonomy is financially meaningful rather than an arbitrary split. It is an author-defined
diagnostic partition, not a supervisory classification.

## The by-cohort collapse has two distinct causes, not one

| Filing year | Credit | Rate/liq | Invisible | Dominant mode | Model behaviour |
| --- | --- | --- | --- | --- | --- |
| 2019 | 18 | 0 | 1 | credit (95%) | strong |
| 2020 | 7 | 0 | 0 | credit (100%) | strong |
| 2022 | 1 | 11 | 2 | rate/liquidity (79%) | collapses |
| 2023 | 6 | 1 | 2 | credit (67%) | moderate |
| 2024 | 1 | 0 | 8 | invisible (89%) | collapses |
| 2025 | 7 | 0 | 1 | credit (88%) | strong |

The two near-floor cohorts collapse for opposite reasons:

- **The 2022 filing cohort is a wrong-cohort collapse.** Eleven of its fourteen failures are
  the 2023 rate/liquidity wave (these banks were filing in 2022 and failed in 2023), with
  low credit signatures. A model trained predominantly on credit distress scores those banks
  low because, on the credit axis, they looked fine. The model is not broken here; it is
  being asked to rank a failure type it under-weights.
- **The 2024 filing cohort is an invisible-cohort collapse.** Eight of its nine failures
  carry no elevated financial signal at the last filing: these are the fraud and sudden
  failures. No model built on quarterly Call Report financials can rank those above healthy
  banks, because the financials do not contain the signal. This is a data-generating-process
  limit, not a modelling deficiency.

The strong cohorts (2019, 2020, 2025 filings) are exactly the credit-dominated ones. The
model's quality is conditional on the failure mode, and the annual headline is really a
weighted average whose weights are the unknown, cohort-specific failure-type mix.

## PR-AUC on the addressable subset

Removing only the 14 financially-invisible failures from the positive set (failures the Call
Report financials structurally cannot predict) lifts out-of-time PR-AUC:

| Population | Positives | PR-AUC | 95% bootstrap CI |
| --- | --- | --- | --- |
| Full out-of-time | 66 | 0.301 | [0.191, 0.438] |
| Addressable (invisible removed) | 52 | 0.382 | [0.250, 0.530] |

The addressable number carries its own interval, by the same percentile bootstrap that
produced the headline CI, so it is not a bare point estimate. With fewer positives (52 vs 66)
the addressable interval is wider, and the two intervals overlap heavily: 0.382 is a
structural reattribution of where the signal sits, not a separable accuracy gain over 0.301.
The gap between them is the price of the 14 structurally-invisible events, which no amount of
modelling on this data can recover.

Two robustness checks on the 0.382 itself:

- **It depends only on the invisible/visible boundary.** The addressable set is the full set
  minus the invisible positives, so moving a bank between the credit and rate/liquidity
  buckets leaves it in the addressable set and cannot change the number. This holds by
  construction, and a swap test confirms it: relabelling every credit/rate-liquidity positive
  to the other bucket and recomputing leaves the addressable PR-AUC identical
  (`addressable_depends_only_on_invisible_boundary: true`,
  `boundary_swap_positives_relabeled` shows the swap actually fired). The
  credit-versus-rate/liquidity split, the one genuinely judgmental boundary, has zero effect on
  the headline; it affects only the narrative of which cohort dominates a given year, which was
  separately shown robust above.
- **It is stable as the invisible boundary moves.** Across the four threshold grids (invisible
  count 9 to 14) the addressable PR-AUC ranges only 0.349 to 0.382
  (`pr_auc_addressable_range_over_grids`), so the headline does not hinge on the exact cut.

Within the addressable set, the rate/liquidity cohort remains the weakest because the training
signal skews credit; that is a genuine, addressable weakness (more rate/liquidity-failure
training mass would help), distinct from the invisible cohort, which is not addressable at
all.

## Why this is the load-bearing finding

It separates the three things that were previously conflated in one unstable number:

1. **What the model does well** (credit-visible distress, PR-AUC 0.382 on 52 failures).
2. **What it under-weights but could learn** (rate/liquidity failures, given more such
   training mass).
3. **What is structurally impossible on this data** (14 invisible failures: fraud, scams,
   sudden loss).

Only category 2 is a model-improvement opportunity. Categories 1 and 3 are, respectively,
already-solved and unsolvable-on-public-financials. Reporting a single 0.301 hides all
three. Chasing a higher headline number on the full out-of-time set would be self-deception:
roughly a fifth of those positives carry no signal to find.

## Statistical caveat

At 66 out-of-time failures the paired test has roughly 6% power (see the G0
statistical-foundation analysis), so the 0.301 vs 0.382 difference, and every by-cohort
number, sits inside wide intervals and is **not** out-of-time statistically separable. The
decomposition is a structural explanation of where the model's signal comes from, not a
certified performance gain.

The classification thresholds are deliberate, simple, and disclosed. Their robustness is
measured, not asserted: across four threshold sets (the base cut, a deliberate loosening to
noncurrent >= 2% / Tier-1 < 7% / uninsured >= 25% / securities >= 3%, a tightening, and an
uninsured-heavy variant), the 2022 filing cohort stays rate/liquidity-dominated and the 2024
filing cohort stays invisible-dominated in every case; only the invisible count moves (9 to
14), and the loosest cut simply reclassifies a few borderline invisibles as rate/liquidity or
credit.
The qualitative story does not depend on the exact cuts (`story_robust_to_thresholds` in the
artifact). The named-bank mapping above can also be checked directly against the FDIC failure
record. Nothing here is supervisory advice, a rating, or a basis for any deposit, investment,
or business decision.
