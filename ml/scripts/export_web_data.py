"""Bake REAL model/data artifacts into JSON for the bespoke web frontend.

Outputs to web/data/: meta.json, performance.json, banks.json, timeline.json,
features.json. Every number is computed from the real DuckDB panel + trained model +
metrics artifact. No fabrication. The frontend renders these + calls the live
/predict endpoint for the hypothetical-bank tab.
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
from finlens_ml.scenario import SLIDER_FEATURES  # noqa: E402

OUT = REPO / "web" / "data"


def _conn():
    import duckdb

    return duckdb.connect(str(get_ml_settings().duckdb_path), read_only=True)


def _clean(obj):
    """Recursively replace non-finite floats (NaN/Inf) with None so the JSON is valid
    (bare NaN breaks browser JSON.parse and blanks the page)."""
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _dump(path, payload):
    path.write_text(json.dumps(_clean(payload), indent=1, allow_nan=False, default=str))


def _quarter_label(qord: int) -> str:
    return f"{qord // 4}Q{qord % 4 + 1}"


def export_meta(metrics: dict) -> dict:
    t = metrics["oot_test"]
    fm = metrics.get("final_model", {})
    cal = metrics.get("oot_calibration", {})
    return {
        "model_version": f"distress-h{metrics['horizon_q']}",
        "horizon_q": metrics["horizon_q"],
        "n_features": len(FEATURE_COLUMNS),
        "trees": fm.get("n_estimators"),
        "calibration": fm.get("calibration_method"),
        "oot": {
            "window_q": metrics["eval_window_quarters"],
            "n_test": metrics["n_test"],
            "failures": metrics["test_positives"],
            "base_rate_pct": round(metrics["test_positives"] / metrics["n_test"] * 100, 4),
            "pr_auc": round(t["calibrated_lgbm"]["pr_auc"], 4),
            "roc_auc": round(t["calibrated_lgbm"]["roc_auc"], 4),
            "recall_at_k": round(t["calibrated_lgbm"]["recall_at_k"], 3),
            "k": t["calibrated_lgbm"]["k"],
            "logit_pr_auc": round(t["logit_benchmark"]["pr_auc"], 4),
            "logit_roc_auc": round(t["logit_benchmark"]["roc_auc"], 4),
            "ece": cal.get("ece"),
        },
    }


def export_performance(metrics: dict, conn) -> dict:
    from sklearn.metrics import precision_recall_curve, roc_curve

    from finlens_ml.predict import score_frame
    from finlens_ml.splits import final_holdout_split

    label = "label_4"
    df = conn.execute("select * from ml.training_dataset").df()
    df = df[df[label].notna()].reset_index(drop=True)
    df[label] = df[label].astype(int)
    _, te = final_holdout_split(df["obs_qord"], horizon_q=4, holdout_quarters=28)
    test = df.iloc[te]
    y = test[label].to_numpy()
    p = score_frame(test, 4)
    prec, rec, _ = precision_recall_curve(y, p)
    # downsample curve points for compact JSON
    idx = np.linspace(0, len(rec) - 1, min(60, len(rec))).astype(int)
    fpr, tpr, _ = roc_curve(y, p)
    ridx = np.linspace(0, len(fpr) - 1, min(60, len(fpr))).astype(int)
    by_year = metrics.get("by_year_calibrated", {})
    return {
        "pr_curve": [[round(float(rec[i]), 4), round(float(prec[i]), 4)] for i in idx],
        "roc_curve": [[round(float(fpr[i]), 4), round(float(tpr[i]), 4)] for i in ridx],
        "by_year": [
            {"year": yr, "n": v["n"], "failures": v["n_positive"],
             "roc_auc": None if isinstance(v["roc_auc"], str) else round(v["roc_auc"], 3),
             "pr_auc": None if isinstance(v["pr_auc"], str) else round(v["pr_auc"], 3)}
            for yr, v in by_year.items()
        ],
    }


def export_timeline(conn) -> list:
    # failures per quarter (from labeled positives' transition), for the hero chart
    df = conn.execute(
        "select quarter, obs_qord, fail_qord from ml.training_dataset where fail_qord is not null"
    ).df()
    fails = df.drop_duplicates("fail_qord") if "fail_qord" in df else df
    counts = (
        conn.execute(
            "select cast(fail_qord as int) fq, count(distinct cert) n "
            "from ml.training_dataset where fail_qord is not null group by fq order by fq"
        ).df()
    )
    return [{"quarter": _quarter_label(int(r.fq)), "failures": int(r.n)} for r in counts.itertuples()]


def _eval_model(df):
    """Train an out-of-time model on <=2018 only, so 2019+ failures (SVB, the 2023
    cluster) are scored genuinely held-out, not in-sample/memorized."""
    import lightgbm as lgb

    tr = df[(df["obs_qord"] < 2019 * 4) & (df["label_4"].notna())]
    X = tr[FEATURE_COLUMNS].astype(float)
    y = tr["label_4"].astype(int).to_numpy()
    mc = [MONOTONE_CONSTRAINTS[c] for c in FEATURE_COLUMNS]
    spw = min(float((y == 0).sum() / max(1, (y == 1).sum())), 25.0)
    m = lgb.LGBMClassifier(
        objective="binary", n_estimators=300, learning_rate=0.03, num_leaves=31,
        min_child_samples=100, monotone_constraints=mc, scale_pos_weight=spw,
        n_jobs=4, random_state=42, verbose=-1,
    )
    m.fit(X, y)
    return m


def export_banks(conn) -> list:
    from finlens_ml.predict import decision, score_frame

    df = conn.execute("select * from ml.training_dataset").df()
    out = []
    pos = df[df["label_4"] == 1].sort_values("obs_qord").drop_duplicates("cert", keep="first")
    # served (all-data) score for training-era banks; out-of-time eval model for 2019+ banks
    served = score_frame(df, 4)
    evalm = _eval_model(df)
    oot = evalm.predict_proba(df[FEATURE_COLUMNS].astype(float))[:, 1]
    df["_served"] = served
    df["_oot"] = oot
    df["_held"] = df["fail_qord"].notna() & (df["fail_qord"] >= 2019 * 4)
    df["_score"] = np.where(df["_held"], df["_oot"], df["_served"])
    for r in pos.itertuples():
        fail_year = int(r.fail_qord) // 4 if not pd.isna(r.fail_qord) else None
        held = fail_year is not None and fail_year >= 2019
        col = "_oot" if held else "_served"  # like-with-like cohort scoring
        coh = df[df["quarter"] == r.quarter]
        srow = df[(df["cert"] == r.cert) & (df["quarter"] == r.quarter)]
        if srow.empty:
            continue
        s = float(srow[col].iloc[0])
        pct = round(float((coh[col] < s).mean() * 100), 1)
        feats = {c: (None if pd.isna(srow[c].iloc[0]) else round(float(srow[c].iloc[0]), 4))
                 for c in FEATURE_COLUMNS}
        out.append({
            "cert": int(r.cert),
            "name": r.bank_name,
            "state": r.state if isinstance(r.state, str) else None,
            "as_of": r.quarter,
            "score": round(s, 4),
            "percentile": pct,
            "flagged": decision(s)["flagged"],
            "outcome": "failed",
            "fail_year": fail_year,
            "held_out": held,
            "basis": "out-of-time (model never trained on this era)" if held
            else "training-era (illustrative)",
            "uninsured": feats.get("uninsured_deposit_share"),
            "htm": feats.get("htm_securities_share"),
            "assets_m": (None if pd.isna(srow["ASSET"].iloc[0]) else int(srow["ASSET"].iloc[0])),
            "features": feats,
        })
    out.sort(key=lambda b: (b["fail_year"] or 0), reverse=True)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((get_ml_settings().artifact_dir / "metrics_h4.json").read_text())
    conn = _conn()
    _dump(OUT / "meta.json", export_meta(metrics))
    _dump(OUT / "performance.json", export_performance(metrics, conn))
    _dump(OUT / "timeline.json", export_timeline(conn))
    _dump(OUT / "banks.json", export_banks(conn))
    _dump(OUT / "features.json", {
        "features": FEATURE_COLUMNS,
        "monotone": MONOTONE_CONSTRAINTS,
        "sliders": {k: list(v) for k, v in SLIDER_FEATURES.items()},
    })
    banks = json.loads((OUT / "banks.json").read_text())
    print(f"wrote web/data/: {len(banks)} failed banks, meta+performance+timeline+features")


if __name__ == "__main__":
    main()
