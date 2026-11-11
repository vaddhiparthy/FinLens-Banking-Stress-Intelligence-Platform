from __future__ import annotations

import requests

from finlens.config import get_settings
from finlens.telemetry import append_telemetry_event, telemetry_summary


def verify_turnstile(token: str | None) -> bool:
    settings = get_settings()
    if not settings.cloudflare_turnstile_secret_key:
        return False
    if not token:
        return False
    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": settings.cloudflare_turnstile_secret_key,
                "response": token,
            },
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return False
    return bool(payload.get("success"))


def record_event(
    *,
    event_type: str,
    page_key: str,
    surface: str,
    session_id: str,
    payload: dict | None = None,
    turnstile_token: str | None = None,
) -> dict:
    if not get_settings().finlens_telemetry_enabled:
        raise ValueError("Telemetry is disabled")
    if not verify_turnstile(turnstile_token):
        raise ValueError("Turnstile verification failed")
    return append_telemetry_event(
        event_type=event_type,
        page_key=page_key,
        surface=surface,
        session_id=session_id,
        payload=payload,
    )


def summary_payload() -> dict:
    return telemetry_summary()
