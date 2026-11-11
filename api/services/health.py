from __future__ import annotations

from finlens.config import get_settings
from finlens.pipeline_status import pipeline_status_rows
from finlens.platform_probes import probe_postgres_sync
from finlens.state import load_state
from finlens.warehouse import stress_pulse_source_mode, local_duckdb_path


def serving_warehouse_ready() -> bool:
    import duckdb

    path = local_duckdb_path()
    if not path.is_file():
        return False
    try:
        with duckdb.connect(str(path), read_only=True) as connection:
            for table in ("marts.fct_bank_failures", "marts.fct_financial_metrics"):
                connection.execute("SELECT 1 FROM " + table + " LIMIT 0")
        return True
    except Exception:
        return False


def health_payload() -> dict:
    settings = get_settings()
    connector_report = load_state("connector_report", default={}, quarantine_corrupt=False)
    connectors = connector_report.get("sources", []) if isinstance(connector_report, dict) else []
    pipeline = pipeline_status_rows(quarantine_corrupt=False)
    pipeline_states = {row["status"] for row in pipeline}
    healthy_states = {"Success", "Deferred", "Not Activated"}
    overall = "ok" if pipeline and pipeline_states.issubset(healthy_states) and (settings.finlens_data_mode == "demo" or serving_warehouse_ready()) else "degraded"
    return {
        "status": overall,
        "environment": settings.fastapi_env,
        "data_mode": settings.finlens_data_mode,
        "stress_pulse_mode": stress_pulse_source_mode(),
        "postgres_sync": probe_postgres_sync(),
        "connectors": connectors,
        "pipeline": pipeline,
    }
