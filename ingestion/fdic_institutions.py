"""Institution-level FDIC ingestion (per-CERT quarterly financials + metadata).

This is the data foundation for the ML subsystem. Unlike ``ingestion/qbp.py`` (which
sums all banks into one system-level row per quarter), this pulls the per-institution
panel needed for a per-bank distress model: one row per CERT per quarter.

Source: FDIC BankFind Suite API (https://api.fdic.gov/banks) — public, no API key.
  - /financials  : per-CERT quarterly Call Report financials (filter by REPDTE)
  - /institutions: per-CERT entity metadata (name, state, charter class, active flag)

Cost: $0. This module intentionally does NOT import ``finlens.aws`` /
``upload_artifact_if_configured`` — it writes locally only, so it adds zero billable
S3 activity even where the global mirror flag is enabled.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finlens.http import build_session, get_json
from finlens.ingestion.base import IngestionTarget, build_storage_path
from finlens.logging import get_logger
from finlens.storage import write_json

LOGGER = get_logger(__name__)

FDIC_API_BASE = "https://api.fdic.gov/banks"
PAGE_LIMIT = 10_000  # FDIC API max rows per request

# Curated CAMELS-relevant financial fields (amounts + FDIC-published ratios). The
# feature layer derives trends/peer-z-scores; raw amounts let dbt recompute ratios
# consistently. Missing fields for a given vintage are tolerated downstream.
FINANCIAL_FIELDS = [
    "CERT", "REPDTE", "NAMEFULL", "STALP", "BKCLASS",
    # size / balance sheet (SCHA=held-to-maturity amortized cost, SCAF=available-for-sale
    # fair value: HTM/AFS concentration is the duration/rate-risk signal behind 2023)
    "ASSET", "DEP", "EQ", "LNLSNET", "LNLSGR", "SC", "SCHA", "SCAF", "CHBAL",
    # capital
    "RBCT1J", "RBC1AAJ", "RBC1RWAJ", "RBCRWAJ", "EQV",
    # asset quality
    "P9LNLS", "P3LNLS", "NCLNLS", "DRLNLS", "CRLNLS", "LNATRES", "NPERFV",
    # earnings
    "NETINC", "NETINCQ", "ROA", "ROAPTX", "ROE", "NIMY", "INTINCY", "EINTEXP",
    "NONIIAY", "NOIJY", "ELNATR",
    # liquidity / funding (DEPINS = insured deposits -> uninsured share, the SVB signal)
    "IDDEPINS", "DEPDOM", "BRO", "VOLIAB", "DEPINS",
    # FDIC-published asset-quality / earnings ratios (stable, convenient)
    "NTLNLSR", "NCLNLSR", "ERNASTR", "EEFFR",
]

INSTITUTION_FIELDS = [
    "CERT", "NAME", "STALP", "CITY", "ACTIVE", "BKCLASS", "CHARTER",
    "ESTYMD", "ENDEFYMD", "ASSET", "DEP", "OFFDOM", "INACTIVE",
]


@dataclass(frozen=True)
class InstitutionIngestionResult:
    dataset: str
    record_count: int
    quarter_count: int
    output_path: Path
    source_url: str


def quarter_repdtes(start_quarter: str, end_quarter: str) -> list[str]:
    """Yield FDIC REPDTE strings (YYYYMMDD) for every quarter in [start, end].

    ``start_quarter`` / ``end_quarter`` are like ``"2008Q1"`` .. ``"2026Q1"``.
    """
    quarter_end = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}

    def parse(q: str) -> tuple[int, int]:
        year, quarter = q.upper().split("Q")
        return int(year), int(quarter)

    sy, sq = parse(start_quarter)
    ey, eq = parse(end_quarter)
    out: list[str] = []
    y, q = sy, sq
    while (y, q) <= (ey, eq):
        out.append(f"{y}{quarter_end[q]}")
        q += 1
        if q > 4:
            q = 1
            y += 1
    return out


def _unwrap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """FDIC wraps each record as {"data": {...}, "score": ...}; pull the inner dict."""
    return [row.get("data", row) for row in rows]


def fetch_page(
    session, endpoint: str, *, fields: list[str], filters: str | None, offset: int
) -> tuple[list[dict[str, Any]], int]:
    params: dict[str, Any] = {
        "fields": ",".join(fields),
        "limit": PAGE_LIMIT,
        "offset": offset,
        "format": "json",
    }
    if filters:
        params["filters"] = filters
    payload = get_json(session, f"{FDIC_API_BASE}/{endpoint}", params=params)
    total = int(payload.get("meta", {}).get("total", 0))
    return _unwrap(payload.get("data", [])), total


def fetch_all(
    session, endpoint: str, *, fields: list[str], filters: str | None
) -> list[dict[str, Any]]:
    rows, total = fetch_page(session, endpoint, fields=fields, filters=filters, offset=0)
    while len(rows) < total:
        page, _ = fetch_page(
            session, endpoint, fields=fields, filters=filters, offset=len(rows)
        )
        if not page:
            break
        rows.extend(page)
    return rows


def fetch_financials(start_quarter: str, end_quarter: str) -> list[dict[str, Any]]:
    session = build_session(user_agent="finlens-ml/0.1 (research)")
    records: list[dict[str, Any]] = []
    for repdte in quarter_repdtes(start_quarter, end_quarter):
        quarter_rows = fetch_all(
            session, "financials", fields=FINANCIAL_FIELDS, filters=f"REPDTE:{repdte}"
        )
        records.extend(quarter_rows)
        LOGGER.info(
            "fdic_financials_quarter", repdte=repdte, rows=len(quarter_rows)
        )
    return records


def fetch_institutions() -> list[dict[str, Any]]:
    session = build_session(user_agent="finlens-ml/0.1 (research)")
    return fetch_all(session, "institutions", fields=INSTITUTION_FIELDS, filters=None)


def _write(dataset: str, records: list[dict[str, Any]], source_url: str) -> Path:
    target = IngestionTarget.create("fdic_institutions")
    payload = {
        "source": "fdic_institutions",
        "dataset": dataset,
        "ingested_at": datetime.now(UTC).isoformat(),
        "source_url": source_url,
        "record_count": len(records),
        "records": records,
    }
    return write_json(build_storage_path(target), payload)


def ingest_institution_financials(
    start_quarter: str = "2008Q1", end_quarter: str | None = None
) -> InstitutionIngestionResult:
    if end_quarter is None:
        now = datetime.now(UTC)
        # most recent fully-filed quarter (filing lag ~1 quarter)
        prior_q = (now.month - 1) // 3  # 0..3 -> last completed quarter index
        end_year, end_q = (now.year, prior_q) if prior_q >= 1 else (now.year - 1, 4)
        end_quarter = f"{end_year}Q{end_q}"
    records = fetch_financials(start_quarter, end_quarter)
    quarters = {r.get("REPDTE") for r in records}
    output_path = _write("call_report_financials", records, f"{FDIC_API_BASE}/financials")
    LOGGER.info(
        "fdic_institution_financials_complete",
        record_count=len(records),
        quarter_count=len(quarters),
        output_path=str(output_path),
    )
    return InstitutionIngestionResult(
        dataset="call_report_financials",
        record_count=len(records),
        quarter_count=len(quarters),
        output_path=output_path,
        source_url=f"{FDIC_API_BASE}/financials",
    )


def ingest_institution_metadata() -> InstitutionIngestionResult:
    records = fetch_institutions()
    output_path = _write("institutions", records, f"{FDIC_API_BASE}/institutions")
    LOGGER.info(
        "fdic_institution_metadata_complete",
        record_count=len(records),
        output_path=str(output_path),
    )
    return InstitutionIngestionResult(
        dataset="institutions",
        record_count=len(records),
        quarter_count=0,
        output_path=output_path,
        source_url=f"{FDIC_API_BASE}/institutions",
    )


def main() -> None:
    meta = ingest_institution_metadata()
    fin = ingest_institution_financials()
    print(json.dumps({"metadata": asdict(meta), "financials": asdict(fin)}, default=str))


if __name__ == "__main__":
    main()
