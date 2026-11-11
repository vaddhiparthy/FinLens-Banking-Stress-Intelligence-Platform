from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
import stat
import tempfile
from uuid import uuid4

from finlens.config import get_settings
from finlens.state import state_file


MAX_TELEMETRY_EVENTS = 10_000


def load_telemetry_events() -> list[dict]:
    try:
        payload = json.loads(state_file("telemetry_events").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = []
    return payload if isinstance(payload, list) else []


@contextmanager
def _telemetry_update_lock():
    path = state_file("telemetry_events")
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import msvcrt
        with path.with_name(".telemetry-events.lock").open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield path
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield path
        finally:
            os.close(descriptor)


def _write_telemetry_events(path, events):
    mode = 0o660
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Telemetry storage must be a regular file")
        mode = stat.S_IMODE(info.st_mode)
    except FileNotFoundError:
        pass
    descriptor, temporary = tempfile.mkstemp(prefix=".telemetry-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            if hasattr(os, "fchmod"):
                os.fchmod(stream.fileno(), mode)
            else:
                os.chmod(temporary, mode)
            json.dump(events, stream, indent=2, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


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
    event = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "page_key": page_key,
        "surface": surface,
        "session_id": session_id,
        "payload": payload or {},
        "captured_at": datetime.now(UTC).isoformat(),
    }
    with _telemetry_update_lock() as path:
        try:
            events = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            events = []
        if not isinstance(events, list):
            raise ValueError("Telemetry history must be a list")
        events.append(event)
        _write_telemetry_events(path, events[-MAX_TELEMETRY_EVENTS:])
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
