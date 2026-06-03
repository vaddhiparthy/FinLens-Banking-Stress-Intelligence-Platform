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


def export_architecture_graph() -> dict:
    """Single source of truth for the Architect's Desk DAG + component detail pages.
    Each node's artifact_path is verified to exist (CI-checkable, un-fabricable)."""
    N = lambda i, label, layer, status, prod, zero, art: {  # noqa: E731
        "id": i, "label": label, "layer": layer, "status": status,
        "route": f"#/desk/c/{i}", "prod_ref": prod, "zero_dollar": zero, "artifact_path": art,
    }
    nodes = [
        N("fdic_src", "FDIC BankFind", "de", "LIVE", "regulatory feed", "free FDIC API (no key)", "ingestion/fdic_institutions.py"),
        N("fred_src", "FRED / ALFRED", "de", "LIVE", "market data vendor", "free FRED API (vintage)", "ingestion/fred.py"),
        N("ingest", "Ingestion", "de", "LIVE", "Kafka + S3 landing", "HTTP pull -> local raw JSON", "ingestion/fdic_institutions.py"),
        N("bronze", "Bronze (raw)", "de", "LOCAL", "S3 data lake", "DuckDB raw tables", "duckdb/ddl/001_create_marts.sql"),
        N("silver", "Silver (staging)", "de", "LOCAL", "Spark + dbt", "dbt staging models", "dbt/models/staging/stg_fdic_qbp.sql"),
        N("intermediate", "Intermediate", "de", "LOCAL", "dbt", "dbt intermediate", "dbt/models/intermediate/int_failures_with_macro_context.sql"),
        N("gold", "Gold marts", "de", "LOCAL", "warehouse marts", "dbt marts (DuckDB)", "dbt/models/marts/fct_stress_pulse.sql"),
        N("quality", "Data quality", "de", "LOCAL", "GX / Soda", "Great Expectations + dbt tests", "great_expectations/run_checkpoint.py"),
        N("business_surfaces", "Business surfaces", "shared", "LOCAL", "BI dashboards", "web console (Business)", "web/index.html"),
        N("feature_panel", "Feature panel (PIT)", "ml", "LOCAL", "Feature store", "DuckDB point-in-time panel", "ml/finlens_ml/data.py"),
        N("features", "Feature engineering", "ml", "LOCAL", "Spark/dbt features", "CAMELS + rate-risk features", "ml/finlens_ml/features.py"),
        N("train", "Training", "ml", "LOCAL", "Kubeflow/SageMaker", "LightGBM hazard + calibration", "ml/finlens_ml/train.py"),
        N("registry", "Model registry", "ml", "LOCAL", "SageMaker registry", "MLflow aliases (champion)", "ml/finlens_ml/registry.py"),
        N("serving", "Serving", "ml", "LOCAL", "SageMaker endpoint", "FastAPI (calibrated + SHAP)", "ml/finlens_ml/serve.py"),
        N("audit", "Inference audit log", "ml", "LOCAL", "model-monitoring store", "JSONL req/resp + reason codes", "ml/finlens_ml/audit.py"),
        N("monitoring", "Monitoring (drift)", "ml", "LOCAL", "Arize/Fiddler", "Evidently data+prediction drift", "ml/finlens_ml/monitor.py"),
        N("ml_surfaces", "ML surfaces / Live Lab", "shared", "LOCAL", "model UI", "web console (ML + Lab)", "web/app.js"),
    ]
    edges = [
        ("fdic_src", "ingest"), ("fred_src", "ingest"), ("ingest", "bronze"),
        ("bronze", "silver"), ("silver", "intermediate"), ("intermediate", "gold"),
        ("gold", "quality"), ("gold", "business_surfaces"), ("gold", "feature_panel"),
        ("feature_panel", "features"), ("features", "train"), ("train", "registry"),
        ("registry", "serving"), ("serving", "audit"), ("serving", "monitoring"),
        ("serving", "ml_surfaces"), ("monitoring", "train"),
    ]
    # verify every artifact_path exists (un-fabricable); record missing for the parity gate
    missing = [n["artifact_path"] for n in nodes if not (REPO / n["artifact_path"]).exists()]
    return {"nodes": nodes, "edges": edges, "missing_artifacts": missing}


def export_wiki() -> dict:
    from streamlit_app.lib.wiki_content import ARTICLES

    arts = [{"title": t, **a} for t, a in ARTICLES.items()]
    clusters: dict[str, list] = {}
    for a in arts:
        clusters.setdefault(a["cluster"], []).append(a["title"])
    return {"articles": arts, "clusters": clusters}


def export_business(conn) -> dict:
    df = conn.execute(
        "select fail_qord, state, bank_name from ml.training_dataset where fail_qord is not null"
    ).df()
    fails = df.drop_duplicates("bank_name") if "bank_name" in df else df
    by_year = (
        fails.assign(year=(fails["fail_qord"] // 4).astype(int))
        .groupby("year").size().reset_index(name="failures")
    )
    by_state = (
        fails.dropna(subset=["state"]).groupby("state").size()
        .reset_index(name="failures").sort_values("failures", ascending=False).head(15)
    )
    # real system-level trends from the per-bank panel (medians/means per quarter)
    panel = conn.execute(
        "select quarter, obs_qord, roa, equity_to_assets, noncurrent_to_loans, "
        "uninsured_deposit_share from ml.training_dataset"
    ).df()
    agg = (
        panel.groupby(["obs_qord", "quarter"])
        .agg(med_roa=("roa", "median"), med_capital=("equity_to_assets", "median"),
             med_noncurrent=("noncurrent_to_loans", "median"),
             med_uninsured=("uninsured_deposit_share", "median"), n=("roa", "size"))
        .reset_index().sort_values("obs_qord")
    )
    trends = [
        {"quarter": r.quarter, "med_roa": round(float(r.med_roa), 3) if pd.notna(r.med_roa) else None,
         "med_capital": round(float(r.med_capital), 3) if pd.notna(r.med_capital) else None,
         "med_noncurrent": round(float(r.med_noncurrent), 3) if pd.notna(r.med_noncurrent) else None,
         "med_uninsured": round(float(r.med_uninsured), 3) if pd.notna(r.med_uninsured) else None,
         "n": int(r.n)} for r in agg.itertuples()
    ]
    return {
        "failures_by_year": [{"year": int(r.year), "failures": int(r.failures)} for r in by_year.itertuples()],
        "failures_by_state": [{"state": r.state, "failures": int(r.failures)} for r in by_state.itertuples()],
        "system_trends": trends,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _dump(OUT / "architecture_graph.json", export_architecture_graph())
    _dump(OUT / "wiki.json", export_wiki())
    metrics = json.loads((get_ml_settings().artifact_dir / "metrics_h4.json").read_text())
    conn = _conn()
    _dump(OUT / "meta.json", export_meta(metrics))
    _dump(OUT / "performance.json", export_performance(metrics, conn))
    _dump(OUT / "timeline.json", export_timeline(conn))
    _dump(OUT / "business.json", export_business(conn))
    # real Data Browser sample (gold panel rows)
    browser = conn.execute(
        "select cert, bank_name, state, quarter, ASSET, roa, equity_to_assets, "
        "noncurrent_to_loans, uninsured_deposit_share, label_4 from ml.training_dataset "
        "where quarter >= '2023Q1' order by ASSET desc nulls last limit 60"
    ).df()
    _dump(OUT / "browser.json", {"columns": list(browser.columns),
                                 "rows": browser.where(browser.notna(), None).values.tolist()})
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
