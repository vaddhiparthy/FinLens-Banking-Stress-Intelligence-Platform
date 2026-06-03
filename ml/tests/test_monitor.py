"""Drift monitoring tests. Skipped when no dataset/model artifact is present."""

from __future__ import annotations

import pytest

from finlens_ml.config import get_ml_settings

_settings = get_ml_settings()
_HAS = _settings.duckdb_path.exists() and (
    _settings.artifact_dir / "booster_h4.txt"
).exists()
_needs = pytest.mark.skipif(not _HAS, reason="no dataset/model artifact present")


@_needs
def test_drift_report_runs_and_summarizes() -> None:
    pytest.importorskip("evidently")
    from finlens_ml.monitor import build_reference_current, drift_report

    ref, cur = build_reference_current()
    assert len(ref) > 0 and len(cur) > 0
    summary = drift_report(ref, cur)
    assert summary["n_features_analyzed"] >= len(
        [c for c in summary]
    )  # sanity: has features
    assert summary["prediction_drift_included"] is True
    # n_drifted is an int in [0, n_features]
    assert isinstance(summary["n_drifted_columns"], int)
    assert 0 <= summary["n_drifted_columns"] <= summary["n_features_analyzed"]


def test_metric_gate_passes_on_committed_metrics() -> None:
    """The committed real metrics must satisfy the CI gate (LGBM beats logit, ROC<0.98)."""
    import json

    p = _settings.artifact_dir / "metrics_h4.json"
    if not p.exists():
        pytest.skip("metrics not present")
    m = json.loads(p.read_text())
    t = m["oot_test"]
    assert t["calibrated_lgbm"]["pr_auc"] >= t["logit_benchmark"]["pr_auc"]
    assert t["calibrated_lgbm"]["roc_auc"] < 0.98
