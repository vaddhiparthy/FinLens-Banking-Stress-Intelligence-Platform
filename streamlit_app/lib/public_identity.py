from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from urllib.request import Request, urlopen

DEFAULT_PROFILE_URL = "https://vaddhiparthy.com/data/site-content.json"
DEFAULT_DISPLAY_NAME = "Surya Vaddhiparthy"
DEFAULT_PORTFOLIO_URL = "https://vaddhiparthy.com/"
DEFAULT_GITHUB_URL = "https://github.com/vaddhiparthy/"
PROFILE_CACHE_SECONDS = 300


@dataclass(frozen=True)
class PublicIdentity:
    display_name: str
    portfolio_url: str
    github_url: str


_profile_cache: tuple[float, PublicIdentity] | None = None
_profile_cache_lock = Lock()


def _load_public_identity(profile_url: str) -> PublicIdentity:
    request = Request(
        profile_url,
        headers={"Accept": "application/json", "User-Agent": "FinLens/1.0"},
    )
    with urlopen(request, timeout=2) as response:
        payload = json.loads(response.read().decode("utf-8"))
    record = payload.get("identity") or {}
    display_name = str(record.get("display_name") or "").strip()
    if not display_name or len(display_name) > 100 or not re.fullmatch(r"[\w .'-]+", display_name):
        raise ValueError("central public display name is invalid")
    return PublicIdentity(
        display_name=display_name,
        portfolio_url=str(record.get("portfolio_url") or DEFAULT_PORTFOLIO_URL).strip(),
        github_url=str(record.get("github_url") or DEFAULT_GITHUB_URL).strip(),
    )


def public_identity() -> PublicIdentity:
    """Read the portfolio's single public identity record, with a safe local fallback."""
    global _profile_cache
    now = monotonic()
    if _profile_cache and now < _profile_cache[0]:
        return _profile_cache[1]
    with _profile_cache_lock:
        now = monotonic()
        if _profile_cache and now < _profile_cache[0]:
            return _profile_cache[1]
        profile_url = os.getenv("PORTFOLIO_PROFILE_URL", DEFAULT_PROFILE_URL).strip()
        try:
            identity = _load_public_identity(profile_url)
        except Exception:
            identity = PublicIdentity(
                DEFAULT_DISPLAY_NAME,
                DEFAULT_PORTFOLIO_URL,
                DEFAULT_GITHUB_URL,
            )
        _profile_cache = (now + PROFILE_CACHE_SECONDS, identity)
        return identity


def apply_public_identity(text: str) -> str:
    identity = public_identity()
    for legacy_name in (
        "Surya Vaddhiparthy",
        "Surya Vaddhiparthy",
        "Surya Vaddhiparthy",
        "Surya Vaddhiparthy",
    ):
        text = text.replace(legacy_name, identity.display_name)
    for origin in ("https://vaddhiparthy.com", "https://vaddhiparthy.com"):
        text = text.replace(origin, identity.portfolio_url.rstrip("/"))
    for profile in ("https://github.com/vaddhiparthy", "https://github.com/vaddhiparthy"):
        text = text.replace(profile, identity.github_url.rstrip("/"))
    return text
