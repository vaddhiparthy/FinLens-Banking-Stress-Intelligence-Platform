from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from finlens.config import get_settings
from finlens.datasets import load_demo_bundle, load_demo_stress_pulse
from finlens.paths import RAW_DATA_DIR, ROOT_DIR
from finlens.pipeline_status import update_flow_status

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = object


def local_duckdb_path() -> Path:
    return ROOT_DIR / ".duckdb" / "finlens.duckdb"


def _latest_source_json(source: str) -> dict | None:
    source_dir = RAW_DATA_DIR / f"source={source}"
    if not source_dir.exists():
        return None
    candidates = [
        path
        for path in source_dir.glob("ingestion_date=*/*.json")
        if not path.name.endswith(".data.json")
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return json.loads(latest.read_text(encoding="utf-8"))


def latest_source_manifest(source: str) -> dict | None:
    return _latest_source_json(source)


def _latest_source_payloads(source: str) -> list[dict]:
    source_dir = RAW_DATA_DIR / f"source={source}"
    if not source_dir.exists():
        return []
    payloads: list[dict] = []
    for path in sorted(source_dir.glob("ingestion_date=*/*.json")):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def _clean_fdic_key(key: str) -> str:
    cleaned = key.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", cleaned).strip("_").lower()
    return cleaned


def _fdic_failures_frame():
    payload = _latest_source_json("fdic")
    if not payload or not payload.get("records"):
        return load_demo_bundle().failures.copy()

    rows = []
    for record in payload["records"]:
        clean = {_clean_fdic_key(key): value for key, value in record.items()}
        bank_name = clean.get("bank_name") or "Unknown institution"
        cert = clean.get("cert") or ""
        close_date = pd.to_datetime(clean.get("closing_date"), errors="coerce")
        rows.append(
            {
                "bank_id": cert or f"{bank_name}-{clean.get('state', 'NA')}",
                "bank_name": bank_name,
                "city": clean.get("city") or "",
                "state": clean.get("state") or "",
                "cert": cert,
                "acquirer": clean.get("acquiring_institution") or "Unknown",
                "closing_date": close_date,
                "year": int(close_date.year) if not pd.isna(close_date) else 0,
                "assets_millions": float("nan"),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return load_demo_bundle().failures.copy()
    return frame.sort_values(["year", "bank_name"], ascending=[False, True]).reset_index(drop=True)


def _fdic_acquirers_frame(failures):
    if failures.empty:
        return load_demo_bundle().acquirers.copy()
    grouped = (
        failures.assign(
            decade=lambda data: (data["year"].fillna(0).astype(int) // 10 * 10).astype(str) + "s"
        )
        .groupby(["acquirer", "decade"], dropna=False)
        .size()
        .reset_index(name="failure_count")
    )
    grouped["assets_absorbed_millions"] = grouped["failure_count"].astype(float)
    return grouped


def _fred_metrics_frame():
    payloads = _latest_source_payloads("fred")
    if not payloads:
        return load_demo_bundle().metrics.copy()

    latest_by_series: dict[str, dict] = {}
    for payload in payloads:
        series_id = payload.get("series_id")
        ingested_at = payload.get("ingested_at", "")
        if not series_id:
            continue
        existing = latest_by_series.get(series_id)
        if existing is None or ingested_at > existing.get("ingested_at", ""):
            latest_by_series[series_id] = payload

    rows: list[dict] = []
    for payload in latest_by_series.values():
        metadata = payload.get("metadata", {})
        metric_name = metadata.get("title") or metadata.get("id") or payload.get("series_id")
        for observation in payload.get("observations", []):
            value = observation.get("value")
            if value in (None, ".", ""):
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "series_id": payload.get("series_id"),
                    "date": observation.get("date"),
                    "value": numeric_value,
                    "metric_name": metric_name,
                }
            )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return load_demo_bundle().metrics.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values(["series_id", "date"]).reset_index(drop=True)


def _stress_pulse_frame():
    expected_columns = [
        "quarter",
        "net_income",
        "roa",
        "nim",
        "problem_banks",
        "asset_yield",
        "funding_cost",
        "noncurrent_rate",
        "nco_rate",
        "afs_losses",
        "htm_losses",
    ]
    settings = get_settings()
    payload = _latest_source_json("qbp")
    if not payload:
        if settings.finlens_data_mode == "live":
            return pd.DataFrame(columns=expected_columns)
        return load_demo_stress_pulse().copy()

    artifact_path = payload.get("artifact_path")
    if not artifact_path:
        if settings.finlens_data_mode == "live":
            return pd.DataFrame(columns=expected_columns)
        return load_demo_stress_pulse().copy()

    path = Path(artifact_path)
    if not path.exists():
        if settings.finlens_data_mode == "live":
            return pd.DataFrame(columns=expected_columns)
        return load_demo_stress_pulse().copy()

    if path.suffix.lower() == ".json":
        frame = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        if settings.finlens_data_mode == "live":
            return pd.DataFrame(columns=expected_columns)
        return load_demo_stress_pulse().copy()

    required = set(expected_columns)
    if not required.issubset(frame.columns):
        if settings.finlens_data_mode == "live":
            return pd.DataFrame(columns=expected_columns)
        return load_demo_stress_pulse().copy()
    return frame.copy()


def _nic_current_parent_frame():
    expected_columns = [
        "rssd_id",
        "fdic_certificate_number",
        "institution_name",
        "current_parent_rssd_id",
        "current_parent_name",
        "active",
        "charter_class",
        "state",
        "primary_regulator",
        "total_assets",
        "total_deposits",
        "roa",
        "roe",
        "source_updated_at",
        "source_code",
    ]
    payload = _latest_source_json("nic")
    if not payload:
        return pd.DataFrame(columns=expected_columns)
    artifact_path = payload.get("artifact_path")
    if not artifact_path:
        return pd.DataFrame(columns=expected_columns)
    path = Path(artifact_path)
    if not path.exists() or path.suffix.lower() != ".json":
        return pd.DataFrame(columns=expected_columns)
    frame = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    for column in expected_columns:
        if column not in frame.columns:
            frame[column] = None
    return frame[expected_columns].copy()


def stress_pulse_source_mode() -> str:
    settings = get_settings()
    payload = _latest_source_json("qbp")
    if not payload:
        if settings.finlens_data_mode == "live":
            return "pending"
        return "demo"
    artifact_path = payload.get("artifact_path")
    if not artifact_path:
        if settings.finlens_data_mode == "live":
            return "pending"
        return "demo"
    path = Path(artifact_path)
    if not path.exists():
        if settings.finlens_data_mode == "live":
            return "pending"
        return "demo"
    if path.suffix.lower() in {".json", ".csv"}:
        try:
            frame = _stress_pulse_frame()
        except Exception:
            return "demo"
        required = {
            "quarter",
            "net_income",
            "roa",
            "nim",
            "problem_banks",
            "asset_yield",
            "funding_cost",
            "noncurrent_rate",
            "nco_rate",
            "afs_losses",
            "htm_losses",
        }
        if required.issubset(frame.columns):
            return "live"
    return "demo"


def initialise_local_duckdb() -> Path:
    import duckdb

    db_path = local_duckdb_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    failures = _fdic_failures_frame()
    metrics = _fred_metrics_frame()
    acquirers = _fdic_acquirers_frame(failures)
    stress_pulse = _stress_pulse_frame()
    nic_current_parent = _nic_current_parent_frame()

    with duckdb.connect(str(db_path)) as conn:
        update_flow_status(
            "bronze_to_silver",
            status="Running",
            last_run=datetime.now(UTC).isoformat(),
            rows="4 contracts",
            note="Normalizing raw source payloads",
        )
        conn.execute("create schema if not exists raw")
        conn.execute("create schema if not exists marts")
        conn.register("failures_df", failures)
        conn.register("metrics_df", metrics)
        conn.register("acquirers_df", acquirers)
        conn.register("stress_pulse_df", stress_pulse)
        conn.register("nic_current_parent_df", nic_current_parent)
        update_flow_status(
            "bronze_to_silver",
            status="Success",
            last_run=datetime.now(UTC).isoformat(),
            rows="4 contracts",
            note="Canonical frames rebuilt",
        )

        update_flow_status(
            "silver_to_gold",
            status="Running",
            last_run=datetime.now(UTC).isoformat(),
            rows="4 views",
            note="Refreshing marts schema",
        )
        conn.execute(
            "create or replace table raw.fdic_failed_banks_raw as select * from failures_df"
        )
        conn.execute(
            "create or replace table raw.fred_observations_raw as select * from metrics_df"
        )
        conn.execute("create or replace table raw.fdic_qbp_raw as select * from stress_pulse_df")
        conn.execute(
            """
            create or replace table raw.nic_current_parent_raw as
            select * from nic_current_parent_df
            """
        )
        conn.execute(
            "create or replace table marts.fct_bank_failures as select * from failures_df"
        )
        conn.execute(
            "create or replace table marts.fct_financial_metrics as select * from metrics_df"
        )
        conn.execute("create or replace table marts.dim_acquirer as select * from acquirers_df")
        conn.execute(
            "create or replace table marts.fct_stress_pulse as select * from stress_pulse_df"
        )
        update_flow_status(
            "silver_to_gold",
            status="Success",
            last_run=datetime.now(UTC).isoformat(),
            rows="4 views",
            note="Gold marts refreshed",
        )
        update_flow_status(
            "gold_to_dashboards",
            status="Success",
            last_run=datetime.now(UTC).isoformat(),
            rows="4 surfaces",
            note="Dashboard contracts ready",
        )

    return db_path


def read_table(name: str) -> pd.DataFrame:
    import duckdb

    settings = get_settings()
    if settings.finlens_data_mode == "mock":
        initialise_local_duckdb()
    with duckdb.connect(str(local_duckdb_path())) as conn:
        return conn.execute(f"select * from {name}").df()
