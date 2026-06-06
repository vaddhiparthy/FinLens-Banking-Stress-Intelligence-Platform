# Ceiling backlog: every residual, its fix, and what is a true wall

This is the honest, exhaustive ledger behind the "highest practically attainable" claim. It
separates three things that must not be conflated: (A) fixable items, now fixed; (B)
weaknesses and edge cases that were investigated; (C) limitations that are genuine walls
(the in-scope data does not exist or is fixed by arithmetic), not risk-avoidance.

Scope is the public FDIC/FFIEC data we are allowed to use; non-public data is simply outside
the project, not a shortfall to log. Nothing here is "too risky to touch" either. Section C
items are impossible within the in-scope data, not dangerous.

## A. Fixable items (all addressed)

- [x] **Addressable PR-AUC reported bare.** Problem: 0.382 had no interval. Fix: 95%
  percentile-bootstrap CI by the same method as the headline, **0.382 [0.250, 0.530]** vs full
  **0.301 [0.191, 0.438]**, overlap flagged. (`failure_decomposition.py`, artifact
  `pr_auc_addressable_ci`.)
- [x] **CI method mislabeled "stratified".** Problem: `bootstrap_metrics` is iid percentile,
  not stratified; the docstring and several docs said "stratified". Fix: relabeled to
  "percentile" at the root docstring (`evaluate.py`) and every reference (decomposition, wiki,
  page, report, model card, validation report). "Stratified" now appears only where it is
  correct (the calibration in-train holdout split).
- [x] **Boundary-invariance proof was a tautology.** Problem: the swap test recomputed the
  identical classifier (no swap). Fix: a genuine credit<->rate/liquidity relabel of all 52
  visible positives; the addressable PR-AUC is unchanged (0.382). Artifact records
  `boundary_swap_positives_relabeled: 52`.
- [x] **Addressable chart had no error bars.** Problem: the bars read as point estimates while
  the prose said otherwise. Fix: 95% CI whiskers added to `addressable_pr_fig`.
- [x] **Sweep duplicated the sequence builder.** Problem: `sequence_sweep.py` re-implemented
  `_build_sequences`, a drift risk. Fix: `_build_sequences` now takes `k` and the sweep imports
  it, so there is one builder.
- [x] **Honesty-boast copy in the UI.** Problem: pre-existing headings "How we know the
  intervals are honest", "Measuring calibration honestly", "Honest data caveat", "Honest known
  gaps", and "the honest story" violated the no-self-praise rule. Fix: all reworded to factual
  headings (coverage-validated, at the base rate, data caveat, known gaps, expected behaviour).
- [x] **Em dash in UI copy.** Fix: the one em dash in the G0 caption replaced with a colon.
- [x] **Stratified-CI cross-check.** Added a stratified percentile bootstrap (positive count
  held fixed) for both headlines as a robustness cross-check; stored in the artifact.

## B. Weaknesses and edge cases (investigated)

- [x] **Threshold subjectivity of the taxonomy.** Swept 4 grids; the 2022-cohort stays
  rate/liquidity-dominated and 2024 stays invisible-dominated every time; invisible count
  9-14; addressable PR-AUC 0.349-0.382. (`threshold_sensitivity`.)
- [x] **The judgmental credit-vs-rate/liquidity boundary moving the headline.** Proven it
  cannot: the addressable set drops only invisible positives, so that boundary has zero effect
  on 0.382 (swap test above).
- [x] **GRU result being a single-config artifact.** 6-config sweep (size, dropout, weight
  decay, K, seed): all 0.189-0.246, every config below the GBM, in-sample to out-of-time
  collapse universal. (`sequence_sweep.json`.)
- [x] **Filing-year vs failure-year mislabel.** Corrected throughout; the two 2026 failures
  that close just past the panel end are extrapolated, not dropped.
- [x] **NaN handling in classification.** The securities legs are NaN-symmetric and the credit
  legs are NaN-guarded, so a missing field can never manufacture a credit or rate/liquidity
  label; it falls to invisible (conservative). In this holdout uninsured/securities are 0%
  null, so the invisible class is genuinely low-signal, not a data artifact.
- [ ] **Taxonomy not validated against an external failure-cause label set.** There is no
  public per-bank labeled failure-cause dataset; the modes are an author-defined diagnostic,
  disclosed as such, and cross-checked against the named FDIC failures (fraud failures land in
  invisible, the 2023 wave in rate/liquidity). A text-mining validation against FDIC Material
  Loss Reviews is possible but is a separate research effort with no certifiable payoff at 66
  failures; left open and labeled, not claimed as done.
- [ ] **Decomposition refits the bagged model per run (~5 min).** Efficiency only, not
  correctness; caching the OOT predictions would speed reruns. Low priority, recorded.

## C. True walls (impossible under the constraints, not risk-avoidance)

- **66 out-of-time failures cap statistical power at ~6%.** You cannot create failures that did
  not happen. No tuning, ensembling, or architecture delta is out-of-time certifiable at this
  n; this is arithmetic, not a choice. Mitigation already applied: everything is reported with
  intervals and explicitly as not separable.
- **Pre-2001 Call Reports do not exist in machine-readable form.** FFIEC CDR coverage begins
  2001Q1; the S&L-era failures (~2,367) are unreachable. Extending earlier is not risky, it is
  not possible. Tested the reachable extension to 2001: it hurt (OOT 0.219 to 0.139) and was
  reverted.
- **Originally-filed point-in-time data is inherently noisier than restated.** Built and
  fair-tested (B1): it loses as a training source (0.131 vs 0.176) because un-restated filings
  carry more error. It is used where it is the only correct option (live forward scoring).
- **BCa intervals are not tractable at 118k rows.** The acceleration term is an O(n) jackknife
  (118k AP recomputations); percentile is the feasible method, its coverage is characterized
  (~92.6%), and the under-coverage is conservative for the overlap conclusion.

## How to read this ledger

Section A is done. Section B is investigated, with two items deliberately left open and
labeled (external taxonomy validation, rerun caching), neither material to any reported number.
Section C is the physical ceiling: each item is impossible under $0 + public data + the failures
that actually occurred, and each is mitigated or measured rather than hidden. The distance from
here to "perfect" is entirely Section C, and Section C does not move.
