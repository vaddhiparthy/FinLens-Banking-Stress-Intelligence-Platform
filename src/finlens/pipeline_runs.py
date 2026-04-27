from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from finlens.state import load_state, save_state


@dataclass
class PipelineStep:
    name: str
    status: str
    duration_seconds: float
    detail: str
    metadata: dict[str, Any]


class PipelineRunRecorder:
    def __init__(self, run_type: str) -> None:
        self.run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        self.run_type = run_type
        self.started_at = datetime.now(UTC)
        self.steps: list[PipelineStep] = []

    def record(
        self,
        name: str,
        func: Callable[[], Any],
        *,
        detail: Callable[[Any], str] | None = None,
        metadata: Callable[[Any], dict[str, Any]] | None = None,
        allow_failure: bool = False,
    ) -> Any:
        started = time.perf_counter()
        try:
            result = func()
        except Exception as exc:
            self.steps.append(
                PipelineStep(
                    name=name,
                    status="Failed",
                    duration_seconds=round(time.perf_counter() - started, 3),
                    detail=str(exc),
                    metadata={},
                )
            )
            if allow_failure:
                return None
            raise

        self.steps.append(
            PipelineStep(
                name=name,
                status="Success",
                duration_seconds=round(time.perf_counter() - started, 3),
                detail=detail(result) if detail else "Completed",
                metadata=metadata(result) if metadata else {},
            )
        )
        return result

    def finish(self, status: str = "Success") -> dict[str, Any]:
        finished_at = datetime.now(UTC)
        payload = {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - self.started_at).total_seconds(), 3),
            "steps": [
                {
                    "name": step.name,
                    "status": step.status,
                    "duration_seconds": step.duration_seconds,
                    "detail": step.detail,
                    "metadata": step.metadata,
                }
                for step in self.steps
            ],
        }
        save_pipeline_run(payload)
        return payload


def save_pipeline_run(payload: dict[str, Any]) -> None:
    history = load_state("pipeline_run_history", default=[])
    if not isinstance(history, list):
        history = []
    history.append(payload)
    save_state("pipeline_run_history", history[-25:])
    save_state("latest_pipeline_run", payload)


def latest_pipeline_run() -> dict[str, Any]:
    return load_state("latest_pipeline_run", default={})


def pipeline_run_history() -> list[dict[str, Any]]:
    history = load_state("pipeline_run_history", default=[])
    return history if isinstance(history, list) else []
