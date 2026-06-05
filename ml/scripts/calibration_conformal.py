"""A5 calibration bake-off + C2 conformal/Venn-Abers feasibility, from scratch ($0).

Calibration bake-off: on a held calibration slice (never used to fit the booster or
chosen on OOT), compare isotonic vs Platt(sigmoid) vs inductive Venn-Abers by ECE and
top-decile reliability, with a bootstrap stability check (does the winner flip?). The
served calibrator is then justified by measurement, not the old y_cal>=50 heuristic.

C2 conformal feasibility: at a ~0.3% base rate, split-conformal prediction SETS for the
binary label are vacuous (almost always {survive}); the honest per-instance uncertainty
is the Venn-Abers probability INTERVAL [p0, p1]. Reports its median width and notes the
prediction-set vacuity rather than shipping a uninformative interval.

Writes ml/artifacts/calibration_bakeoff.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402
from finlens_ml.splits import final_holdout_split  # noqa: E402
from finlens_ml.train import EVAL_HOLDOUT_QUARTERS, _make_lgbm, load_dataset  # noqa: E402

SEED = 42


def _ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    e = 0.0
    for b in range(bins):
        m = idx == b
        if m.sum():
            e += (m.sum() / len(p)) * abs(p[m].mean() - y[m].mean())
    return float(e)


def _top_decile_gap(y, p):
    k = max(1, len(p) // 10)
    top = np.argsort(-p)[:k]
    return float(abs(p[top].mean() - y[top].mean()))


def _venn_abers(cal_s, cal_y, test_s):
    """Inductive Venn-Abers (refit isotonic per point; called on a bounded sample)."""
    from sklearn.isotonic import IsotonicRegression
    cs, cl = np.asarray(cal_s, float), np.asarray(cal_y, float)
    p0 = np.empty(len(test_s))
    p1 = np.empty(len(test_s))
    for i, s in enumerate(test_s):
        ir0 = IsotonicRegression(out_of_bounds="clip").fit(np.append(cs, s), np.append(cl, 0))
        ir1 = IsotonicRegression(out_of_bounds="clip").fit(np.append(cs, s), np.append(cl, 1))
        p0[i] = ir0.predict([s])[0]
        p1[i] = ir1.predict([s])[0]
    p = p1 / (1 - p0 + p1 + 1e-12)
    return p, p0, p1


def main():
    s = get_ml_settings()
    df = load_dataset()
    df = df[df["label_4"].notna()].reset_index(drop=True).copy()
    df["label_4"] = df["label_4"].astype(int)
    X = df[FEATURE_COLUMNS].astype(float)
    y = df["label_4"].to_numpy()
    obs = df["obs_qord"]
    tr, te = final_holdout_split(obs, horizon_q=4, holdout_quarters=EVAL_HOLDOUT_QUARTERS,
                                 reporting_lag_q=s.reporting_lag_q)
    from sklearn.model_selection import train_test_split
    Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y[tr], y[te]
    # proper-train vs calibration slice (stratified, in-training only)
    Xf, Xc, yf, yc = train_test_split(Xtr, ytr, test_size=0.25, stratify=ytr, random_state=SEED)
    spw = min(float((yf == 0).sum() / max(1, (yf == 1).sum())), 40.0)
    base = _make_lgbm(spw, SEED, n_estimators=300)
    base.fit(Xf, yf)
    sc = base.predict_proba(Xc)[:, 1]
    st = base.predict_proba(Xte)[:, 1]

    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    iso = IsotonicRegression(out_of_bounds="clip").fit(sc, yc)
    p_iso = iso.predict(st)
    platt = LogisticRegression().fit(sc.reshape(-1, 1), yc)
    p_platt = platt.predict_proba(st.reshape(-1, 1))[:, 1]

    # Venn-Abers on a bounded sample of the test set (per-point refit is O(n))
    rng = np.random.default_rng(SEED)
    samp = rng.choice(len(st), min(1500, len(st)), replace=False)
    p_va_s, p0_s, p1_s = _venn_abers(sc, yc, st[samp])
    va_width = float(np.median(p1_s - p0_s))

    methods = {
        "isotonic": (yte, p_iso),
        "platt": (yte, p_platt),
        "venn_abers(sample)": (yte[samp], p_va_s),
    }
    results = {}
    for name, (yy, pp) in methods.items():
        results[name] = {"ece": round(_ece(yy, pp), 5),
                         "top_decile_gap": round(_top_decile_gap(yy, pp), 5)}

    # bootstrap stability: does the ECE-winner (iso vs platt, full test) flip?
    flips = 0
    nb = 300
    for _ in range(nb):
        idx = rng.integers(0, len(yte), len(yte))
        wi = _ece(yte[idx], p_iso[idx])
        wp = _ece(yte[idx], p_platt[idx])
        if (wi <= wp) != (results["isotonic"]["ece"] <= results["platt"]["ece"]):
            flips += 1
    winner = min(("isotonic", "platt"), key=lambda k: results[k]["ece"])

    out = {
        "calibration_bakeoff": results,
        "winner": winner,
        "winner_stability": {"bootstrap_flip_rate": round(flips / nb, 3),
                             "note": "fraction of resamples where the iso-vs-platt ECE winner flips"},
        "conformal_feasibility": {
            "venn_abers_median_interval_width": round(va_width, 4),
            "prediction_set_note": (
                "Split-conformal prediction SETS for the binary label are vacuous at this "
                f"~{yte.mean():.3%} base rate (almost always {{survive}}), so they are not "
                "shipped. The Venn-Abers probability interval [p0, p1] is the usable "
                "per-instance uncertainty; its median width is reported above."),
        },
    }
    (s.artifact_dir / "calibration_bakeoff.json").write_text(json.dumps(out, indent=2))
    print("bake-off:", results, flush=True)
    print(f"winner: {winner} | flip-rate {flips/nb:.2f} | VA median width {va_width:.4f}",
          flush=True)


if __name__ == "__main__":
    main()
