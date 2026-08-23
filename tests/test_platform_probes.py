from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import requests

from finlens import platform_probes


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def test_airflow_probe_uses_v3_health_and_requires_all_components(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_get(url: str, timeout: int) -> _Response:
        observed.update(url=url, timeout=timeout)
        return _Response(
            {
                "metadatabase": {"status": "healthy"},
                "scheduler": {"status": "healthy"},
                "dag_processor": {"status": "healthy"},
            }
        )

    monkeypatch.setattr(
        platform_probes,
        "get_settings",
        lambda: SimpleNamespace(airflow_api_base_url="http://airflow-web:8080"),
    )
    monkeypatch.setattr(requests, "get", fake_get)

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        dags = root / "airflow" / "dags"
        dags.mkdir(parents=True)
        (dags / "dag_test.py").write_text("# fixture\n", encoding="utf-8")
        monkeypatch.setattr(platform_probes, "ROOT_DIR", root)
        result = platform_probes.probe_airflow_project()

    assert observed == {
        "url": "http://airflow-web:8080/api/v2/monitor/health",
        "timeout": 8,
    }, observed
    assert result["status"] == "Ready"
    assert result["runtime_status"] == "Ready"
    assert result["metadatabase"] == "healthy"
    assert result["scheduler"] == "healthy"
    assert result["dag_processor"] == "healthy"


def test_airflow_probe_fails_when_dag_processor_is_not_healthy(monkeypatch) -> None:
    monkeypatch.setattr(
        platform_probes,
        "get_settings",
        lambda: SimpleNamespace(airflow_api_base_url="http://airflow-web:8080"),
    )
    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: _Response(
            {
                "metadatabase": {"status": "healthy"},
                "scheduler": {"status": "healthy"},
                "dag_processor": {"status": "unhealthy"},
            }
        ),
    )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        dags = root / "airflow" / "dags"
        dags.mkdir(parents=True)
        (dags / "dag_test.py").write_text("# fixture\n", encoding="utf-8")
        monkeypatch.setattr(platform_probes, "ROOT_DIR", root)
        result = platform_probes.probe_airflow_project()

    assert result["status"] == "Failed"
    assert result["runtime_status"] == "Unhealthy"
    assert result["dag_processor"] == "unhealthy"
