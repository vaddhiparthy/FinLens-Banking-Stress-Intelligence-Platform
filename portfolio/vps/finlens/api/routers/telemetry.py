from fastapi import APIRouter, HTTPException

from api.models.schemas import (
    TelemetryEventRequest,
    TelemetryEventResponse,
    TelemetrySummaryResponse,
)
from api.services.telemetry import record_event, summary_payload

router = APIRouter()


@router.post("/telemetry/events", response_model=TelemetryEventResponse)
def telemetry_event(payload: TelemetryEventRequest) -> TelemetryEventResponse:
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
