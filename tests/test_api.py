from fastapi.testclient import TestClient

from api.main import app


def test_health_endpoint_returns_payload() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "pipeline" in payload


def test_telemetry_summary_endpoint_returns_payload() -> None:
    client = TestClient(app)
    response = client.get("/telemetry/summary")

    assert response.status_code == 200
    payload = response.json()
    assert "event_count" in payload


def test_failures_and_bank_routes_serialize_nonfinite_values_as_null(monkeypatch) -> None:
    import pandas as pd

    from api.services import repository

    frame = pd.DataFrame(
        [
            {
                "bank_id": "nan-bank",
                "closing_date": pd.Timestamp("2026-01-02"),
                "assets_millions": float("nan"),
            },
            {"bank_id": "positive-infinity-bank", "assets_millions": float("inf")},
            {"bank_id": "negative-infinity-bank", "assets_millions": float("-inf")},
        ]
    )
    monkeypatch.setattr(repository, "read_table", lambda _table: frame)

    client = TestClient(app)
    failures_response = client.get("/failures")
    bank_response = client.get("/banks/nan-bank")

    assert failures_response.status_code == 200
    assert [row["assets_millions"] for row in failures_response.json()["items"]] == [
        None,
        None,
        None,
    ]
    assert "NaN" not in failures_response.text
    assert "Infinity" not in failures_response.text
    assert bank_response.status_code == 200
    assert bank_response.json()["assets_millions"] is None
    assert bank_response.json()["closing_date"] == "2026-01-02T00:00:00"
