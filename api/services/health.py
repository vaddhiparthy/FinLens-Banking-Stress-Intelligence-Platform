from __future__ import annotations

from finlens.config import get_settings
from finlens.pipeline_status import pipeline_status_rows
from finlens.state import load_state
from finlens.warehouse import stress_pulse_source_mode


def health_payload() -> dict:
    settings = get_settings()
    connector_report = load_state("connector_report", default={})
    connectors = connector_report.get("sources", []) if isinstance(connector_report, dict) else []
    pipeline = pipeline_status_rows()
    pipeline_states = {row["status"] for row in pipeline}
    healthy_states = {"Success", "Missing Data"}
    overall = "ok" if pipeline and pipeline_states.issubset(healthy_states) else "degraded"
    return {
        "status": overall,
        "environment": settings.fastapi_env,
        "data_mode": settings.finlens_data_mode,
        "stress_pulse_mode": stress_pulse_source_mode(),
        "connectors": connectors,
        "pipeline": pipeline,
    }
