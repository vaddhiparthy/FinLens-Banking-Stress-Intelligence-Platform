from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from finlens.state import load_state, save_state

FLOW_LABELS = {
    "fdic": ("FDIC -> Bronze", "FDIC BankFind"),
    "qbp": ("QBP -> Bronze", "FDIC QBP"),
    "fred": ("FRED -> Bronze", "FRED"),
    "nic": ("NIC -> Bronze", "NIC"),
    "bronze_to_silver": ("Bronze -> Silver", "Normalization"),
    "silver_to_gold": ("Silver -> Gold", "Gold modeling"),
    "gold_to_dashboards": ("Gold -> Dashboards", "Serving"),
}

DEFERRED_FLOWS = {
    "qbp": {
        "status": "Not Activated",
        "last_run": "Source contract inactive",
        "rows": "—",
        "note": "No FDIC_QBP_SOURCE_URL is configured; reconciliation is disabled, not faked",
    },
    "nic": {
        "status": "Not Activated",
        "last_run": "Source contract inactive",
        "rows": "—",
        "note": (
            "No NIC_CURRENT_PARENT_SOURCE_URL is configured; "
            "current-parent lineage is inactive"
        ),
    },
}

FLOW_ORDER = [
    "fdic",
    "qbp",
    "fred",
    "nic",
    "bronze_to_silver",
    "silver_to_gold",
    "gold_to_dashboards",
]


def load_pipeline_status() -> dict[str, dict[str, Any]]:
    payload = load_state("pipeline_status", default={})
    return payload if isinstance(payload, dict) else {}


def save_pipeline_status(statuses: dict[str, dict[str, Any]]) -> None:
    save_state("pipeline_status", statuses)


def update_flow_status(flow_key: str, **fields: Any) -> None:
    statuses = load_pipeline_status()
    current = statuses.get(flow_key, {})
    current.update(fields)
    current.setdefault("updated_at", datetime.now(UTC).isoformat())
    statuses[flow_key] = current
    save_pipeline_status(statuses)


def pipeline_status_rows() -> list[dict[str, Any]]:
    statuses = load_pipeline_status()
    rows: list[dict[str, Any]] = []
    for index, flow_key in enumerate(FLOW_ORDER, start=1):
        label, source = FLOW_LABELS[flow_key]
        current = statuses.get(flow_key, DEFERRED_FLOWS.get(flow_key, {}))
        rows.append(
            {
                "flow_no": index,
                "flow_name": label,
                "source": source,
                "status": current.get("status", "Missing Data"),
                "last_run": current.get("last_run", "—"),
                "rows": current.get("rows", "—"),
                "note": current.get("note", "No run recorded yet"),
            }
        )
    return rows
