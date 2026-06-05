# Competing Risks: Failure vs Merger

The model treats merger/acquisition exits as right-censored (a bank that leaves the
panel without a failure record has its pre-exit quarters dropped, never labeled 0). The
known concern is **informative censoring**: a distressed bank that is *acquired* instead
of failing has its would-be-positive quarters removed, biasing measured failure recall
downward. This analysis quantifies that bias instead of assuming it.
(`ml/scripts/competing_risks.py`, `ml/artifacts/competing_risks.json`; no new
dependencies, $0.)

## Mergers dominate exits, so competing risks is real
Cause-specific discrete-time hazards (failure and merger) with an Aalen-Johansen
cumulative-incidence estimate over the 2008-2026 panel:

| event | events | cumulative incidence |
|---|---|---|
| merger / acquisition | 14,132 | 0.739 |
| failure | 2,138 | 0.185 |

Mergers are ~**4x** more common than failures. Treating them as plain censoring (rather
than a competing event) is therefore a real modeling choice, not a rounding detail.

## But the informative-censoring bias is small (quantified)
A cause-specific LightGBM merger hazard is fit on the same features. The decision-
relevant question is not "how many mergers" but "how many mergers were of *distressed*
banks" - those are the would-be failures removed by censoring. Scoring each
merger-exit bank's **last filing** with the failure model:

- **81 of 3,718 merger-exit banks (2.2%)** were at or above the review threshold at
  exit (elevated distress).
- So at most ~2.2% of merger exits were distressed acquisitions. The informative-
  censoring bias on measured failure recall is bounded by roughly this fraction - i.e.
  true recall is at most a few points higher than measured, not a large correction.

## Conclusion
The current right-censoring is **adequate and the bias it introduces is small and now
measured**, not hand-waved. A full Fine-Gray subdistribution model is the textbook next
refinement, but with only 2.2% of mergers distressed it would move the failure estimate
marginally; the cause-specific hazards + the quantified bias above are the
decision-relevant deliverable. This replaces the prior "handled by censoring, not a
formal model" gap with a number.
