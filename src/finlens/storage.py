from __future__ import annotations

import json
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, payload: str) -> Path:
    ensure_parent(path)
    path.write_text(payload, encoding="utf-8")
    return path


def write_bytes(path: Path, payload: bytes) -> Path:
    ensure_parent(path)
    path.write_bytes(payload)
    return path
