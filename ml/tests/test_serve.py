"""FastAPI serving tests via TestClient."""

from __future__ import annotations

import pytest

from finlens_ml.config import get_ml_settings

_HAS = (get_ml_settings().artifact_dir / "calibrated_h4.skops").exists() or (
    get_ml_settings().artifact_dir / "booster_h4.txt"
).exists()
_needs = pytest.mark.skipif(not _HAS, reason="no trained model artifact present")

_DISTRESSED = {"tier1_rwa_ratio": 3.0, "roa": -3.0, "equity_to_assets": 1.5,
               "noncurrent_to_loans": 12.0, "nco_to_loans": 5.0}
_HEALTHY = {"tier1_rwa_ratio": 16.0, "roa": 1.4, "equity_to_assets": 12.0,
            "noncurrent_to_loans": 0.3, "nco_to_loans": 0.05}


def _client():
    pytest.importorskip("shap")
    from fastapi.testclient import TestClient

    from finlens_ml.serve import app

    return TestClient(app)


def test_health_always_ok() -> None:
    with _client() as c:
        assert c.get("/health").json()["status"] == "ok"


@_needs
def test_ready_and_version() -> None:
    with _client() as c:
        r = c.get("/ready")
        assert r.status_code == 200
        assert r.json()["model_version"].startswith("finlens-distress-h4-")


@_needs
def test_predict_distressed_higher_than_healthy() -> None:
    with _client() as c:
        pd_ = c.post("/predict", json={"features": _DISTRESSED}).json()
        pg = c.post("/predict", json={"features": _HEALTHY}).json()
        assert 0.0 <= pg["probability"] <= 1.0
        assert pd_["probability"] > pg["probability"]
        assert pd_["flagged"] is True
        assert len(pd_["reasons"]) > 0


@_needs
def test_batch_equals_single() -> None:
    with _client() as c:
        single = c.post("/predict", json={"features": _DISTRESSED}).json()["probability"]
        batch = c.post("/predict/batch", json={"records": [_DISTRESSED]}).json()
        assert abs(batch["predictions"][0]["probability"] - single) < 1e-9


def test_schema_rejects_unknown_feature() -> None:
    with _client() as c:
        r = c.post("/predict", json={"features": {"not_a_feature": 1.0}})
        assert r.status_code == 422


def test_schema_rejects_non_finite() -> None:
    with _client() as c:
        r = c.post("/predict", json={"features": {"roa": 1e20}})
        assert r.status_code == 422
