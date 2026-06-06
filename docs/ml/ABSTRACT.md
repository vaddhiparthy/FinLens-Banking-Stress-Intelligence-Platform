# Abstract and framing (S2): a measurement paper, not a model paper

This is the canonical framing for the work. The contribution is about *how rare-event
bank-failure prediction is evaluated*, not about a better predictor. Every sentence that reads
like "our model achieves X" is deliberately subordinated to the measurement claim.

## Abstract (draft)

Bank failure is highly predictable from public accounting data, a result established at scale
by Correia, Luck and Verner (2025) and reproduced across the machine-learning literature. We do
not contest that result. We show instead that the standard way of *evaluating* such predictors
is biased in a specific, correctable way. Pooled rare-event metrics (PR-AUC, recall@k, and
especially accuracy) are computed over a positive set that mixes failures that are financially
observable in the accounting data with failures (notably fraud) that leave no financial
signature and are therefore structurally unrankable by any accounting-based model. Using the
2019-2026 out-of-time U.S. bank failures (66 events) and failure causes sourced from primary
regulator documents (FDIC OIG, OCC, Federal Reserve, Treasury OIG), we decompose the positive
set by failure visibility and report performance on the financially-addressable subset
alongside the pooled figure. The pooled-to-addressable lift is positive and of similar
magnitude across five model families (penalized logistic regression, random forest, XGBoost,
and constrained/unconstrained gradient boosting), demonstrating that the gap is a property of
the evaluation, not of any model. We quantify the irreducible ceiling the invisible cohort
imposes, show the result is stable to the label source (author thresholds vs regulator-stated
cause agree on 92% of positives) and to a 2020-reporting-regime feature break, and argue that
rare-event bank-failure benchmarks should report addressable-subset performance. We are not
aware of prior work that conditions failure-prediction evaluation on failure cause or reports
an addressable-versus-pooled metric.

## What we explicitly do not claim

- Not a new or better predictor. The served model is a calibrated monotone gradient-boosted
  hazard model; it is the vehicle, not the contribution.
- Not statistical separability of any single number. At 66 out-of-time failures the paired
  power is ~6%; every figure is reported with bootstrap intervals and described as not
  individually separable. The claim is the consistent *direction* across models and label
  sources, and the structural reattribution of where the signal sits, not a certified gain.

## The one-line positioning

Correia et al. show fundamentals predict failure; we show that holds for the financially
visible failures, that the fraud cohort is invisible to fundamentals by construction, and that
pooled metrics hide this, so the field's standard evaluation understates and mismeasures
rare-event failure prediction. The fix is to report addressable-subset performance with
externally-grounded failure-cause labels.

## Tier expectation

The 66-failure wall is real and bounds the achievable venue: a strong applied-ML or
financial-stability journal plus a citable preprint, not a top-three finance journal. The
measurement framing converts the small sample from a weakness into the subject, but does not
remove it.
