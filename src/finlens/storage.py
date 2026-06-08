from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o777)
    except OSError:
        pass


def write_json(path: Path, payload: Any) -> Path:
    ensure_parent(path)
    # Atomic write: serialize to a unique temp file in the same directory, then
    # os.replace() onto the target. This prevents a concurrent reader (or a
    # racing writer) from ever observing a half-written / truncated file, which
    # was producing "Extra data" JSONDecodeErrors and crashing every page that
    # reads telemetry on load.
    data = json.dumps(payload, indent=2, sort_keys=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{id(payload)}.tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A corrupt or partially-written file must never take down the UI.
        # Preserve the bad payload for inspection, then fall back to default.
        try:
            path.replace(path.with_name(f"{path.name}.corrupt.bak"))
        except OSError:
            pass
        return default


def write_text(path: Path, payload: str) -> Path:
    ensure_parent(path)
    path.write_text(payload, encoding="utf-8")
    return path


def write_bytes(path: Path, payload: bytes) -> Path:
    ensure_parent(path)
    path.write_bytes(payload)
    return path
