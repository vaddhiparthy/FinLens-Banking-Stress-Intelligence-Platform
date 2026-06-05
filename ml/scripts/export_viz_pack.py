"""Bake a REAL analytics viz-pack for the AI Engineering surface.

Everything is computed from the real DuckDB panel + an out-of-time eval model
(trained on <=2018, scored on 2019+ so the failures are genuinely held out, the same
protocol as the shipped metrics). No fabrication. Output: ml/artifacts/viz_pack.json.

Charts driven by this pack: PR curve, ROC curve, calibration reliability diagram,
score distribution (failed vs survived), threshold sweep, SHAP global importance,
feature correlation heatmap, by-year performance, per-feature drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS, MONOTONE_CONSTRAINTS  # noqa: E402

ART = REPO / "ml" / "artifacts"
OOT_YEAR = 2019


def _conn():
    import duckdb

    return duckdb.connect(str(get_ml_settings().duckdb_path), read_only=True)


def _oot_predictions():
    """Reproduce the SHIPPED eval protocol (train.py): final_holdout_split(28) +
    _fit_calibrated, so the curves match the Model Quality table exactly. Returns
    (y_te, p_cal, p_logit, year_te)."""
    from finlens_ml.splits import final_holdout_split
    from finlens_ml.train import (
        EVAL_HOLDOUT_QUARTERS,
        _fit_calibrated,
        _fit_logit,
        load_dataset,
    )

    df = load_dataset()
    df = df[df["label_4"].notna()].reset_index(drop=True).copy()
    df["label_4"] = df["label_4"].astype(int)
    X = df[FEATURE_COLUMNS].astype(float)
    y = df["label_4"].to_numpy()
    obs = df["obs_qord"]
    tr_idx, te_idx = final_holdout_split(
        obs, horizon_q=4, holdout_quarters=EVAL_HOLDOUT_QUARTERS,
        reporting_lag_q=get_ml_settings().reporting_lag_q,
    )
    X_tr, y_tr = X.iloc[tr_idx], y[tr_idx]
    X_te, y_te = X.iloc[te_idx], y[te_idx]
    year_te = (obs.iloc[te_idx].to_numpy() // 4).astype(int)
    # reuse the SAME tuned hyperparameters the shipped model was trained with, so the
    # curves match the served model and the metrics table.
    metrics = json.loads((ART / "metrics_h4.json").read_text())
    best_params = metrics.get("hyperparameter_tuning", {}).get("best_params") or None
    eval_model, eval_cal, *_ = _fit_calibrated(X_tr, y_tr, 42, params=best_params)
    logit = _fit_logit(X_tr, y_tr)
    p_cal = eval_cal.predict_proba(X_te)[:, 1]
    p_logit = logit.predict_proba(X_te)[:, 1]
    return y_te, p_cal, p_logit, year_te


def _psi_report(top_features: list[str], n_bins: int = 10) -> list[dict]:
    """Population Stability Index per feature: reference (<=2018) vs current (2019+).
    PSI < 0.1 stable, 0.1-0.25 moderate shift, > 0.25 significant shift."""
    conn = _conn()
    df = conn.execute("select * from ml.training_dataset").df()
    conn.close()
    ref = df[df["obs_qord"] < 2019 * 4]
    cur = df[df["obs_qord"] >= 2019 * 4]
    rows = []
    for f in top_features:
        r = pd.to_numeric(ref[f], errors="coerce").dropna()
        c = pd.to_numeric(cur[f], errors="coerce").dropna()
        if len(r) < 50 or len(c) < 50:
            continue
        edges = np.unique(np.quantile(r, np.linspace(0, 1, n_bins + 1)))
        if len(edges) < 3:
            continue
        r_pct = np.histogram(r, bins=edges)[0] / len(r)
        c_pct = np.histogram(c, bins=edges)[0] / len(c)
        eps = 1e-4
        r_pct = np.clip(r_pct, eps, None)
        c_pct = np.clip(c_pct, eps, None)
        psi = float(np.sum((c_pct - r_pct) * np.log(c_pct / r_pct)))
        rows.append({"feature": f, "psi": round(psi, 3)})
    return sorted(rows, key=lambda x: -x["psi"])


def _curves(y, p):
    from sklearn.metrics import (
        average_precision_score,
        precision_recall_curve,
        roc_auc_score,
        roc_curve,
    )

    prec, rec, _ = precision_recall_curve(y, p)
    pidx = np.linspace(0, len(rec) - 1, min(80, len(rec))).astype(int)
    fpr, tpr, _ = roc_curve(y, p)
    ridx = np.linspace(0, len(fpr) - 1, min(80, len(fpr))).astype(int)
    return {
        "pr_auc": round(float(average_precision_score(y, p)), 4),
        "roc_auc": round(float(roc_auc_score(y, p)), 4),
        "base_rate": round(float(y.mean()), 5),
        "pr_curve": [[round(float(rec[i]), 4), round(float(prec[i]), 4)] for i in pidx],
        "roc_curve": [[round(float(fpr[i]), 4), round(float(tpr[i]), 4)] for i in ridx],
    }


def _calibration(y, p, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, bins) - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = idx == b
        if mask.sum() == 0:
            continue
        rows.append({
            "pred": round(float(p[mask].mean()), 4),
            "obs": round(float(y[mask].mean()), 4),
            "n": int(mask.sum()),
        })
    return rows


def _score_distribution(y, p, n_bins=30):
    edges = np.linspace(0, float(p.max()) if p.max() > 0 else 1.0, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    failed = np.histogram(p[y == 1], bins=edges)[0]
    survived = np.histogram(p[y == 0], bins=edges)[0]
    return {
        "centers": [round(float(c), 4) for c in centers],
        "failed": [int(v) for v in failed],
        "survived": [int(v) for v in survived],
    }


def _threshold_sweep(y, p):
    rows = []
    for t in np.linspace(0.02, 0.6, 30):
        flagged = p >= t
        n_flag = int(flagged.sum())
        tp = int((flagged & (y == 1)).sum())
        prec = tp / n_flag if n_flag else 0.0
        rec = tp / int((y == 1).sum()) if (y == 1).sum() else 0.0
        rows.append({
            "threshold": round(float(t), 3),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "flagged": n_flag,
        })
    return rows


def _shap_importance(sample, top_k=15):
    import shap

    booster = _load_booster()
    expl = shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent")
    X = sample[FEATURE_COLUMNS].astype(float)
    sv = expl.shap_values(X)
    if isinstance(sv, list):
        sv = sv[1] if len(sv) > 1 else sv[0]
    mean_abs = np.abs(sv).mean(axis=0)
    order = np.argsort(-mean_abs)[:top_k]
    return [
        {"feature": FEATURE_COLUMNS[i], "mean_abs_shap": round(float(mean_abs[i]), 5)}
        for i in order
    ]


def _load_booster():
    import lightgbm as lgb

    return lgb.Booster(model_file=str(ART / "booster_h4.txt"))


def _correlation(sample, top_features):
    sub = sample[top_features].astype(float)
    corr = sub.corr().fillna(0.0).round(3)
    return {"features": top_features, "matrix": corr.values.tolist()}


def main() -> None:
    # Curves/calibration/distribution from the shipped calibrated OOT predictions.
    y, p_cal, p_logit, year_te = _oot_predictions()
    lc = _curves(y, p_logit)

    # SHAP + correlation on a bounded reproducible sample of the full panel.
    conn = _conn()
    df = conn.execute("select * from ml.training_dataset").df()
    conn.close()
    sample = df.sample(n=min(3000, len(df)), random_state=42)
    shap_imp = _shap_importance(sample)
    top_feats = [r["feature"] for r in shap_imp[:12]]

    drift = {}
    drift_path = ART / "drift_report.json"
    if drift_path.exists():
        drift = json.loads(drift_path.read_text())

    pack = {
        "oot_window_start_year": OOT_YEAR,
        "n_oot": int(len(y)),
        "n_oot_failures": int(y.sum()),
        "curves": _curves(y, p_cal),
        "logit_curves": {"pr_auc": lc["pr_auc"], "roc_auc": lc["roc_auc"],
                         "pr_curve": lc["pr_curve"], "roc_curve": lc["roc_curve"]},
        "calibration": _calibration(y, p_cal),
        "score_distribution": _score_distribution(y, p_cal),
        "threshold_sweep": _threshold_sweep(y, p_cal),
        "shap_importance": shap_imp,
        "correlation": _correlation(sample, top_feats),
        "psi": _psi_report(top_feats),
        "drift_top_features": drift.get("top_drifted_features", []),
        "drift_summary": {
            "n_features_analyzed": drift.get("n_features_analyzed"),
            "n_drifted_columns": drift.get("n_drifted_columns"),
            "share_of_drifted_columns": drift.get("share_of_drifted_columns"),
            "prediction_drift_score": drift.get("prediction_drift_score"),
        },
    }
    out = ART / "viz_pack.json"
    out.write_text(json.dumps(pack, indent=1, allow_nan=False, default=str))
    print(f"wrote {out}")
    print(f"OOT: {pack['n_oot']:,} rows, {pack['n_oot_failures']} failures; "
          f"calibrated PR-AUC={pack['curves']['pr_auc']} ROC-AUC={pack['curves']['roc_auc']}; "
          f"logit PR-AUC={lc['pr_auc']}; base_rate={pack['curves']['base_rate']}")
    print(f"SHAP top: {[r['feature'] for r in shap_imp[:5]]}")


if __name__ == "__main__":
    main()
