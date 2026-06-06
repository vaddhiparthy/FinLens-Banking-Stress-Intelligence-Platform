# GRU sequence challenger: testing the trajectory architecture

The served model is a discrete-time hazard GBM that scores one bank-quarter at a time (with
a few engineered quarter-over-quarter deltas). A fair critique is that this under-uses
**within-bank temporal autocorrelation**: a bank's trajectory, the shape of its last several
quarters, may carry signal a point-in-time model cannot represent. The theoretically-matched
architecture for that is a recurrent network over the quarterly sequence. This builds it and
tests it on equal footing.

Artifact: `ml/artifacts/sequence_challenger.json`. Reproduce:
`python ml/scripts/sequence_challenger.py` (needs CPU torch).

## What was built

| Element | Choice |
| --- | --- |
| Architecture | GRU, hidden 48, over the last K = 8 quarters of all 34 features |
| Sequence build | per-CERT history ending at each labelable quarter, left-padded + masked |
| Readout | last unmasked time step, into a 32-unit ReLU head with dropout 0.2 |
| Standardization | z-scored on train statistics only (no leakage) |
| Imbalance | `pos_weight` in BCE = train negative/positive ratio |
| Early stopping | on an inner time-ordered validation tail (PR-AUC, patience 12) |
| Calibration | isotonic on the inner validation slice, the same recipe as the GBM |
| Split | the identical out-of-time holdout used everywhere else |

Training sequences: 229,803. Out-of-time sequences: 118,943 (66 failures).

## Result: the trajectory model does not beat the incumbent

| Model | OOT PR-AUC | OOT ROC-AUC |
| --- | --- | --- |
| Served GBM (bagged) | 0.301 | n/a |
| GRU sequence challenger | 0.207 | 0.769 |

The GRU's point estimate is **lower** (delta -0.094). It overfits in-sample: inner-validation
PR-AUC reaches 0.607 and then collapses to 0.207 out-of-time. That collapse is itself
informative. The trajectory signal the GRU finds in the training era does **not** transfer
across the regime and cohort shift into the out-of-time window, which is exactly what the
[failure-type decomposition](FAILURE_DECOMPOSITION.md) predicts: the out-of-time failures are
a different mix of failure modes (rate/liquidity in 2022, invisible in 2024), and a model
that memorizes in-sample trajectory shapes has nothing to grab onto when the failure type
changes.

## The result is not a single-config artifact

To rule out that one untuned configuration was simply a bad GRU, a sweep of six
configurations was run on the same split (`ml/scripts/sequence_sweep.py`,
`ml/artifacts/sequence_sweep.json`): hidden size 16 to 48, dropout 0.2 to 0.4, weight decay
1e-5 to 1e-3, history length K in {4, 8, 12}, and three seeds.

| Config | inner-val PR-AUC | OOT PR-AUC |
| --- | --- | --- |
| base h48 K8 s42 | 0.607 | 0.207 |
| smaller h24 K8 s42 | 0.611 | 0.209 |
| tiny h16 K8 s42 | 0.619 | 0.219 |
| short K4 h32 s42 | 0.605 | 0.189 |
| long K12 h32 s7 | 0.562 | 0.246 |
| base h48 K8 s123 | 0.667 | 0.238 |

Every configuration lands out-of-time between 0.189 and 0.246, all below the served GBM's
0.301; five of the six sit inside its bootstrap CI and the sixth sits just below it (even
worse). The inner-validation to out-of-time collapse (0.56 to 0.67 in-sample, 0.19 to 0.25
out-of-time) is present in every config. No reachable GRU beats the incumbent at this data
scale regardless of capacity, regularization, history length, or seed, and the non-transfer
reading is supported across the sweep rather than inferred from one run.

## Statistical separability

Two independent reasons this is reported as a challenger, not a result:

1. **CI containment.** The GRU's 0.207 falls **inside** the served model's bootstrap PR-AUC
   interval [0.191, 0.438]. The two models are not distinguishable on the out-of-time set.
2. **Power.** At 66 out-of-time failures the paired comparison has roughly 6% power (see the
   G0 statistical-foundation analysis). The data cannot certify a difference of this size in
   either direction.

So the result is: the architecturally-matched sequence model **did not deliver an
out-of-time gain**, its point estimate is worse, and at this sample size neither the loss nor
any hypothetical gain would be statistically separable. Claiming the GRU "captures
trajectory structure the GBM misses" would be the exact fake improvement to avoid: in-sample
it appears to, out-of-time it does not.

## Why the GBM remains served

Even setting the point estimates aside (they are not separable), the GBM is preferred on
grounds the small recurrent net cannot match at this data scale:

- a better out-of-time point estimate,
- monotone constraints (more capital can never raise predicted risk; the GRU has no such
  guarantee),
- calibrated probabilities with per-bank SHAP attributions a supervisor can read,
- a far smaller, auditable, serialization-safe artifact.

The challenger is kept in the repository as the documented test of the trajectory hypothesis,
not as a candidate for promotion. The obvious "more sophisticated architecture" was built,
measured on equal footing, and found not to help on the data that exists.
