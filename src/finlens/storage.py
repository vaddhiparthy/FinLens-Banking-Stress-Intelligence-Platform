from __future__ import annotations

import json
import os
import time
import stat
from uuid import uuid4
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> Path:
    ensure_parent(path)
    data = json.dumps(payload, indent=2, sort_keys=True)
    previous_mode = None
    try:
        previous = path.lstat()
        if stat.S_ISREG(previous.st_mode):
            previous_mode = stat.S_IMODE(previous.st_mode)
    except FileNotFoundError:
        pass
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            if previous_mode is not None:
                os.chmod(temporary, previous_mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(5):
            try:
                os.replace(temporary, path)
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
        if os.name != "nt":
            descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return path
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass



def read_json(path: Path, default: Any, *, quarantine_corrupt: bool = False) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError, OSError):
        # Preserve damaged data during reads; quarantine requires an explicit request.
        if quarantine_corrupt:
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
