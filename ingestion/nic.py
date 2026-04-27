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
class NicIngestionResult:
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


def _normalize_institutions(payload: bytes) -> bytes:
    try:
        document = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return payload

    rows = []
    for item in document.get("data", []):
        data = item.get("data", item)
        cert = data.get("CERT")
        rows.append(
            {
                "rssd_id": None,
                "fdic_certificate_number": str(cert) if cert is not None else None,
                "institution_name": data.get("NAME"),
                "current_parent_rssd_id": None,
                "current_parent_name": None,
                "active": data.get("ACTIVE"),
                "charter_class": data.get("BKCLASS"),
                "state": data.get("STALP"),
                "primary_regulator": data.get("REGAGNT"),
                "total_assets": data.get("ASSET"),
                "total_deposits": data.get("DEP"),
                "roa": data.get("ROA"),
                "roe": data.get("ROE"),
                "source_updated_at": data.get("DATEUPDT"),
                "source_code": "FDIC_BANKS_INSTITUTIONS",
            }
        )

    if not rows:
        return payload
    return json.dumps(rows, indent=2).encode("utf-8")


def ingest_nic_current_parent() -> NicIngestionResult:
    settings = get_settings()
    settings.require("nic_current_parent_source_url")

    source_url = settings.nic_current_parent_source_url or ""
    payload = _normalize_institutions(_read_source_payload(source_url))
    target = IngestionTarget.create("nic")
    artifact_path = write_bytes(
        build_storage_path(target, extension=".data.json"),
        payload,
    )
    artifact_s3_uri = upload_artifact_if_configured(artifact_path, target)
    metadata_path = write_json(
        build_storage_path(target),
        {
            "source": "nic",
            "dataset": "current_parent_only",
            "ingested_at": datetime.now(UTC).isoformat(),
            "source_url": source_url,
            "artifact_path": str(artifact_path),
            "artifact_s3_uri": artifact_s3_uri,
            "size_bytes": len(payload),
        },
    )
    metadata_s3_uri = upload_artifact_if_configured(metadata_path, target)
    LOGGER.info(
        "nic_ingestion_complete",
        artifact_path=str(artifact_path),
        metadata_path=str(metadata_path),
        size_bytes=len(payload),
    )
    return NicIngestionResult(
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        source_url=source_url,
        size_bytes=len(payload),
        artifact_s3_uri=artifact_s3_uri,
        metadata_s3_uri=metadata_s3_uri,
    )


def main() -> None:
    print(asdict(ingest_nic_current_parent()))


if __name__ == "__main__":
    main()
