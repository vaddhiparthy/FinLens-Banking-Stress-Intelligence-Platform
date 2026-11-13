from __future__ import annotations

from contextlib import contextmanager
import json
import os

from pathlib import Path
from typing import Any

from finlens.paths import STATE_DIR
from finlens.storage import read_json, write_json


def state_file(name: str) -> Path:
    return STATE_DIR / f"{name}.json"


def load_state(name: str, *, default: Any, quarantine_corrupt: bool = False) -> Any:
    return read_json(state_file(name), default=default, quarantine_corrupt=quarantine_corrupt)


def save_state(name: str, payload: Any) -> Path:
    return write_json(state_file(name), payload)


@contextmanager
def state_update_lock():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        import msvcrt
        with (STATE_DIR / ".state-update.lock").open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        descriptor = os.open(STATE_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)


def load_state_for_update(name: str, *, default: Any) -> Any:
    try:
        return json.loads(state_file(name).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
