from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    environment: str
    data_mode: str
    stress_pulse_mode: str
    postgres_sync: dict = Field(default_factory=dict)
    connectors: list[dict] = Field(default_factory=list)
    pipeline: list[dict] = Field(default_factory=list)


class TelemetryEventRequest(BaseModel):
    event_type: str
    page_key: str
    surface: str
    session_id: str
    payload: dict = Field(default_factory=dict)
    turnstile_token: str | None = None


class TelemetryEventResponse(BaseModel):
    accepted: bool
    event_id: str | None = None


class TelemetrySummaryResponse(BaseModel):
    event_count: int
    unique_sessions: int
    page_views: int
    page_view_breakdown: dict[str, int] = Field(default_factory=dict)
