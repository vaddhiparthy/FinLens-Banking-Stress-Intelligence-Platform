"""MLflow model-registry helpers (alias-based champion/challenger).

Centralizes registry operations so train (promotion) and serving (resolution) share one
implementation. Uses MLflow 3.x **aliases** (not deprecated stages): the champion alias is
what serving resolves (`models:/<name>@champion`), so promotion/rollback is a single alias
repoint. Best-effort + offline-tolerant — callers fall back to the local artifact if the
registry is unavailable. $0: MLflow on a local sqlite/Postgres backend, no billable service.
"""

from __future__ import annotations

from finlens_ml.config import get_ml_settings


def _client():
    import mlflow

    settings = get_ml_settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    return mlflow.tracking.MlflowClient()


def champion_uri() -> str:
    s = get_ml_settings()
    return f"models:/{s.registered_model_name}@{s.champion_alias}"


def set_champion(version: str | int) -> None:
    """Point the champion alias at a registered model version (promotion / rollback)."""
    s = get_ml_settings()
    _client().set_registered_model_alias(s.registered_model_name, s.champion_alias, str(version))


def latest_version() -> str | None:
    s = get_ml_settings()
    try:
        versions = _client().search_model_versions(f"name='{s.registered_model_name}'")
        if not versions:
            return None
        return str(max(versions, key=lambda v: int(v.version)).version)
    except Exception:
        return None


def champion_version() -> str | None:
    s = get_ml_settings()
    try:
        mv = _client().get_model_version_by_alias(s.registered_model_name, s.champion_alias)
        return str(mv.version)
    except Exception:
        return None


def promote_latest_to_champion() -> str | None:
    """Set the champion alias to the newest registered version. Returns the version, or None."""
    v = latest_version()
    if v is not None:
        try:
            set_champion(v)
        except Exception:
            return None
    return v
