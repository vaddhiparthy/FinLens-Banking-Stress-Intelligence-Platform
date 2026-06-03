"""Tests for the inference audit log."""

from __future__ import annotations

import json


def test_log_inference_appends_record(tmp_path, monkeypatch) -> None:
    import finlens_ml.audit as audit

    log = tmp_path / "inference_log.jsonl"
    monkeypatch.setattr(audit, "_log_path", lambda: log)
    rid = audit.log_inference(
        features={"roa": -3.0, "tier1_rwa_ratio": 3.0},
        probability=0.42, flagged=True, model_version="test-v1", horizon_q=4,
        reasons=[{"feature": "tier1_rwa_ratio", "shap": 4.5}], source="predict",
    )
    assert len(rid) == 16
    rec = json.loads(log.read_text().strip())
    assert rec["request_id"] == rid
    assert rec["model_version"] == "test-v1"
    assert rec["probability"] == 0.42 and rec["flagged"] is True
    assert rec["features"]["roa"] == -3.0
    assert rec["reasons"][0]["feature"] == "tier1_rwa_ratio"
    assert "ts" in rec


def test_read_log_roundtrip(tmp_path, monkeypatch) -> None:
    import finlens_ml.audit as audit

    log = tmp_path / "inference_log.jsonl"
    monkeypatch.setattr(audit, "_log_path", lambda: log)
    for i in range(3):
        audit.log_inference(features={"roa": float(i)}, probability=0.1 * i, flagged=False,
                            model_version="v", horizon_q=4)
    rows = audit.read_log()
    assert len(rows) == 3
    assert [r["features"]["roa"] for r in rows] == [0.0, 1.0, 2.0]
