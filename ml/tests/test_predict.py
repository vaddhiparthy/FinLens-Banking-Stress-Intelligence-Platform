"""Serving-path tests. Skipped in CI when no trained artifact is present
(artifacts are gitignored; training runs offline/locally)."""

from __future__ import annotations

import pytest

from finlens_ml.config import get_ml_settings

_ARTIFACT = get_ml_settings().artifact_dir / "calibrated_h4.skops"
_BOOSTER = get_ml_settings().artifact_dir / "booster_h4.txt"
_HAS_MODEL = _ARTIFACT.exists() or _BOOSTER.exists()

pytestmark = pytest.mark.skipif(not _HAS_MODEL, reason="no trained model artifact present")


def test_distressed_scores_higher_than_healthy() -> None:
    from finlens_ml.predict import score_record

    distressed = {
        "equity_to_assets": 1.5,
        "noncurrent_to_loans": 12.0,
        "roa": -3.0,
        "nco_to_loans": 5.0,
        "tier1_rwa_ratio": 3.0,
        "loans_to_deposits": 120.0,
    }
    healthy = {
        "equity_to_assets": 12.0,
        "noncurrent_to_loans": 0.3,
        "roa": 1.4,
        "nco_to_loans": 0.05,
        "tier1_rwa_ratio": 16.0,
        "loans_to_deposits": 70.0,
    }
    p_bad = score_record(distressed)
    p_good = score_record(healthy)
    assert 0.0 <= p_good <= 1.0 and 0.0 <= p_bad <= 1.0
    assert p_bad > p_good


def test_decision_threshold() -> None:
    from finlens_ml.predict import decision

    d = decision(0.99)
    assert d["flagged"] is True
    assert decision(0.0)["flagged"] is False
