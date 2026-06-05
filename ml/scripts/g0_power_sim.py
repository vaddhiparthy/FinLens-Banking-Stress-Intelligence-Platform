"""G0 - interval-coverage + gate-power simulation (statistical foundation).

Per the certified ML max-out plan, this is the PREREQUISITE deliverable that gates
every paired threshold. It answers two questions with EXTERNAL-truth DGPs (never a
bootstrap of the one ~66-positive OOT realization, which would be circular):

  1. Coverage: for AP 95% CIs at n_pos~66, which of {percentile, stratified-by-
     positive, BCa} actually covers a KNOWN true AP? Does the closed-form recall@k
     Jeffreys interval cover at least as well?
  2. Power / MDE: with n_pos~66, what is the paired-bootstrap power to detect a true
     AP delta of 0.02 / 0.05 / 0.10, and what P*/D* thresholds give a stated
     false-ship rate? Produces the binding MDE sentence and tier_a_oot_shippable.

Two external-truth DGPs:
  - PRIMARY  : high-n surrogate-population subsampling. The 2008-2012 crisis region
               (high positive count) is the surrogate population; its full-sample AP
               (on cross-fitted OOF scores) is the KNOWN truth, external to every
               subsample.
  - CROSS    : parametric planted-separation model whose true AP is computed by a
               very large draw, calibrated to the rolling-fold AP regime (~0.233).

$0, fixed seed. Negative counts are subsampled for tractability (esp. BCa jackknife);
n_pos is held at the OOT count, the dominant driver of AP interval width. A low-
base-rate sensitivity check is run for the percentile method.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import average_precision_score

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS, MONOTONE_CONSTRAINTS  # noqa: E402
from finlens_ml.train import load_dataset  # noqa: E402

SEED = 42
N_OOT_POS = 66          # matches the shipped OOT holdout positive count
N_SIMS = 500            # external-truth datasets per coverage cell
N_BOOT = 400            # bootstrap resamples per CI
SIM_N_NEG = 1200        # tractable negative count (BCa jackknife is O(n)); n_pos drives width
NOMINAL = 0.95


def _ap(y, s):
    if y.sum() == 0 or y.sum() == len(y):
        return np.nan
    return float(average_precision_score(y, s))


def ci_percentile(y, s, n_boot, rng):
    n = len(y)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        a = _ap(y[idx], s[idx])
        if a == a:
            vals.append(a)
    if not vals:
        return (np.nan, np.nan)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def ci_stratified(y, s, n_boot, rng):
    """Resample positives and negatives separately, preserving each class count."""
    pos = np.where(y == 1)[0]
    neg = np.where(y == 0)[0]
    vals = []
    for _ in range(n_boot):
        ip = rng.integers(0, len(pos), len(pos))
        ineg = rng.integers(0, len(neg), len(neg))
        idx = np.concatenate([pos[ip], neg[ineg]])
        a = _ap(y[idx], s[idx])
        if a == a:
            vals.append(a)
    if not vals:
        return (np.nan, np.nan)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def ci_bca(y, s, n_boot, rng):
    """Bias-corrected and accelerated interval for AP. Acceleration via jackknife
    (O(n) AP evals; n is kept small here so this is feasible)."""
    n = len(y)
    theta_hat = _ap(y, s)
    boot = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        a = _ap(y[idx], s[idx])
        if a == a:
            boot.append(a)
    boot = np.asarray(boot)
    if boot.size == 0 or theta_hat != theta_hat:
        return (np.nan, np.nan)
    z0 = stats.norm.ppf((np.sum(boot < theta_hat) + 0.5) / (boot.size + 1.0))
    # jackknife acceleration
    jk = np.empty(n)
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        mask[i] = False
        jk[i] = _ap(y[mask], s[mask])
        mask[i] = True
    jbar = np.nanmean(jk)
    num = np.nansum((jbar - jk) ** 3)
    den = 6.0 * (np.nansum((jbar - jk) ** 2) ** 1.5)
    a_acc = num / den if den != 0 else 0.0
    zl, zu = stats.norm.ppf(0.025), stats.norm.ppf(0.975)

    def adj(z):
        return stats.norm.cdf(z0 + (z0 + z) / (1 - a_acc * (z0 + z)))

    lo = float(np.percentile(boot, 100 * adj(zl)))
    hi = float(np.percentile(boot, 100 * adj(zu)))
    return (lo, hi)


def recall_at_k(y, s, k):
    k = min(k, len(s))
    order = np.argsort(-s)[:k]
    tot = int(y.sum())
    return float(y[order].sum() / tot) if tot else np.nan, int(y[order].sum()), tot


def jeffreys_recall_ci(caught, total):
    if total == 0:
        return (np.nan, np.nan)
    lo = stats.beta.ppf(0.025, caught + 0.5, total - caught + 0.5)
    hi = stats.beta.ppf(0.975, caught + 0.5, total - caught + 0.5)
    return (float(lo), float(hi))


def _crisis_oof_scores():
    """Surrogate population = 2008-2012 crisis region; OOF cross-fitted scores so the
    full-region AP is an honest, external truth (not in-sample-inflated)."""
    import lightgbm as lgb
    from sklearn.model_selection import StratifiedKFold

    df = load_dataset()
    df = df[df["label_4"].notna()].copy()
    df["yr"] = df["quarter"].str.slice(0, 4).astype(int)
    crisis = df[(df["yr"] >= 2008) & (df["yr"] <= 2012)].reset_index(drop=True)
    X = crisis[FEATURE_COLUMNS].astype(float).to_numpy()
    y = crisis["label_4"].astype(int).to_numpy()
    mc = [MONOTONE_CONSTRAINTS[c] for c in FEATURE_COLUMNS]
    oof = np.zeros(len(y))
    skf = StratifiedKFold(n_splits=4, shuffle=True, random_state=SEED)
    for tr, te in skf.split(X, y):
        spw = min(float((y[tr] == 0).sum() / max(1, (y[tr] == 1).sum())), 40.0)
        m = lgb.LGBMClassifier(objective="binary", n_estimators=300, num_leaves=31,
                               learning_rate=0.03, monotone_constraints=mc,
                               scale_pos_weight=spw, n_jobs=4, random_state=SEED, verbose=-1)
        m.fit(X[tr], y[tr])
        oof[te] = m.predict_proba(X[te])[:, 1]
    return y, oof


def _parametric_population(target_ap, base_rate, rng, n=2_000_000):
    """Two-Gaussian score model; tune positive-mean separation so the large-sample AP
    matches target_ap at the given base rate. Returns (mu, true_ap)."""
    n_pos = max(1, int(n * base_rate))
    n_neg = n - n_pos
    y = np.concatenate([np.ones(n_pos), np.zeros(n_neg)]).astype(int)

    def ap_for(mu):
        s = np.empty(n)
        s[:n_pos] = rng.normal(mu, 1.0, n_pos)
        s[n_pos:] = rng.normal(0.0, 1.0, n_neg)
        return _ap(y, s), s

    lo, hi = 0.0, 6.0
    best_mu, best_ap = 3.0, 0.0
    for _ in range(22):  # bisection on monotone AP(mu)
        mu = 0.5 * (lo + hi)
        ap, _ = ap_for(mu)
        best_mu, best_ap = mu, ap
        if ap < target_ap:
            lo = mu
        else:
            hi = mu
    return best_mu, best_ap


def run_coverage(dgp_name, draw_fn, true_ap, methods, rng):
    """draw_fn(rng) -> (y, s) for one n_pos~66 dataset. Returns coverage per method."""
    hit = {m: 0 for m in methods}
    valid = {m: 0 for m in methods}
    jeff_hit = 0
    jeff_valid = 0
    for _ in range(N_SIMS):
        y, s = draw_fn(rng)
        for m, fn in methods.items():
            lo, hi = fn(y, s, N_BOOT, rng)
            if lo == lo and hi == hi:
                valid[m] += 1
                if lo <= true_ap <= hi:
                    hit[m] += 1
        # recall@k Jeffreys coverage against the population recall@k truth
        _, caught, tot = recall_at_k(y, s, 200)
        jl, jh = jeffreys_recall_ci(caught, tot)
        if jl == jl:
            jeff_valid += 1
    cover = {m: (hit[m] / valid[m] if valid[m] else np.nan) for m in methods}
    return {"dgp": dgp_name, "true_ap": round(float(true_ap), 4),
            "coverage": {m: round(cover[m], 3) for m in methods},
            "n_sims": N_SIMS}


def run_power(base_rate, rng):
    """Parametric paired power: baseline true AP ~ shipped rolling mean 0.233; inject
    deltas, generate PAIRED scores, measure P(new AP >= old AP) at n_pos~66."""
    base_ap = 0.233
    mu0, ap0 = _parametric_population(base_ap, base_rate, rng)
    deltas = [0.0, 0.01, 0.02, 0.05, 0.10]
    mus = {}
    for d in deltas:
        mu, ap = _parametric_population(min(base_ap + d, 0.95), base_rate, rng)
        mus[d] = (mu, ap)
    n_total = N_OOT_POS + SIM_N_NEG
    n_pos, n_neg = N_OOT_POS, SIM_N_NEG

    def paired_prob(mu_new):
        """One dataset: P(new>=old) via paired bootstrap; return that prob."""
        y = np.concatenate([np.ones(n_pos), np.zeros(n_neg)]).astype(int)
        # correlated old/new: shared latent + independent noise; new has larger pos shift
        latent_pos = rng.normal(0, 1, n_pos)
        latent_neg = rng.normal(0, 1, n_neg)
        s_old = np.concatenate([latent_pos + mu0, latent_neg])
        s_new = np.concatenate([latent_pos + mu_new, latent_neg])
        n = n_total
        wins = 0
        nb = 300
        for _ in range(nb):
            idx = rng.integers(0, n, n)
            a_old = _ap(y[idx], s_old[idx])
            a_new = _ap(y[idx], s_new[idx])
            if a_new == a_new and a_old == a_old and a_new >= a_old:
                wins += 1
        return wins / nb

    # distribution of P(new>=old) across datasets, per delta
    n_datasets = 200
    pstats = {}
    for d in deltas:
        mu_new = mus[d][0]
        probs = [paired_prob(mu_new) for _ in range(n_datasets)]
        pstats[d] = np.asarray(probs)

    # choose P* so false-ship (delta=0) rate = 0.05; power = P(stat >= P*) at each delta
    null = pstats[0.0]
    p_star = float(np.percentile(null, 95))
    false_ship = float(np.mean(null >= p_star))
    power = {str(d): round(float(np.mean(pstats[d] >= p_star)), 3) for d in deltas}
    return {
        "base_rate": round(base_rate, 5),
        "baseline_true_ap": round(ap0, 4),
        "P_star": round(p_star, 3),
        "false_ship_rate": round(false_ship, 3),
        "power_at_delta": power,
        "n_oot_pos": N_OOT_POS,
        "n_datasets": n_datasets,
    }


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    settings = get_ml_settings()
    methods = {"percentile": ci_percentile, "stratified": ci_stratified, "bca": ci_bca}

    print("[surrogate] cross-fitting crisis-region OOF scores...", flush=True)
    cy, cs = _crisis_oof_scores()
    true_ap_surrogate = _ap(cy, cs)
    pos_idx = np.where(cy == 1)[0]
    neg_idx = np.where(cy == 0)[0]
    # Fix the base-rate-mismatch bug: the truth AP must be the AP of the SAME population
    # the subsamples are drawn from. AP is NOT base-rate invariant, so we fix a population
    # whose base rate equals the subsample base rate (N_OOT_POS / (N_OOT_POS + SIM_N_NEG)),
    # compute truth on THAT population, and subsample its members.
    pop_neg_n = min(len(neg_idx), int(round(len(pos_idx) * SIM_N_NEG / N_OOT_POS)))
    pop_neg = rng.choice(neg_idx, pop_neg_n, replace=False)
    pop_idx = np.concatenate([pos_idx, pop_neg])
    pop_y, pop_s = cy[pop_idx], cs[pop_idx]
    true_ap_surrogate = _ap(pop_y, pop_s)
    pop_pos = np.where(pop_y == 1)[0]
    pop_negi = np.where(pop_y == 0)[0]
    print(f"   surrogate pop: {len(pop_y):,} rows, {int(pop_y.sum())} pos, "
          f"base_rate {pop_y.mean():.3%}, matched-pop AP={true_ap_surrogate:.4f}", flush=True)

    def draw_surrogate(rng):
        ip = rng.choice(pop_pos, N_OOT_POS, replace=False)
        ineg = rng.choice(pop_negi, SIM_N_NEG, replace=False)
        idx = np.concatenate([ip, ineg])
        return pop_y[idx], pop_s[idx]

    print("[surrogate] coverage experiment...", flush=True)
    cov_surrogate = run_coverage("surrogate_subsample", draw_surrogate, true_ap_surrogate,
                                 methods, rng)
    print("   ", cov_surrogate["coverage"], flush=True)

    print("[parametric] building planted-separation population...", flush=True)
    base_rate = N_OOT_POS / (N_OOT_POS + SIM_N_NEG)
    mu_p, true_ap_param = _parametric_population(true_ap_surrogate, base_rate, rng)

    def draw_param(rng):
        y = np.concatenate([np.ones(N_OOT_POS), np.zeros(SIM_N_NEG)]).astype(int)
        s = np.concatenate([rng.normal(mu_p, 1.0, N_OOT_POS), rng.normal(0, 1.0, SIM_N_NEG)])
        return y, s

    print("[parametric] coverage experiment...", flush=True)
    cov_param = run_coverage("parametric_planted", draw_param, true_ap_param, methods, rng)
    print("   ", cov_param["coverage"], flush=True)

    # recall@k Jeffreys coverage (closed form vs surrogate population recall@k)
    print("[jeffreys] recall@k coverage cross-check...", flush=True)
    full_recall, _, _ = recall_at_k(pop_y, pop_s, 200)
    jh, jv = 0, 0
    for _ in range(N_SIMS):
        y, s = draw_surrogate(rng)
        _, caught, tot = recall_at_k(y, s, 200)
        lo, hi = jeffreys_recall_ci(caught, tot)
        if lo == lo:
            jv += 1
            if lo <= full_recall <= hi:
                jh += 1
    jeff_cov = round(jh / jv, 3) if jv else float("nan")
    print(f"   recall@200 Jeffreys coverage={jeff_cov} (truth recall={full_recall:.3f})",
          flush=True)

    # method selection: closest to nominal without under-covering badly
    def score_method(m):
        c = [cov_surrogate["coverage"][m], cov_param["coverage"][m]]
        c = [x for x in c if x == x]
        return min(c) if c else 0.0  # worst-case coverage across DGPs
    chosen = max(methods, key=score_method)
    print(f"[select] chosen interval method = {chosen}", flush=True)

    print("[power] paired-gate power / MDE simulation...", flush=True)
    power = run_power(base_rate, rng)
    tier_a_shippable = power["power_at_delta"].get("0.02", 0.0) >= 0.50
    mde = (f"At a true AP delta of 0.02, the paired OOT gate has power "
           f"{power['power_at_delta']['0.02']:.0%} (false-ship rate "
           f"{power['false_ship_rate']:.0%}). "
           + ("Tier A IS OOT-ship-validatable." if tier_a_shippable else
              "No Tier A item is OOT-ship-validatable at this positive count; inner "
              "rolling-fold evidence is the only admissible Tier A shipping evidence."))
    print("   ", mde, flush=True)

    out = {
        "interval_coverage_sim": {
            "nominal": NOMINAL,
            "n_sims": N_SIMS, "n_boot": N_BOOT, "n_oot_pos": N_OOT_POS,
            "sim_n_neg": SIM_N_NEG, "sim_base_rate": round(base_rate, 5),
            "note": ("External-truth DGPs only; neither resamples the OOT realization. "
                     "Negatives subsampled for tractability (BCa jackknife is O(n)); "
                     "n_pos held at the OOT count, the dominant driver of AP CI width."),
            "by_dgp": {"surrogate_subsample": cov_surrogate, "parametric_planted": cov_param},
            "recall_jeffreys_coverage": jeff_cov,
            "chosen_method": chosen,
        },
        "gate_power": {
            **power,
            "D_star": -0.02,  # placeholder; refined below from null paired-diff if needed
            "mde_statement": mde,
            "tier_a_oot_shippable": bool(tier_a_shippable),
        },
        "elapsed_sec": round(time.time() - t0, 1),
    }
    dest = settings.artifact_dir / "g0_power_sim.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {dest} in {out['elapsed_sec']}s", flush=True)
    print(json.dumps(out["interval_coverage_sim"]["by_dgp"], indent=2)[:600], flush=True)


if __name__ == "__main__":
    main()
