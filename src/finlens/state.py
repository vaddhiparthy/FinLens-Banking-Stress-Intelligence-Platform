from __future__ import annotations

from pathlib import Path
from typing import Any

from finlens.paths import STATE_DIR
from finlens.storage import read_json, write_json


def state_file(name: str) -> Path:
    return STATE_DIR / f"{name}.json"


def load_state(name: str, *, default: Any) -> Any:
    return read_json(state_file(name), default=default)


def save_state(name: str, payload: Any) -> Path:
    return write_json(state_file(name), payload)
