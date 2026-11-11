from collections import deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request

from api.models.schemas import (
    TelemetryEventRequest,
    TelemetryEventResponse,
    TelemetrySummaryResponse,
)
from api.services.telemetry import record_event, summary_payload

router = APIRouter()
_RATE_WINDOW_SECONDS = 600
_RATE_LIMIT = 30
_MAX_BUCKETS = 4096
_RATE_BUCKETS: dict[str, deque[float]] = {}
_RATE_LOCK = Lock()


def _trusted_client_ip(request: Request) -> str:
    # Caddy removes any incoming copy and sets this private proxy header.
    values = request.headers.getlist("x-finlens-client-ip")
    return values[-1].rsplit(",", 1)[-1].strip() if values else "unknown"


def _allow_event(request: Request) -> bool:
    identity = _trusted_client_ip(request)
    now = monotonic()
    cutoff = now - _RATE_WINDOW_SECONDS
    with _RATE_LOCK:
        hits = _RATE_BUCKETS.get(identity)
        if hits is None:
            if len(_RATE_BUCKETS) >= _MAX_BUCKETS:
                expired = [
                    key for key, bucket in _RATE_BUCKETS.items()
                    if not bucket or bucket[-1] <= cutoff
                ]
                for key in expired:
                    del _RATE_BUCKETS[key]
            if len(_RATE_BUCKETS) >= _MAX_BUCKETS:
                return False
            hits = deque()
            _RATE_BUCKETS[identity] = hits
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= _RATE_LIMIT:
            return False
        hits.append(now)
        return True


@router.post("/telemetry/events", response_model=TelemetryEventResponse)
def telemetry_event(request: Request, payload: TelemetryEventRequest) -> TelemetryEventResponse:
    if not _allow_event(request):
        raise HTTPException(status_code=429, detail="try_again_later")
    try:
        event = record_event(
            event_type=payload.event_type,
            page_key=payload.page_key,
            surface=payload.surface,
            session_id=payload.session_id,
            payload=payload.payload,
            turnstile_token=payload.turnstile_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TelemetryEventResponse(accepted=True, event_id=event.get("event_id"))


@router.get("/telemetry/summary", response_model=TelemetrySummaryResponse)
def telemetry_summary() -> TelemetrySummaryResponse:
    return TelemetrySummaryResponse(**summary_payload())
