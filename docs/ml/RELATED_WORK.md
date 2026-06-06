# Related work and positioning (S1)

All citations below were independently verified to exist and to say what is attributed to them
(V0). The frame: prior work establishes that bank failure is predictable; we do not compete on
predictability. We problematize how that predictability is *evaluated*, and show pooled
rare-event metrics conflate financially-observable failures with structurally-invisible
(fraud) failures.

## The established result we position against

**Correia, Luck & Verner, "Failing Banks" (2025).** NY Fed Staff Report 1117 / Richmond Fed
WP 25-04 / NBER w32907 / arXiv 2506.06082 (and the Liberty Street Economics note, Nov 2024,
"Why Do Banks Fail?"). A panel of nearly all US commercial banks 1863-2024; failures are
highly predictable from simple public accounting metrics (solvency, noncore-funding
vulnerability), with next-year ROC-AUC ~80-85%, and fundamentals dominate runs. It reasons
about solvency-vs-liquidity *mechanisms* but scores prediction against a single pooled failure
label and does not decompose performance by failure cause. This is the authoritative
predictability result; we provide the measurement nuance its pooled framing leaves open.

## The near-twin (same pipeline, prediction framing)

**Shakiba, "Explaining and Predicting U.S. Bank Failures, 2001-2024" (CMC Senior Thesis,
2026).** A bank-quarter panel of 632,764 observations across 10,740 institutions from FFIEC
Call Reports via WRDS, FDIC Failed Bank List labels, four-quarter horizon; logit / ridge /
lasso / RF / XGBoost trained on 2001-2010 and tested out-of-sample, ROC-AUC > 0.97 with
screening lift > 200x the base rate. Notably it **drops two risk-weighted capital ratios for
the post-2020 Community Bank Leverage Ratio reporting change** (the same break we address in C4).
Our differentiation is twofold: (1) we do not add another prediction model; we change the
evaluation; and (2) our C4 robustness shows that *dropping* the disrupted risk-weighted ratio
(the thesis's choice) is harmful (a large addressable-PR-AUC loss), whereas retaining it with
native-null handling plus an election indicator is neutral and strictly better. So we both
reframe the problem and refine a concrete modelling decision in the adjacent work.

## ML-for-bank-failure papers (prediction, pooled metrics)

- **Hu, Shao & Zhang, "Predicting U.S. bank failures and stress testing with machine learning
  algorithms," Finance Research Letters 75 (2025).** FDIC data 2001Q1-2023Q3, EWMA-encoded
  dynamics, logit/XGBoost/RF/SVM/NN; Random Forest reaches 98.4% accuracy. The headline
  illustrates our motivating problem: *accuracy* on a <1% base-rate panel is an uninformative
  metric, which is why we report PR-AUC and, further, addressable PR-AUC.
- **Vallarino, "A Comparative Machine Learning Survival Models Analysis for Predicting Time to
  Bank Failure in the US (2001-2023)," Journal of Economic Analysis 3(1) (2024).** 564
  failures, survival models; time-to-failure, still a pooled label.
- **Citterio et al., "Bank failure prediction models: Review and outlook," Socio-Economic
  Planning Sciences 92 (2024).** The field survey; organizes the literature by default
  definition, technique, and variable selection. There is no category for cause-conditional or
  addressable-vs-pooled evaluation, which corroborates the gap we fill.

## Classic econometric lineage

- **Cole & Gunther, "Predicting Bank Failures: A Comparison of On- and Off-Site Monitoring
  Systems," Journal of Financial Services Research 13(2) (1998).** Off-site Call-Report probit
  vs CAMEL ratings; a CAMEL rating's information decays after ~two quarters, so a model on
  current public data outpredicts stale exam ratings. The foundational case for public-data
  early warning.
- **Cole & Gunther, "Separating the likelihood and timing of bank failure," Journal of Banking
  & Finance 19(6) (1995).** The survival/timing reference (cite this one, not the 1998 paper,
  for time-to-failure).

## The gap we fill

Across the established result (Correia et al.), the near-twin (Shakiba), the ML papers
(Hu et al.; Vallarino), the field survey (Citterio et al.), and the classic lineage (Cole &
Gunther), **we are not aware of prior work that evaluates bank-failure prediction conditioned
on failure cause, or that reports an addressable-vs-pooled metric.** Every cited work competes
on an aggregate score against a single failure label. Our contribution:

1. Externally-sourced failure-cause labels (FDIC OIG / OCC / Fed / Treasury OIG) for the
   out-of-time failures, not author-defined thresholds (C1).
2. A pooled-vs-addressable evaluation that, on five model families including the published RF
   and XGBoost, shows a consistent positive lift when the structurally-invisible (fraud)
   failures are removed (C3), i.e. the gap is a property of the evaluation, not any model.
3. The consequence: pooled rare-event metrics understate performance by a roughly
   constant amount and hide an irreducible ceiling set by failures with no financial signal.

We frame this as the measurement complement to Correia et al.: fundamentals predict the
financially-visible failures; the fraud cohort is invisible to fundamentals, and pooled
metrics conceal that. Per standard practice and the limits of an exhaustive-but-not-infinite
search, we state this as "we are not aware of" rather than "no one has done this."
