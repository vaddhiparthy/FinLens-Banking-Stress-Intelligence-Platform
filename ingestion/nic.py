from __future__ import annotations

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


def ingest_nic_current_parent() -> NicIngestionResult:
    settings = get_settings()
    settings.require("nic_current_parent_source_url")

    session = build_session()
    source_url = settings.nic_current_parent_source_url or ""
    payload = get_bytes(session, source_url)
    target = IngestionTarget.create("nic")
    artifact_path = write_bytes(
        build_storage_path(target, extension=_artifact_extension(source_url)),
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
