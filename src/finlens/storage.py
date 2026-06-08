from __future__ import annotations

import json
import os
import time
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
    # os.replace is atomic on POSIX, but on Windows it raises PermissionError
    # (WinError 5) when the destination is momentarily held open by a concurrent
    # reader, an antivirus scanner, or another app thread loading the same file.
    # That is transient, so retry a few times with a short backoff before giving up.
    last_err: OSError | None = None
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return path
        except OSError as err:  # PermissionError is a subclass of OSError
            last_err = err
            time.sleep(0.05 * (attempt + 1))
    # Final fallback: a best-effort non-atomic overwrite so the write still lands.
    try:
        path.write_text(data, encoding="utf-8")
        return path
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
        if last_err is not None and not path.exists():
            raise last_err


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
