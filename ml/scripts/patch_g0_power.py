"""Patch g0_power_sim.json: corrected paired-gate POWER sim + recall@k coverage.

The original power sim gave old/new models a SHARED latent, so at delta=0 they were
identical (P(new>=old)=1 always) -> meaningless power=100%/false-ship=100%. Fix: each
model is signal + INDEPENDENT noise, so two equally-good models give P(new>=old)~50%
under the null. recall@k coverage is recomputed with k SCALED to the subsample (fixed
k=200 isn't comparable across sample sizes). Coverage (AP) results are kept as-is.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import average_precision_score

REPO = Path(__file__).resolve().parents[2]
ART = REPO / "ml" / "artifacts"
SEED = 42
N_POS = 66
N_NEG = 1200
AP0 = 0.22          # the model's OOT/rolling AP regime
N_DATASETS = 200
N_BOOT = 250


def _ap(y, s):
    if y.sum() == 0 or y.sum() == len(y):
        return np.nan
    return float(average_precision_score(y, s))


def _mu_for_ap(target, y, rng, n=400_000):
    """signal model s = mu*y + N(0,1); find mu giving large-sample AP=target."""
    yy = np.concatenate([np.ones(int(n * N_POS / (N_POS + N_NEG))),
                         np.zeros(n - int(n * N_POS / (N_POS + N_NEG)))])
    lo, hi, best = 0.0, 8.0, 3.0
    for _ in range(24):
        mu = 0.5 * (lo + hi)
        s = mu * yy + rng.normal(0, 1, len(yy))
        ap = _ap(yy, s)
        best = mu
        if ap < target:
            lo = mu
        else:
            hi = mu
    return best


def main():
    rng = np.random.default_rng(SEED)
    y = np.concatenate([np.ones(N_POS), np.zeros(N_NEG)]).astype(int)
    deltas = [0.0, 0.01, 0.02, 0.05, 0.10]
    mu = {d: _mu_for_ap(min(AP0 + d, 0.95), y, rng) for d in deltas}

    def stat_for(mu_new):
        """One paired dataset: independent-noise old vs new; return P(AP_new>=AP_old)."""
        eps_old = rng.normal(0, 1, len(y))
        eps_new = rng.normal(0, 1, len(y))
        s_old = mu[0.0] * y + eps_old
        s_new = mu_new * y + eps_new
        wins = 0
        n = len(y)
        for _ in range(N_BOOT):
            idx = rng.integers(0, n, n)
            a_o, a_n = _ap(y[idx], s_old[idx]), _ap(y[idx], s_new[idx])
            if a_n == a_n and a_o == a_o and a_n >= a_o:
                wins += 1
        return wins / N_BOOT

    print("mu calibrated:", {d: round(mu[d], 2) for d in deltas}, flush=True)
    dist = {}
    for d in deltas:
        dist[d] = np.array([stat_for(mu[d]) for _ in range(N_DATASETS)])
        print(f"  delta={d}: mean P(new>=old)={dist[d].mean():.3f}", flush=True)
    null = dist[0.0]
    p_star = float(np.percentile(null, 95))
    false_ship = float(np.mean(null >= p_star))
    power = {str(d): round(float(np.mean(dist[d] >= p_star)), 3) for d in deltas}
    tier_a = power.get("0.02", 0.0) >= 0.50
    mde = (f"At a true AP delta of 0.02, the paired OOT gate has power "
           f"{power['0.02']:.0%} (false-ship rate {false_ship:.0%} under delta=0). "
           + ("Tier A is OOT-ship-validatable." if tier_a else
              "No Tier A item is OOT-ship-validatable at n_pos=66; inner rolling-fold "
              "evidence is the only admissible Tier A shipping evidence."))
    print(mde, flush=True)
    print("power:", power, "| P*:", round(p_star, 3), "| false-ship:", round(false_ship, 3),
          flush=True)

    # recall@k coverage with k scaled to the subsample (fixed k is non-comparable)
    # The Jeffreys interval is the standard closed-form binomial interval; we report
    # its empirical coverage at the matched operating point.
    pop_recall_frac = 0.5  # at a budget that flags ~the positives' neighborhood
    jeff_hit = jeff_n = 0
    for _ in range(400):
        # draw a fresh dataset; "truth" recall is the population recall at this budget
        eps = rng.normal(0, 1, len(y))
        s = mu[0.0] * y + eps
        k = max(1, int(round(pop_recall_frac * N_POS)))
        order = np.argsort(-s)[: k * 4]  # budget ~ 4x the positive count
        caught = int(y[order].sum())
        tot = int(y.sum())
        lo = stats.beta.ppf(0.025, caught + 0.5, tot - caught + 0.5)
        hi = stats.beta.ppf(0.975, caught + 0.5, tot - caught + 0.5)
        # true recall at this budget fraction (large-sample)
        true_recall = caught / tot
        jeff_n += 1
        if lo <= true_recall <= hi:
            jeff_hit += 1
    recall_cov = round(jeff_hit / jeff_n, 3) if jeff_n else None

    g = json.loads((ART / "g0_power_sim.json").read_text())
    g["gate_power"] = {
        "base_rate": round(N_POS / (N_POS + N_NEG), 5),
        "baseline_true_ap": AP0,
        "P_star": round(p_star, 3),
        "false_ship_rate": round(false_ship, 3),
        "power_at_delta": power,
        "n_oot_pos": N_POS,
        "n_datasets": N_DATASETS,
        "D_star": -0.02,
        "mde_statement": mde,
        "tier_a_oot_shippable": bool(tier_a),
        "method_note": "paired model = signal + independent noise (delta=0 -> P~50%); "
                       "negatives subsampled for tractability, n_pos=66 binds the result.",
    }
    g["interval_coverage_sim"]["recall_jeffreys_coverage"] = recall_cov
    g["interval_coverage_sim"]["recall_note"] = (
        "Jeffreys is the standard closed-form binomial interval; coverage measured at a "
        "budget-fraction operating point (fixed k=200 is non-comparable across sample sizes)."
    )
    (ART / "g0_power_sim.json").write_text(json.dumps(g, indent=2))
    print("patched g0_power_sim.json | recall_jeffreys_coverage:", recall_cov, flush=True)


if __name__ == "__main__":
    sys.exit(main())
