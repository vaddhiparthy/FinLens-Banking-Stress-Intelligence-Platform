"""Serving-path tests. Skipped in CI when no trained artifact is present
(artifacts are gitignored; training runs offline/locally)."""

from __future__ import annotations

import importlib.util

import pytest

from finlens_ml.config import get_ml_settings

_ARTIFACT = get_ml_settings().artifact_dir / "calibrated_h4.skops"
_BOOSTER = get_ml_settings().artifact_dir / "booster_h4.txt"
_HAS_MODEL = _ARTIFACT.exists() or _BOOSTER.exists()
# The serving path imports skops; skip when the ML extra isn't installed (e.g. the
# light `--all-groups` CI jobs) instead of erroring on import.
_HAS_SKOPS = importlib.util.find_spec("skops") is not None

_needs_model = pytest.mark.skipif(
    not (_HAS_MODEL and _HAS_SKOPS),
    reason="no trained model artifact present, or skops (ml extra) not installed",
)


@_needs_model
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


@_needs_model
def test_decision_threshold() -> None:
    from finlens_ml.predict import decision

    d = decision(0.99)
    assert d["flagged"] is True
    assert decision(0.0)["flagged"] is False


def test_skops_load_rejects_unexpected_type(tmp_path) -> None:
    """The trust boundary is real: a serialized object whose type is NOT on the
    allow-list must be refused, not silently trusted (the pickle-equivalent bug)."""
    import pytest

    sio = pytest.importorskip("skops.io")
    from collections import Counter

    from finlens_ml.predict import _skops_load

    bad = tmp_path / "tampered.skops"
    sio.dump(Counter({"a": 1}), bad)  # collections.Counter is not on the allow-list
    with pytest.raises(ValueError, match="unexpected serialized types"):
        _skops_load(bad)
