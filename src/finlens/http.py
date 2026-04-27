from __future__ import annotations

from typing import Any

import requests

from finlens.ingestion.base import build_retry_policy


def build_session(*, user_agent: str | None = None, timeout: int = 30) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json, text/csv;q=0.9, */*;q=0.8"})

    if user_agent:
        session.headers["User-Agent"] = user_agent

    session.request = _wrap_request(session.request, timeout=timeout)  # type: ignore[method-assign]
    return session


def _wrap_request(request_method, *, timeout: int):
    retryable = build_retry_policy()

    @retryable
    def wrapped(method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", timeout)
        response = request_method(method, url, **kwargs)
        response.raise_for_status()
        return response

    return wrapped


def get_json(session: requests.Session, url: str, **kwargs) -> dict[str, Any]:
    response = session.get(url, **kwargs)
    return response.json()


def get_text(session: requests.Session, url: str, **kwargs) -> str:
    response = session.get(url, **kwargs)
    return response.text


def get_bytes(session: requests.Session, url: str, **kwargs) -> bytes:
    response = session.get(url, **kwargs)
    return response.content
