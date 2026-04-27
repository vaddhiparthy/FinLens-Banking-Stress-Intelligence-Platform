from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from finlens.aws import upload_artifact_if_configured
from finlens.config import get_settings
from finlens.http import build_session, get_bytes
from finlens.ingestion.base import IngestionTarget, build_storage_path
from finlens.logging import get_logger
from finlens.storage import write_bytes, write_json

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class QbpIngestionResult:
    artifact_path: Path
    metadata_path: Path
    source_url: str
    size_bytes: int
    artifact_s3_uri: str | None = None
    metadata_s3_uri: str | None = None


def _artifact_extension(source_url: str) -> str:
    path = urlparse(source_url).path
    suffix = Path(path).suffix
    return suffix or ".bin"


def _read_source_payload(source_url: str) -> bytes:
    parsed = urlparse(source_url)
    if parsed.scheme in {"http", "https"}:
        session = build_session()
        return get_bytes(session, source_url)
    if parsed.scheme == "file":
        return Path(parsed.path).read_bytes()
    path = Path(source_url)
    if path.exists():
        return path.read_bytes()
    session = build_session()
    return get_bytes(session, source_url)


def _to_number(value: object) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _rate(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round((numerator / denominator) * 100, 4)


def _normalize_fdic_summary(payload: bytes) -> bytes:
    try:
        document = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return payload

    rows = []
    for item in document.get("data", []):
        data = item.get("data", item)
        year = str(data.get("YEAR", "")).strip()
        if not year:
            continue
        asset = _to_number(data.get("sum_ASSET") or data.get("ASSET"))
        net_income = _to_number(data.get("sum_NETINC") or data.get("NETINC"))
        net_interest_income = _to_number(data.get("sum_NIM") or data.get("NIM"))
        charge_offs = _to_number(data.get("sum_DRLNLS") or data.get("DRLNLS"))
        noncurrent = _to_number(data.get("sum_P9LNLS") or data.get("P9LNLS"))
        equity = _to_number(data.get("sum_EQ") or data.get("EQ"))
        deposits = _to_number(data.get("sum_DEP") or data.get("DEP"))
        rows.append(
            {
                "quarter": f"{year}Q4",
                "net_income": net_income,
                "roa": _rate(net_income, asset),
                "nim": _rate(net_interest_income, asset),
                "problem_banks": None,
                "asset_yield": None,
                "funding_cost": None,
                "noncurrent_rate": _rate(noncurrent, asset),
                "nco_rate": _rate(charge_offs, asset),
                "afs_losses": None,
                "htm_losses": None,
                "total_assets": asset,
                "total_deposits": deposits,
                "total_equity": equity,
                "source_code": "FDIC_BANKS_SUMMARY",
            }
        )

    if not rows:
        return payload
    return json.dumps(rows, indent=2).encode("utf-8")


def ingest_fdic_qbp() -> QbpIngestionResult:
    settings = get_settings()
    settings.require("fdic_qbp_source_url")

    source_url = settings.fdic_qbp_source_url or ""
    payload = _normalize_fdic_summary(_read_source_payload(source_url))
    target = IngestionTarget.create("qbp")
    artifact_path = write_bytes(
        build_storage_path(target, extension=".data.json"),
        payload,
    )
    artifact_s3_uri = upload_artifact_if_configured(artifact_path, target)
    metadata_path = write_json(
        build_storage_path(target),
        {
            "source": "qbp",
            "dataset": "fdic_quarterly_banking_profile",
            "ingested_at": datetime.now(UTC).isoformat(),
            "source_url": source_url,
            "artifact_path": str(artifact_path),
            "artifact_s3_uri": artifact_s3_uri,
            "size_bytes": len(payload),
        },
    )
    metadata_s3_uri = upload_artifact_if_configured(metadata_path, target)
    LOGGER.info(
        "qbp_ingestion_complete",
        artifact_path=str(artifact_path),
        metadata_path=str(metadata_path),
        size_bytes=len(payload),
    )
    return QbpIngestionResult(
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        source_url=source_url,
        size_bytes=len(payload),
        artifact_s3_uri=artifact_s3_uri,
        metadata_s3_uri=metadata_s3_uri,
    )


def main() -> None:
    print(asdict(ingest_fdic_qbp()))


if __name__ == "__main__":
    main()
