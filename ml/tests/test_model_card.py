"""Model-card / governance generation tests. Skipped when no artifact/dataset."""

from __future__ import annotations

import pytest

from finlens_ml.config import get_ml_settings

_settings = get_ml_settings()
_HAS = (_settings.artifact_dir / "metrics_h4.json").exists() and _settings.duckdb_path.exists()
_needs = pytest.mark.skipif(not _HAS, reason="no artifact/dataset present")


@_needs
def test_cross_segment_equity_has_segments() -> None:
    pytest.importorskip("shap")
    from finlens_ml.model_card import cross_segment_equity

    seg = cross_segment_equity()
    assert "region" in seg
    # at least one segment table has rows with computed metrics
    assert len(seg["region"]) >= 1
    assert {"segment", "n", "positives", "roc_auc"}.issubset(seg["region"].columns)


@_needs
def test_generate_model_card_writes_real_metrics() -> None:
    pytest.importorskip("shap")
    from finlens_ml.model_card import generate_model_card, generate_validation_report

    card = generate_model_card()
    report = generate_validation_report()
    text = " ".join(card.read_text(encoding="utf-8").lower().split())  # normalize wrapping
    assert "pr-auc" in text and "no protected class" in text
    # SR 11-7 is the real, established model-risk guidance; the card must not invent a
    # fictitious successor (e.g. "SR 26-2"), which a validator would catch instantly.
    assert "sr 11-7" in text
    assert "sr 26-2" not in text
    assert "conceptual soundness" in report.read_text(encoding="utf-8").lower()


def test_fairness_framing_is_honest() -> None:
    """The model card must NOT claim protected-class fairness for an institution model."""
    settings = get_ml_settings()
    card = settings.repo_root / "docs" / "ml" / "MODEL_CARD.md"
    if not card.exists():
        pytest.skip("model card not generated")
    text = " ".join(card.read_text(encoding="utf-8").lower().split())  # normalize wrapping
    assert "no protected class" in text
    # must explicitly state protected-class fairness metrics do NOT apply
    assert "demographic parity / disparate impact / the four-fifths rule do not apply" in text
