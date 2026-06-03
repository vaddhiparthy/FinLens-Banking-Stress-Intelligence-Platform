"""ML subsystem settings — credential-free by design.

This object deliberately exposes ONLY machine-learning configuration: filesystem
paths, model horizons, decision thresholds, the MLflow tracking URI, and the
DuckDB path. It exposes NO AWS credentials, NO S3 buckets, and NO
``aws_s3_mirror_enabled`` flag. ML code therefore cannot reach a billable service
through its own settings — the $0 invariant holds by construction, and the CI
import-guard (forbidding ``finlens.aws`` / ``boto3`` / ``snowflake`` imports under
``ml/finlens_ml``) backs it up.

All values are overridable via ``FINLENS_ML_*`` environment variables so the same
code runs identically on the workstation and on the VPS without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser() if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    try:
        return float(raw) if raw is not None else default
    except ValueError:
        return default


@dataclass(frozen=True)
class MLSettings:
    """Machine-learning configuration. No AWS / billable fields, intentionally."""

    repo_root: Path

    # --- storage (local only) ---
    duckdb_path: Path
    artifact_dir: Path  # local model + report artifacts
    mlflow_tracking_uri: str  # local file store by default; postgres URI on VPS

    # --- modeling ---
    train_start_quarter: str  # earliest REPDTE quarter to include, e.g. "2008Q1"
    primary_horizon_q: int  # quarters ahead for the primary failure/distress label
    secondary_horizon_q: int
    reporting_lag_q: int  # call-report filing lag embargo, in quarters
    random_seed: int

    # --- decision thresholds (overridable; calibrated probabilities) ---
    flag_threshold: float  # probability above which a bank is flagged for review
    review_budget_k: int  # top-k banks a supervisor would review (for recall@k)

    # --- experiment / registry ---
    registered_model_name: str
    champion_alias: str
    challenger_alias: str

    # explicit, immutable record that this subsystem touches no billable service
    cost_guarantee: str = field(
        default="$0 — no AWS/S3/Snowflake/paid-API access from the ML subsystem",
    )


@lru_cache(maxsize=1)
def get_ml_settings() -> MLSettings:
    root = _repo_root()
    default_duckdb = root / ".duckdb" / "finlens.duckdb"
    default_artifacts = root / "ml" / "artifacts"
    # sqlite backend by default so the MLflow MODEL REGISTRY (aliases) works locally;
    # a file store cannot host the registry. On the VPS, override with a Postgres URI
    # via FINLENS_ML_MLFLOW_URI. Single source of truth read by train/registry/serving.
    default_mlflow = os.environ.get(
        "FINLENS_ML_MLFLOW_URI",
        f"sqlite:///{(root / 'ml' / 'mlflow.db').as_posix()}",
    )
    return MLSettings(
        repo_root=root,
        duckdb_path=_env_path("FINLENS_ML_DUCKDB_PATH", default_duckdb),
        artifact_dir=_env_path("FINLENS_ML_ARTIFACT_DIR", default_artifacts),
        mlflow_tracking_uri=default_mlflow,
        train_start_quarter=os.environ.get("FINLENS_ML_TRAIN_START", "2008Q1"),
        primary_horizon_q=_env_int("FINLENS_ML_HORIZON_PRIMARY", 4),
        secondary_horizon_q=_env_int("FINLENS_ML_HORIZON_SECONDARY", 8),
        reporting_lag_q=_env_int("FINLENS_ML_REPORTING_LAG_Q", 1),
        random_seed=_env_int("FINLENS_ML_SEED", 42),
        flag_threshold=_env_float("FINLENS_ML_FLAG_THRESHOLD", 0.10),
        review_budget_k=_env_int("FINLENS_ML_REVIEW_BUDGET_K", 200),
        registered_model_name=os.environ.get(
            "FINLENS_ML_MODEL_NAME", "finlens_bank_distress"
        ),
        champion_alias=os.environ.get("FINLENS_ML_CHAMPION_ALIAS", "champion"),
        challenger_alias=os.environ.get("FINLENS_ML_CHALLENGER_ALIAS", "challenger"),
    )
