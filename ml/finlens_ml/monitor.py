"""Drift monitoring with Evidently (0.7.x programmatic Report API).

Computes data drift (feature distribution shift) and prediction drift (model-score
distribution shift) between a reference window and a current window of the bank-quarter
panel. Prediction drift is the earliest warning signal because true failure labels
arrive late.

Evidently pins plotly<6 while the app needs plotly>=6. We use ONLY the programmatic
Report API and serialize results to a dict/JSON — no Evidently plotly rendering — so
the two coexist. If a future Evidently render path is needed, run it in an isolated
process. $0: no billable imports.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from finlens_ml.config import get_ml_settings
from finlens_ml.features import FEATURE_COLUMNS

_MAX_ROWS = 20000  # bound memory


def _load_window(where: str, limit: int = _MAX_ROWS) -> pd.DataFrame:
    import duckdb

    settings = get_ml_settings()
    with duckdb.connect(str(settings.duckdb_path), read_only=True) as conn:
        return conn.execute(
            f"select * from ml.training_dataset where {where} "
            f"using sample {limit} rows (reservoir, 42)"
        ).df()


def build_reference_current(
    split_year: int = 2019,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reference = pre-split-year (training regime); current = split-year onward."""
    ref = _load_window(f"obs_qord < {split_year * 4}")
    cur = _load_window(f"obs_qord >= {split_year * 4}")
    return ref, cur


def _attach_scores(df: pd.DataFrame) -> pd.DataFrame:
    from finlens_ml.predict import score_frame

    out = df.copy()
    try:
        out["distress_score"] = score_frame(out, 4)
    except Exception:
        out["distress_score"] = np.nan
    return out


def drift_report(reference: pd.DataFrame | None = None,
                 current: pd.DataFrame | None = None) -> dict:
    """Run Evidently data + prediction drift; return a JSON-able summary dict."""
    from evidently import Report
    from evidently.presets import DataDriftPreset

    if reference is None or current is None:
        reference, current = build_reference_current()
    cols = [c for c in FEATURE_COLUMNS if c in reference.columns]
    ref = _attach_scores(reference[cols + [c for c in ("cert",) if c in reference.columns]])
    cur = _attach_scores(current[cols + [c for c in ("cert",) if c in current.columns]])
    analysis_cols = cols + ["distress_score"]

    report = Report([DataDriftPreset()])
    snapshot = report.run(current_data=cur[analysis_cols], reference_data=ref[analysis_cols])
    result = snapshot.dict() if hasattr(snapshot, "dict") else snapshot.as_dict()
    return _summarize(result, analysis_cols)


def _summarize(result: dict, analysis_cols: list[str]) -> dict:
    """Extract a compact, JSON-safe drift summary from the Evidently 0.7.x result."""
    metrics = result.get("metrics", [])
    n_drifted = share = None
    prediction_drift = None
    per_column: dict[str, float] = {}
    for m in metrics:
        name = m.get("metric_name", "")
        val = m.get("value", {})
        if name.startswith("DriftedColumnsCount") and isinstance(val, dict):
            n_drifted = val.get("count")
            share = val.get("share")
        elif name.startswith("ValueDrift(column="):
            col = m.get("config", {}).get("column")
            if isinstance(val, (int, float)):
                per_column[col] = float(val)
                if col == "distress_score":
                    prediction_drift = float(val)
    # the most-drifted features (excluding the prediction score)
    top = sorted(
        ((c, v) for c, v in per_column.items() if c != "distress_score"),
        key=lambda kv: kv[1], reverse=True,
    )[:5]
    return {
        "n_features_analyzed": len(analysis_cols),
        "n_drifted_columns": int(n_drifted) if n_drifted is not None else None,
        "share_of_drifted_columns": share,
        "prediction_drift_score": prediction_drift,
        "prediction_drift_included": "distress_score" in analysis_cols,
        "top_drifted_features": [{"feature": c, "drift": round(v, 4)} for c, v in top],
    }


def main() -> None:
    summary = drift_report()
    out = get_ml_settings().artifact_dir / "drift_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
