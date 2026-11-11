from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models.schemas import HealthResponse
from api.routers.failures import router as failures_router
from api.routers.metrics import router as metrics_router
from api.routers.telemetry import router as telemetry_router
from api.services.health import health_payload
from finlens.config import get_settings

settings = get_settings()
MAX_TELEMETRY_REQUEST_BYTES = 32 * 1024
app = FastAPI(
    title="FinLens API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vaddhiparthy.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)


@app.middleware("http")
async def limit_telemetry_request_body(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/telemetry/events":
        raw_length = request.headers.get("content-length")
        try:
            content_length = int(raw_length) if raw_length else None
        except ValueError:
            content_length = None
        if content_length is None:
            return JSONResponse({"detail": "content_length_required"}, status_code=411)
        if content_length > MAX_TELEMETRY_REQUEST_BYTES:
            return JSONResponse({"detail": "request_too_large"}, status_code=413)
    return await call_next(request)

app.include_router(failures_router)
app.include_router(metrics_router)
app.include_router(telemetry_router)


@app.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    payload = health_payload()
    response.status_code = 200 if payload["status"] == "ok" else 503
    return HealthResponse(**payload)


@app.get("/healthz", response_model=HealthResponse)
def healthz(response: Response) -> HealthResponse:
    payload = health_payload()
    response.status_code = 200 if payload["status"] == "ok" else 503
    return HealthResponse(**payload)
