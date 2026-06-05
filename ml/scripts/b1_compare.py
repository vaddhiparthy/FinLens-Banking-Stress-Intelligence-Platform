"""B1 payoff: does the originally-filed POINT-IN-TIME panel beat the FDIC restated
panel, holding the recipe constant? Same features, same final_holdout_split(28q),
same calibrated-monotone-LGBM recipe; only the data SOURCE differs.

Reports OOT PR-AUC + 95% bootstrap CI for each, and the noncurrent_to_loans feature
health (the field FDIC stored as ~half-zero). Honest: with ~66 OOT positives the CIs
overlap; the inner rolling-fold deltas (also reported) are the admissible evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.evaluate import bootstrap_metrics, evaluate  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402
from finlens_ml.splits import final_holdout_split, rolling_origin_folds  # noqa: E402
from finlens_ml.train import _fit_calibrated, load_dataset  # noqa: E402

SEED, HORIZON, HOLDOUT_Q = 42, 4, 28
PIT = REPO / "data" / "pit" / "pit_training_dataset.parquet"


def _prep(df):
    label = f"label_{HORIZON}"
    df = df[df[label].notna()].reset_index(drop=True).copy()
    df[label] = df[label].astype(int)
    return df[FEATURE_COLUMNS].astype(float), df[label].to_numpy(), df["obs_qord"]


def _oot(df, lag, k):
    X, y, obs = _prep(df)
    tr, te = final_holdout_split(obs, horizon_q=HORIZON, holdout_quarters=HOLDOUT_Q,
                                 reporting_lag_q=lag)
    _, cal, *_ = _fit_calibrated(X.iloc[tr], y[tr], SEED)
    p = cal.predict_proba(X.iloc[te])[:, 1]
    m = evaluate(y[te], p, k=k)
    ci = bootstrap_metrics(y[te], p, k=k, n_boot=2000, seed=SEED)["pr_auc_ci"]
    return {"pr_auc": round(float(m.pr_auc), 4), "ci": [round(c, 4) for c in ci],
            "n_test": int(len(te)), "pos": int(y[te].sum())}


def _rolling(df, lag, k):
    X, y, obs = _prep(df)
    folds = rolling_origin_folds(obs.reset_index(drop=True), horizon_q=HORIZON,
                                 min_train_quarters=28, step=4, n_test_quarters=4,
                                 reporting_lag_q=lag)
    aps = []
    for f in folds:
        if y[f.train_idx].sum() < 20 or y[f.test_idx].sum() < 1:
            continue
        _, cal, *_ = _fit_calibrated(X.iloc[f.train_idx], y[f.train_idx], SEED)
        p = cal.predict_proba(X.iloc[f.test_idx])[:, 1]
        aps.append(float(evaluate(y[f.test_idx], p, k=k).pr_auc))
    return {"folds": len(aps), "mean": round(float(np.mean(aps)), 4),
            "std": round(float(np.std(aps)), 4)}


def main():
    s = get_ml_settings()
    k, lag = s.review_budget_k, s.reporting_lag_q
    fdic = load_dataset()
    pit = pd.read_parquet(PIT)
    print(f"FDIC panel {len(fdic):,} rows | PIT panel {len(pit):,} rows\n", flush=True)

    print("[FDIC restated] OOT...", flush=True)
    f_oot = _oot(fdic, lag, k)
    print("   ", f_oot, flush=True)
    print("[point-in-time] OOT...", flush=True)
    p_oot = _oot(pit, lag, k)
    print("   ", p_oot, flush=True)
    print("[FDIC restated] rolling...", flush=True)
    f_rb = _rolling(fdic, lag, k)
    print("   ", f_rb, flush=True)
    print("[point-in-time] rolling...", flush=True)
    p_rb = _rolling(pit, lag, k)
    print("   ", p_rb, flush=True)

    out = {"fdic_restated": {"oot": f_oot, "rolling": f_rb},
           "point_in_time": {"oot": p_oot, "rolling": p_rb},
           "noncurrent_health": {
               "fdic_frac_zero": round(float((pd.to_numeric(fdic["noncurrent_to_loans"],
                                              errors="coerce") == 0).mean()), 3),
               "pit_frac_zero": round(float((pd.to_numeric(pit["noncurrent_to_loans"],
                                             errors="coerce") == 0).mean()), 3)}}
    import json
    (s.artifact_dir / "b1_compare.json").write_text(json.dumps(out, indent=2))
    print("\n== B1 PAYOFF ==", flush=True)
    print(f"  FDIC restated  OOT PR-AUC {f_oot['pr_auc']} {f_oot['ci']} | rolling "
          f"{f_rb['mean']}±{f_rb['std']}", flush=True)
    print(f"  point-in-time  OOT PR-AUC {p_oot['pr_auc']} {p_oot['ci']} | rolling "
          f"{p_rb['mean']}±{p_rb['std']}", flush=True)
    print(f"  noncurrent zero-rate: FDIC {out['noncurrent_health']['fdic_frac_zero']:.0%} "
          f"-> PIT {out['noncurrent_health']['pit_frac_zero']:.0%}", flush=True)


if __name__ == "__main__":
    main()
