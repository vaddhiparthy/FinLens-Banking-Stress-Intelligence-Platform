"""Inference audit log — the spine of bank MRM (SR 11-7/26-2) ongoing monitoring.

Every scored request is appended as one JSON line: timestamp, request id, input feature
map, model version, calibrated probability, decision flag, and top reason codes. This is
what makes (a) live prediction-drift, (b) outcomes back-testing, and (c) an auditable
"what did the model say, when, and why" trail possible. Bounded, append-only, local
(JSONL under the artifact dir) — $0, no billable services.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from finlens_ml.config import get_ml_settings

_LOCK = threading.Lock()  # serialize appends across worker threads


def _log_path() -> Path:
    p = get_ml_settings().artifact_dir / "inference_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def log_inference(
    *,
    features: dict,
    probability: float,
    flagged: bool,
    model_version: str,
    horizon_q: int,
    reasons: list | None = None,
    snapshot: str | None = None,
    source: str = "predict",
) -> str:
    """Append one inference record; returns the request id (also useful in the response)."""
    rid = uuid.uuid4().hex[:16]
    record = {
        "request_id": rid,
        "ts": datetime.now(UTC).isoformat(),
        "source": source,
        "model_version": model_version,
        "horizon_q": horizon_q,
        "probability": round(float(probability), 6),
        "flagged": bool(flagged),
        "features": {k: (None if v is None else float(v)) for k, v in features.items()},
        "reasons": [
            {"feature": r["feature"], "shap": round(float(r["shap"]), 5)}
            for r in (reasons or [])
        ],
        "data_snapshot": snapshot,
    }
    line = json.dumps(record, separators=(",", ":"))
    try:
        with _LOCK, _log_path().open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass  # logging must never break serving
    return rid


def read_log(limit: int = 1000) -> list[dict]:
    p = _log_path()
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out
