"""Bank-quarter panel construction from ingested per-institution FDIC data.

Reads the raw JSON written by ``ingestion/fdic_institutions.py`` and builds an
immutable, point-in-time bank-quarter panel (one row per CERT per quarter). The
panel is the foundation for the discrete-time hazard model: features are derived
from it (P2) and labels are attached to it (``labels.py``).

This module imports only stdlib + pandas + the finlens raw-path helper. It never
imports ``finlens.aws`` / ``boto3`` / ``snowflake`` ($0 invariant).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from finlens.paths import RAW_DATA_DIR

# numeric financial columns coerced to float; identity columns kept as-is
_ID_COLS = ["CERT", "REPDTE", "NAMEFULL"]


def _institution_payloads() -> list[dict]:
    import json

    source_dir = RAW_DATA_DIR / "source=fdic_institutions"
    if not source_dir.exists():
        return []
    payloads = []
    for path in sorted(source_dir.glob("ingestion_date=*/*.json")):
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def _latest_records(dataset: str) -> list[dict]:
    """Most-recently-ingested record set for a given dataset name."""
    matches = [p for p in _institution_payloads() if p.get("dataset") == dataset]
    if not matches:
        return []
    latest = max(matches, key=lambda p: p.get("ingested_at", ""))
    return latest.get("records", [])


def _to_quarter(repdte: object) -> str | None:
    s = str(repdte)
    if len(s) != 8 or not s.isdigit():
        return None
    year, month = int(s[:4]), int(s[4:6])
    quarter = (month - 1) // 3 + 1
    return f"{year}Q{quarter}"


def load_financials_frame(records: list[dict] | None = None) -> pd.DataFrame:
    """Per-CERT quarterly financials as a clean numeric DataFrame."""
    records = records if records is not None else _latest_records("call_report_financials")
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records)
    frame["cert"] = pd.to_numeric(frame["CERT"], errors="coerce").astype("Int64")
    frame["repdte"] = pd.to_datetime(frame["REPDTE"], format="%Y%m%d", errors="coerce")
    frame["quarter"] = frame["REPDTE"].map(_to_quarter)
    numeric_cols = [c for c in frame.columns if c not in _ID_COLS + ["cert", "repdte", "quarter"]]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.rename(columns={"NAMEFULL": "bank_name"})
    frame = frame.dropna(subset=["cert", "repdte"]).copy()
    return frame.sort_values(["cert", "repdte"]).reset_index(drop=True)


def load_institutions_frame(records: list[dict] | None = None) -> pd.DataFrame:
    """Per-CERT entity metadata (state, charter class, active, exit date)."""
    records = records if records is not None else _latest_records("institutions")
    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records)
    frame["cert"] = pd.to_numeric(frame.get("CERT"), errors="coerce").astype("Int64")
    for col in ("ESTYMD", "ENDEFYMD"):
        if col in frame.columns:
            frame[col.lower()] = pd.to_datetime(frame[col], errors="coerce")
    frame["state"] = frame.get("STALP")
    frame["bank_class"] = frame.get("BKCLASS")
    frame["active"] = pd.to_numeric(frame.get("ACTIVE"), errors="coerce").astype("Int64")
    keep = ["cert", "state", "bank_class", "active", "estymd", "endefymd"]
    return frame[[c for c in keep if c in frame.columns]].dropna(subset=["cert"]).copy()


def build_panel(
    financials: pd.DataFrame | None = None,
    institutions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join financials with entity metadata into the bank-quarter panel."""
    fin = financials if financials is not None else load_financials_frame()
    if fin.empty:
        return fin
    inst = institutions if institutions is not None else load_institutions_frame()
    if not inst.empty:
        meta_cols = ["cert", "state", "bank_class"]
        fin = fin.merge(inst[[c for c in meta_cols if c in inst.columns]], on="cert", how="left")
    return fin


def materialize_panel(duckdb_path: Path, panel: pd.DataFrame, schema: str = "ml") -> int:
    """Persist the panel to an immutable DuckDB table (the visible DE/AI artifact)."""
    import duckdb

    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute(f"create schema if not exists {schema}")
        conn.register("panel_df", panel)
        conn.execute(f"create or replace table {schema}.bank_quarter_panel as select * from panel_df")
        count = conn.execute(f"select count(*) from {schema}.bank_quarter_panel").fetchone()[0]
    return int(count)
