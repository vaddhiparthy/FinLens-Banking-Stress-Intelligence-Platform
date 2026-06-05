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

## Fine-Gray subdistribution model (built, not just proposed)
A discrete-time Fine-Gray subdistribution model was built from scratch
(`ml/scripts/fine_gray.py`, `ml/artifacts/fine_gray.json`; lifelines/scikit-survival
ship no Fine-Gray estimator, and this is a discrete-time panel, so the from-scratch
subdistribution is the correct tool). It keeps **10,702** merger-window bank-quarters in
the failure risk set as guaranteed non-events (the subdistribution treatment) that the
cause-specific model drops. Same OOT protocol, default params on both:

| model | OOT PR-AUC | 95% CI |
|---|---|---|
| Cause-specific (shipped censoring) | 0.176 | [0.100, 0.281] |
| Fine-Gray subdistribution | 0.182 | [0.102, 0.294] |

The two are within noise of each other (heavily overlapping CIs), which confirms
empirically what the 2.2% distressed-merger rate implied: the competing-risks correction
is immaterial to the served ranking.

## Conclusion
The current right-censoring is **adequate, and the bias it introduces is small, now
measured, and now cross-checked against a built Fine-Gray model** rather than hand-waved.
This replaces the prior "handled by censoring, not a formal model" gap with two numbers
(2.2% distressed-merger rate; Fine-Gray 0.182 vs cause-specific 0.176, within noise).
