"""Seed-bagged calibrated model: average the probabilities of K calibrated LightGBM
models trained on distinct seeds. Bagging reduces estimator variance (the dominant
fold-to-fold noise at this positive count) and had the highest point estimate in the
ablation. Kept as a top-level, skops-serializable class so it can be the served artifact.

predict_proba matches the sklearn 2-column convention so serving / SHAP wrappers that
expect ``predict_proba(X)[:, 1]`` work unchanged. For local SHAP reason codes, expose
the first member's booster via ``representative_booster`` (reason codes are directional
transparency, not a legal adverse-action statement; the bagged probability is the served
number).
"""

from __future__ import annotations

import numpy as np


class BaggedCalibrated:
    def __init__(self, models: list, seeds: list | None = None):
        if not models:
            raise ValueError("BaggedCalibrated needs at least one model")
        self.models = models
        self.seeds = seeds or list(range(len(models)))

    def predict_proba(self, X) -> np.ndarray:
        ps = np.mean([m.predict_proba(X)[:, 1] for m in self.models], axis=0)
        ps = np.clip(ps, 0.0, 1.0)
        return np.column_stack([1.0 - ps, ps])

    def predict(self, X) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    @property
    def classes_(self):
        return getattr(self.models[0], "classes_", np.array([0, 1]))

    @property
    def n_members(self) -> int:
        return len(self.models)


def fit_bagged(X, y, seed: int, k: int, params: dict | None, fixed_rounds: int):
    """Train K seed-bagged calibrated models via the shared _fit_calibrated recipe."""
    from finlens_ml.train import _fit_calibrated

    members = []
    for i in range(k):
        _, cal, *_ = _fit_calibrated(X, y, seed + i, fixed_rounds=fixed_rounds, params=params)
        members.append(cal)
    return BaggedCalibrated(members, seeds=[seed + i for i in range(k)])
