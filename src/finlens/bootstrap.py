from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from finlens.config import Settings, get_settings
from finlens.pipeline_status import update_flow_status
from finlens.state import save_state
from ingestion.fdic import ingest_fdic_failed_banks
from ingestion.fred import ingest_fred_series_batch
from ingestion.nic import ingest_nic_current_parent
from ingestion.qbp import ingest_fdic_qbp

Runner = Callable[[], Any]


@dataclass(frozen=True)
class SourceDefinition:
    key: str
    label: str
    required_env: tuple[str, ...]
    cadence: str
    runner: Runner


@dataclass(frozen=True)
class SourceCheck:
    key: str
    label: str
    enabled: bool
    ready: bool
    cadence: str
    required_env: tuple[str, ...]
    missing_env: tuple[str, ...]

    @property
    def status(self) -> str:
        if not self.enabled:
            return "disabled"
        if self.ready:
            return "ready"
        return "missing_connector"


SOURCE_DEFINITIONS: dict[str, SourceDefinition] = {
    "fdic": SourceDefinition(
        key="fdic",
        label="FDIC BankFind failures",
        required_env=(),
        cadence="manual",
        runner=ingest_fdic_failed_banks,
    ),
    "fred": SourceDefinition(
        key="fred",
        label="FRED series batch",
        required_env=("fred_api_key",),
        cadence="daily",
        runner=ingest_fred_series_batch,
    ),
    "qbp": SourceDefinition(
        key="qbp",
        label="FDIC QBP workbook",
        required_env=("fdic_qbp_source_url",),
        cadence="quarterly",
        runner=ingest_fdic_qbp,
    ),
    "nic": SourceDefinition(
        key="nic",
        label="NIC current parent metadata",
        required_env=("nic_current_parent_source_url",),
        cadence="quarterly",
        runner=ingest_nic_current_parent,
    ),
}


def source_checks(
    settings: Settings | None = None,
    *,
    selected_sources: list[str] | None = None,
) -> list[SourceCheck]:
    active_settings = settings or get_settings()
    enabled = set(selected_sources or active_settings.active_source_list)
    checks: list[SourceCheck] = []

    for key, definition in SOURCE_DEFINITIONS.items():
        is_enabled = key in enabled
        missing = tuple(active_settings.missing_or_placeholder(*definition.required_env))
        checks.append(
            SourceCheck(
                key=key,
                label=definition.label,
                enabled=is_enabled,
                ready=(not missing) if is_enabled else False,
                cadence=definition.cadence,
                required_env=definition.required_env,
                missing_env=missing,
            )
        )

    return checks


def save_connector_report(checks: list[SourceCheck]) -> None:
    save_state(
        "connector_report",
        {
            "sources": [
                {
                    "key": check.key,
                    "label": check.label,
                    "enabled": check.enabled,
                    "ready": check.ready,
                    "status": check.status,
                    "cadence": check.cadence,
                    "required_env": list(check.required_env),
                    "missing_env": list(check.missing_env),
                }
                for check in checks
            ]
        },
    )


def validate_active_sources(
    settings: Settings | None = None,
    *,
    selected_sources: list[str] | None = None,
) -> list[SourceCheck]:
    checks = source_checks(settings, selected_sources=selected_sources)
    save_connector_report(checks)
    failures = [check for check in checks if check.enabled and not check.ready]
    if failures:
        lines = ["Connector validation failed for active sources:"]
        for failure in failures:
            missing = ", ".join(failure.missing_env)
            lines.append(f"- {failure.key}: missing {missing}")
        raise ValueError("\n".join(lines))
    return checks


def run_active_sources(
    settings: Settings | None = None,
    *,
    selected_sources: list[str] | None = None,
) -> dict[str, Any]:
    active_settings = settings or get_settings()
    checks = validate_active_sources(active_settings, selected_sources=selected_sources)
    enabled = {check.key for check in checks if check.enabled}
    results: dict[str, Any] = {}

    for key in active_settings.active_source_list if selected_sources is None else selected_sources:
        if key not in enabled:
            continue
        definition = SOURCE_DEFINITIONS[key]
        try:
            result = definition.runner()
        except Exception as exc:
            update_flow_status(
                key,
                status="Failed",
                last_run="Failed",
                rows="0",
                note=str(exc),
            )
            raise
        results[key] = result
        update_flow_status(key, **_status_fields_for_result(key, result))

    return results


def _status_fields_for_result(key: str, result: Any) -> dict[str, str]:
    if key == "fdic":
        return {
            "status": "Success",
            "last_run": "Completed",
            "rows": str(getattr(result, "record_count", "—")),
            "note": "Latest ingest complete",
        }
    if key == "fred":
        updated_count = sum(1 for item in result if getattr(item, "updated", False))
        return {
            "status": "Success",
            "last_run": "Completed",
            "rows": f"{len(result)} series",
            "note": f"{updated_count} series updated",
        }
    if key == "qbp":
        return {
            "status": "Success",
            "last_run": "Completed",
            "rows": f"{getattr(result, 'size_bytes', 0):,} bytes",
            "note": "Quarterly workbook landed",
        }
    if key == "nic":
        return {
            "status": "Success",
            "last_run": "Completed",
            "rows": f"{getattr(result, 'size_bytes', 0):,} bytes",
            "note": "Current parent metadata landed",
        }
    return {
        "status": "Success",
        "last_run": "Completed",
        "rows": "—",
        "note": "Run complete",
    }
