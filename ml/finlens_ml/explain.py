"""SHAP explainability for the bank-distress model (global + local reason codes).

Uses TreeExplainer on the native LightGBM booster (the object whose ranking drives
the decision). For trees, the path-dependent method needs no background dataset and
is memory-frugal; we still bound the number of rows explained so peak RSS stays
within the VPS budget (architecture §6.1).

Honest limitation (stated in the model card): SHAP assumes feature independence in
probability space, which is violated by correlated CAMELS ratios — so local SHAP is
VALIDATOR/SUPERVISOR-facing transparency, NOT an ECOA/Reg-B adverse-action reason
code (no consumer applicant exists). No billable imports ($0 invariant).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from finlens_ml.config import get_ml_settings
from finlens_ml.features import FEATURE_COLUMNS

_MAX_EXPLAIN_ROWS = 3000  # bound peak memory for SHAP


@dataclass(frozen=True)
class ReasonCode:
    feature: str
    value: float
    shap: float
    direction: str  # "increases risk" / "decreases risk"


def _load_booster():
    import lightgbm as lgb

    path = get_ml_settings().artifact_dir / "booster_h4.txt"
    if not path.exists():
        raise FileNotFoundError(f"booster not found at {path}; run train.py first")
    return lgb.Booster(model_file=str(path))


def _explainer(booster):
    import shap

    return shap.TreeExplainer(booster, feature_perturbation="tree_path_dependent")


def global_importance(sample: pd.DataFrame | None = None, n: int = 2000) -> pd.DataFrame:
    """Mean |SHAP| per feature over a bounded sample -> global ranking."""
    booster = _load_booster()
    expl = _explainer(booster)
    if sample is None:
        sample = _load_sample(n)
    X = sample[FEATURE_COLUMNS].astype(float).head(_MAX_EXPLAIN_ROWS)
    sv = expl.shap_values(X)
    if isinstance(sv, list):  # binary -> list of 2; take positive class
        sv = sv[1] if len(sv) > 1 else sv[0]
    mean_abs = np.abs(sv).mean(axis=0)
    return (
        pd.DataFrame({"feature": FEATURE_COLUMNS, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )


def local_reasons(features: dict, top_k: int = 6) -> list[ReasonCode]:
    """Per-bank reason codes: the top SHAP contributors for one record."""
    booster = _load_booster()
    expl = _explainer(booster)
    row = {c: float(features.get(c)) if features.get(c) is not None else np.nan
           for c in FEATURE_COLUMNS}
    X = pd.DataFrame([row], columns=FEATURE_COLUMNS).astype(float)
    sv = expl.shap_values(X)
    if isinstance(sv, list):
        sv = sv[1] if len(sv) > 1 else sv[0]
    contrib = sv[0]
    order = np.argsort(-np.abs(contrib))[:top_k]
    return [
        ReasonCode(
            feature=FEATURE_COLUMNS[i],
            value=float(X.iloc[0, i]),
            shap=float(contrib[i]),
            direction="increases risk" if contrib[i] > 0 else "decreases risk",
        )
        for i in order
    ]


def _load_sample(n: int) -> pd.DataFrame:
    import duckdb

    settings = get_ml_settings()
    with duckdb.connect(str(settings.duckdb_path), read_only=True) as conn:
        return conn.execute(
            f"select * from ml.training_dataset using sample {int(n)} rows (reservoir, 42)"
        ).df()
