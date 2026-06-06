# Publication readiness: durable checklist + adversarial validation

Tracks the full set of changes required to turn FinLens from a (saturated) bank-failure
*prediction* project into a defensible *measurement* paper, per the literature review and the
follow-up coding plan. Every item has a definition-of-done and a named adversarial validator
with an explicit kill condition; an item is not "done" until its validator returns a unanimous
pass with zero blocking issues. This file is the source of truth; the in-session task list
mirrors it.

## The thesis (what the paper claims)

Pooled evaluation of rare-event bank-failure models conflates failures that are financially
observable with failures (notably fraud) that are structurally invisible to accounting data.
Using the 2019-2026 out-of-time cohort, we show the pooled PR-AUC is a biased performance
summary, decompose the positive set with externally-sourced failure-cause labels, quantify the
irreducible ceiling the invisible cohort imposes, and show the pooled-vs-addressable gap is a
property of the evaluation that holds across model families. Positioned as the measurement
nuance to Correia/Luck/Verner "Failing Banks" (2025), whose "fundamentals predict failure"
result is established for the financially-visible cohort but is silent on the invisible one.

## Competitive landscape (verification status)

- [x] Correia, Luck & Verner, "Failing Banks" (2025) — VERIFIED real: NY Fed Staff Report
  1117 / Richmond WP 25-04 / NBER w32907 / arXiv 2506.06082. 1863-2024 panel; failures highly
  predictable from public accounting metrics; ROC-AUC 80-85% (NOT PR-AUC); fundamentals over
  runs. Does not decompose by failure type or report addressable-vs-pooled. The elephant.
- [ ] Claremont thesis (2024) "Explaining and Predicting U.S. Bank Failures 2001-2024" — TO
  VERIFY (claimed near-twin: Call Report panel, FDIC labels, 4q horizon, dropped RWA ratios for
  the post-2020 break).
- [ ] RF/XGBoost peer-reviewed papers (claimed 98.4% RF, 2001-2023Q3; counterfactual-explanations
  paper; insolvency comparison) — TO VERIFY.
- [ ] Cole & Gunther (1998) and the CAMELS-downgrade econometric lineage — TO VERIFY/cite.

## Master checklist

| # | Item | Definition of done | Adversarial validator (kill condition) | Status |
|---|------|--------------------|----------------------------------------|--------|
| C3 | Cross-model pooled-vs-addressable | pooled & addressable PR-AUC + CIs for >=3 model families; lift positive in all; first-class output | ML/stats reviewer: FAIL if lift not cross-model, leakage, or CI wrong | DONE (committed 7735090) |
| C4 | CBLR/CECL feature break | regime indicator (or imputation) for the 2020Q1 tier1_rwa discontinuity; documented in feature dict; retrain + re-cert | ML/stats: FAIL if null-semantics flip unhandled or leakage; domain: FAIL if CBLR mechanics misstated | TODO (needs retrain go) |
| C1 | External failure-cause labels | failure_cause_labels.py: per-CERT cause from COMPOSITE source (OIG MLR + OIG short reviews + DOJ/SEC + FDIC PR) with source doc + date per bank | domain: FAIL if a cause contradicts the cited source; ML: FAIL if coverage gaps undisclosed | TODO (needs web-fetch go) |
| C2 | Decomposition off external labels | failure_decomposition joins external labels; addressable PR-AUC recomputed on externally-defined invisible set | ML/stats: FAIL if numbers don't reconcile or label join is wrong | BLOCKED by C1 |
| C5 | Label-source sensitivity | addressable PR-AUC stable across {MLR, OCC, DOJ, threshold} label sources | ML/stats: FAIL if result swings materially with source and that isn't disclosed | BLOCKED by C1 |
| S1 | Full literature positioning | related-work section citing+differentiating Correia, Claremont, RF/XGBoost, Cole-Gunther, CAMELS-downgrade | peer-reviewer: FAIL if any load-bearing comparable is missing or mischaracterized | TODO |
| S2 | Reframe model->measurement | every "my model achieves X" reframed; evaluation problem leads; 0.301->0.382 framed as artifact evidence | UI/honesty + peer-reviewer: FAIL on any performance-brag framing | PARTIAL (docs already hedged) |
| S3 | Competing-risks as second pillar | merger-censoring + Fine-Gray positioned vs the discrete-time competing-risks methods literature | methodologist: FAIL if presented as a one-off check, not positioned vs literature | TODO |
| S4 | arXiv/SSRN preprint | compileable manuscript with C1-C5 + S1-S3 folded in; reproducible artifacts referenced | full 3-persona gate: FAIL if any item above is open | TODO |
| V0 | Verify all citations | every cited work independently confirmed to exist and say what we claim | self + peer-reviewer: FAIL on any unverified load-bearing citation | PARTIAL (Correia done) |

## Build order (dependency-correct)

1. **C4** (CBLR retrain) and **C1** (external labels) are the two independent long poles. C4
   needs a go (it overwrites the certified 0.301). C1 needs a web-fetch go.
2. **C2**, **C5** depend on C1. **S2/S3** can proceed in parallel (writing).
3. **S1/V0** (lit) proceed in parallel; finish before **S4** (preprint).
4. Re-run **C3** after C1/C4 so the cross-model claim uses external labels and the CBLR-fixed
   model.

## Adversarial validation protocol (per item)

Each item, when built, is reviewed by a panel of independent subagents before it is marked
done. Panel adapted to a publication bar:

- **Methodologist / peer reviewer** — would a competent referee accept the method? Leakage,
  power, CI correctness, baseline fairness, overclaiming.
- **Banking-domain examiner** — are the failure-cause labels, CBLR mechanics, and PCA terms
  correct and consistent with the cited sources and the FDIC record?
- **Reproducibility / honesty reviewer** — do numbers reconcile across code, artifact, doc, and
  manuscript; no honesty-boast or unverifiable claims; auto-synced not hardcoded.

Pass requires UNANIMOUS, zero blocking issues. Blockers are fixed and the panel re-run until
clean, exactly as the model-layer gate was run. No item is "done" on vibes; each is backed by a
committed artifact and a passing gate.

## What is explicitly NOT in scope (not limitations, just boundaries)

Non-public data (confidential CAMELS exam ratings, deposit-flow, intraday liquidity) is outside
the project by definition; we build on the public FDIC/FFIEC data we are allowed to use. This is
the scope, not a shortfall, and is not logged as a gap.
