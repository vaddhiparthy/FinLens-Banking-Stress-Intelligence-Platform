from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from finlens.aws import upload_artifact_if_configured
from finlens.config import get_settings
from finlens.http import build_session, get_text
from finlens.ingestion.base import IngestionTarget, build_storage_path
from finlens.logging import get_logger
from finlens.storage import write_json

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class FdicIngestionResult:
    record_count: int
    output_path: Path
    source_url: str
    s3_uri: str | None = None


def fetch_failed_bank_rows() -> list[dict[str, str]]:
    settings = get_settings()
    session = build_session()
    csv_text = get_text(session, settings.fdic_failed_banks_url)
    reader = csv.DictReader(StringIO(csv_text))
    return [dict(row) for row in reader]


def build_failed_bank_payload(rows: list[dict[str, str]]) -> dict[str, Any]:
    settings = get_settings()
    return {
        "source": "fdic",
        "dataset": "failed_bank_list",
        "ingested_at": datetime.now(UTC).isoformat(),
        "source_url": settings.fdic_failed_banks_url,
        "record_count": len(rows),
        "records": rows,
    }


def ingest_fdic_failed_banks() -> FdicIngestionResult:
    rows = fetch_failed_bank_rows()
    payload = build_failed_bank_payload(rows)
    target = IngestionTarget.create("fdic")
    output_path = write_json(build_storage_path(target), payload)
    s3_uri = upload_artifact_if_configured(output_path, target)
    LOGGER.info("fdic_ingestion_complete", output_path=str(output_path), record_count=len(rows))
    return FdicIngestionResult(
        record_count=len(rows),
        output_path=output_path,
        source_url=payload["source_url"],
        s3_uri=s3_uri,
    )


def main() -> None:
    result = ingest_fdic_failed_banks()
    print(asdict(result))


if __name__ == "__main__":
    main()
