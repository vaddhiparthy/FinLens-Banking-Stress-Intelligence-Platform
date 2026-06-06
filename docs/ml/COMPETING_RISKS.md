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

## Positioning against the competing-risks methods literature (S3)

This treatment is deliberately aligned with the established competing-risks methodology, so a
methods reviewer can place it. The relevant lineage:

- **Cause-specific vs subdistribution hazards.** The standard distinction (cause-specific
  hazard for etiology vs the subdistribution hazard for absolute risk) is from Fine & Gray,
  "A proportional hazards model for the subdistribution of a competing risk," JASA 94 (1999)
  496-509, with the applied framing in Austin, Lee & Fine, "Introduction to the analysis of
  survival data in the presence of competing risks," Circulation 133 (2016) 601-609. We report
  both views: cause-specific failure and merger hazards, and the Aalen-Johansen cumulative
  incidence (the absolute-risk quantity the subdistribution targets).
- **Discrete time is the correct regime here.** Call Reports are quarterly, so the event time
  is genuinely discrete and the continuous-time Fine-Gray model does not directly apply. This
  is exactly the gap the discrete-time competing-risks literature addresses: Berger et al.,
  "Subdistribution hazard models for competing risks in discrete time," Biostatistics 21(3)
  (2020) 449-466, and the overview in Schmid & Berger, "Competing risks analysis for discrete
  time-to-event data," WIREs Computational Statistics 13(5) (2021) e1529. Our Fine-Gray
  cross-check is implemented as a **discrete-time** subdistribution model (ml/scripts/
  fine_gray.py), consistent with that literature, not a misapplied continuous-time fit.
- **What we add.** The methods literature establishes how to model competing risks; it does
  not quantify, for a bank-failure panel, how much the common right-censoring-of-mergers
  practice biases measured failure performance. We give that decision-relevant number (2.2% of
  merger exits were elevated-distress at exit) and show a discrete-time Fine-Gray subdistribution
  model lands within noise of the cause-specific model (0.182 vs 0.176), so for this panel the
  censoring approach is adequate and the competing-risks correction is immaterial to the served
  ranking. The contribution is the empirical bias bound for this application, positioned within
  the discrete-time subdistribution framework, not a new estimator.
