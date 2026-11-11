"""SHAP explainability tests. Skipped when no trained booster is present."""

from __future__ import annotations

import pytest

from finlens_ml.config import get_ml_settings
from finlens_ml.features import FEATURE_COLUMNS

_BOOSTER = get_ml_settings().artifact_dir / "booster_h4.txt"
_needs_model = pytest.mark.skipif(not _BOOSTER.exists(), reason="no trained booster present")


@_needs_model
def test_global_importance_ranks_all_features() -> None:
    pytest.importorskip("shap")
    from finlens_ml.explain import global_importance

    gi = global_importance(n=300)
    assert set(gi["feature"]) == set(FEATURE_COLUMNS)
    # capital (tier-1) should be among the strongest drivers (domain expectation)
    top5 = list(gi.head(5)["feature"])
    assert any("tier1" in f or "equity" in f or f == "roa" for f in top5)
    # sorted descending
    assert gi["mean_abs_shap"].is_monotonic_decreasing


@_needs_model
def test_local_reasons_directionally_correct() -> None:
    pytest.importorskip("shap")
    from finlens_ml.explain import local_reasons

    distressed = {
        "tier1_rwa_ratio": 3.0,
        "roa": -3.0,
        "equity_to_assets": 1.5,
        "noncurrent_to_loans": 12.0,
    }
    codes = local_reasons(distressed, top_k=6)
    assert len(codes) == 6
    # the dominant driver for a thinly-capitalized bank should increase risk
    drivers = {c.feature: c for c in codes}
    if "tier1_rwa_ratio" in drivers:
        assert drivers["tier1_rwa_ratio"].direction == "increases risk"
