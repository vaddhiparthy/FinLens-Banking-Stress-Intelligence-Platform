"""Load the trained model and score banks (real, batch, or hypothetical).

Used by the FastAPI serving layer (P5) and the interactive scenario tab (P6). Loads
the calibrated model via skops (safe deserialization — never raw pickle). Falls back
to the native LightGBM booster (uncalibrated) if the skops artifact is unavailable.

$0: no billable imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from finlens_ml.config import get_ml_settings
from finlens_ml.features import FEATURE_COLUMNS


@dataclass(frozen=True)
class LoadedModel:
    predict_proba: object  # callable: (DataFrame[FEATURE_COLUMNS]) -> prob array
    horizon_q: int
    calibrated: bool
    source: str


def _skops_load(path: Path):
    import skops.io as sio

    untrusted = sio.get_untrusted_types(file=path)
    # our own artifact: trust sklearn/lightgbm/numpy types we serialized
    return sio.load(path, trusted=untrusted)


@lru_cache(maxsize=4)
def load_model(horizon_q: int = 4) -> LoadedModel:
    settings = get_ml_settings()
    skops_path = settings.artifact_dir / f"calibrated_h{horizon_q}.skops"
    booster_path = settings.artifact_dir / f"booster_h{horizon_q}.txt"
    if skops_path.exists():
        model = _skops_load(skops_path)
        return LoadedModel(
            predict_proba=lambda df: model.predict_proba(df[FEATURE_COLUMNS].astype(float))[:, 1],
            horizon_q=horizon_q,
            calibrated=True,
            source=str(skops_path),
        )
    if booster_path.exists():
        import lightgbm as lgb

        booster = lgb.Booster(model_file=str(booster_path))
        return LoadedModel(
            predict_proba=lambda df: booster.predict(df[FEATURE_COLUMNS].astype(float)),
            horizon_q=horizon_q,
            calibrated=False,
            source=str(booster_path),
        )
    raise FileNotFoundError(
        f"No model artifact for horizon {horizon_q} in {settings.artifact_dir}. Run train.py first."
    )


def score_frame(df: pd.DataFrame, horizon_q: int = 4) -> np.ndarray:
    """Probability of distress within the horizon for each row (must have FEATURE_COLUMNS)."""
    model = load_model(horizon_q)
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing required features: {missing}")
    return np.asarray(model.predict_proba(df))


def score_record(features: dict, horizon_q: int = 4) -> float:
    """Score a single bank (real or hypothetical) from a feature dict.
    Missing features are filled with NaN (LightGBM handles natively)."""
    row = {c: float(features.get(c, np.nan)) if features.get(c) is not None else np.nan
           for c in FEATURE_COLUMNS}
    df = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    return float(score_frame(df, horizon_q)[0])


def decision(prob: float) -> dict:
    """Map a calibrated probability to a flag using the configured threshold."""
    settings = get_ml_settings()
    return {
        "probability": prob,
        "flagged": bool(prob >= settings.flag_threshold),
        "threshold": settings.flag_threshold,
    }
