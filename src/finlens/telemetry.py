from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from finlens.config import get_settings
from finlens.state import load_state, save_state


def load_telemetry_events() -> list[dict]:
    payload = load_state("telemetry_events", default=[])
    return payload if isinstance(payload, list) else []


def append_telemetry_event(
    *,
    event_type: str,
    page_key: str,
    surface: str,
    session_id: str,
    payload: dict | None = None,
) -> dict:
    settings = get_settings()
    if not settings.finlens_telemetry_enabled:
        return {}
    events = load_telemetry_events()
    event = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "page_key": page_key,
        "surface": surface,
        "session_id": session_id,
        "payload": payload or {},
        "captured_at": datetime.now(UTC).isoformat(),
    }
    events.append(event)
    save_state("telemetry_events", events)
    return event


def telemetry_summary() -> dict:
    events = load_telemetry_events()
    sessions = {item["session_id"] for item in events if item.get("session_id")}
    page_views = [item for item in events if item.get("event_type") == "page_view"]
    per_page: dict[str, int] = {}
    for item in page_views:
        page = item.get("page_key", "unknown")
        per_page[page] = per_page.get(page, 0) + 1
    return {
        "event_count": len(events),
        "unique_sessions": len(sessions),
        "page_views": len(page_views),
        "page_view_breakdown": per_page,
    }
