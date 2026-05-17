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
