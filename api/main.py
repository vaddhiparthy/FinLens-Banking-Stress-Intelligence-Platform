from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.models.schemas import HealthResponse
from api.routers.failures import router as failures_router
from api.routers.metrics import router as metrics_router
from api.routers.telemetry import router as telemetry_router
from api.services.health import health_payload
from finlens.config import get_settings

settings = get_settings()
app = FastAPI(title="FinLens API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(failures_router)
app.include_router(metrics_router)
app.include_router(telemetry_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(**health_payload())


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(**health_payload())
