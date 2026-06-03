"""FastAPI serving for the bank-distress model.

Production-grade patterns (architecture §6): model loaded ONCE at startup via a
lifespan handler into app state (warm, not per-request); Pydantic v2 request/response
with validation; /predict (single) + /predict/batch (vectorized) + /health + /ready
(readiness fails if the model is not loaded); calibrated probability + decision flag +
model version + SHAP reason codes in the response. OMP_NUM_THREADS pinned to 1 for
stable, bounded CPU use on the VPS.

$0: no billable imports.
"""

from __future__ import annotations

import hashlib
import os
from contextlib import asynccontextmanager

os.environ.setdefault("OMP_NUM_THREADS", "1")  # bounded, thread-safe inference

import pandas as pd  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402

from finlens_ml.config import get_ml_settings  # noqa: E402
from finlens_ml.features import FEATURE_COLUMNS  # noqa: E402

_FEATURE_SET = set(FEATURE_COLUMNS)


def _validate_feature_map(v: dict[str, float | None]) -> dict[str, float | None]:
    """Shared validation contract for single and batch: reject unknown keys and
    non-finite/absurd values; null is allowed (missing feature -> NaN)."""
    unknown = set(v) - _FEATURE_SET
    if unknown:
        raise ValueError(f"unknown feature(s): {sorted(unknown)}")
    for key, val in v.items():
        if val is not None and (val != val or abs(val) > 1e12):  # NaN/inf or absurd
            raise ValueError(f"feature '{key}' must be a finite number or null")
    return v


def _model_version(horizon_q: int = 4) -> str:
    path = get_ml_settings().artifact_dir / f"calibrated_h{horizon_q}.skops"
    if not path.exists():
        path = get_ml_settings().artifact_dir / f"booster_h{horizon_q}.txt"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else "none"
    return f"finlens-distress-h{horizon_q}-{digest}"


class BankFeatures(BaseModel):
    """Sparse CAMELS feature map. Unknown keys rejected; values must be finite or null
    (missing features are allowed — LightGBM handles NaN natively)."""

    features: dict[str, float | None] = Field(default_factory=dict)

    @field_validator("features")
    @classmethod
    def _check(cls, v: dict[str, float | None]) -> dict[str, float | None]:
        return _validate_feature_map(v)


class BatchRequest(BaseModel):
    records: list[dict[str, float | None]] = Field(min_length=1, max_length=5000)

    @field_validator("records")
    @classmethod
    def _check_records(cls, v: list[dict[str, float | None]]) -> list[dict[str, float | None]]:
        for rec in v:
            _validate_feature_map(rec)  # same contract as the single endpoint
        return v


class ReasonOut(BaseModel):
    feature: str
    value: float | None
    shap: float
    direction: str


class PredictResponse(BaseModel):
    probability: float
    flagged: bool
    threshold: float
    horizon_quarters: int
    model_version: str
    reasons: list[ReasonOut] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    from finlens_ml.predict import load_model

    settings = get_ml_settings()
    try:
        app.state.model = load_model(4)
        app.state.version = _model_version(4)
        app.state.threshold = settings.flag_threshold
        app.state.ready = True
    except Exception as exc:  # serve /health but fail /ready if the model is absent
        app.state.model = None
        app.state.ready = False
        app.state.load_error = str(exc)
    yield


app = FastAPI(title="FinLens Bank-Distress API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    if not getattr(app.state, "ready", False):
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ready", "model_version": app.state.version}


def _score_one(features: dict) -> PredictResponse:
    from finlens_ml.explain import local_reasons
    from finlens_ml.predict import decision, score_frame

    row = {c: features.get(c) for c in FEATURE_COLUMNS}
    df = pd.DataFrame([row], columns=FEATURE_COLUMNS).astype(float)
    prob = float(score_frame(df, 4)[0])
    dec = decision(prob)
    reasons = [
        ReasonOut(feature=r.feature, value=(None if r.value != r.value else r.value),
                  shap=r.shap, direction=r.direction)
        for r in local_reasons(features, top_k=6)
    ]
    return PredictResponse(
        probability=prob, flagged=dec["flagged"], threshold=dec["threshold"],
        horizon_quarters=4, model_version=app.state.version, reasons=reasons,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(req: BankFeatures) -> PredictResponse:
    if not getattr(app.state, "ready", False):
        raise HTTPException(status_code=503, detail="model not loaded")
    return _score_one(req.features)


@app.post("/predict/batch")
def predict_batch(req: BatchRequest) -> dict:
    if not getattr(app.state, "ready", False):
        raise HTTPException(status_code=503, detail="model not loaded")
    from finlens_ml.predict import decision, score_frame

    unknown = set().union(*[set(r) for r in req.records]) - _FEATURE_SET
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown feature(s): {sorted(unknown)}")
    df = pd.DataFrame(
        [{c: rec.get(c) for c in FEATURE_COLUMNS} for rec in req.records],
        columns=FEATURE_COLUMNS,
    ).astype(float)
    probs = score_frame(df, 4)  # vectorized, single call
    out = [
        {"probability": float(p), **{k: v for k, v in decision(float(p)).items() if k != "probability"}}
        for p in probs
    ]
    return {"model_version": app.state.version, "horizon_quarters": 4, "predictions": out}
