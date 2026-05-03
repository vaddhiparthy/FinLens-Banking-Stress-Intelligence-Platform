from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from tenacity import retry, stop_after_attempt, wait_exponential

from finlens.config import get_settings
from finlens.paths import DLQ_DATA_DIR, RAW_DATA_DIR


@dataclass(frozen=True)
class IngestionTarget:
    source: str
    ingestion_date: date
    object_id: str
    dead_letter: bool = False

    @classmethod
    def create(
        cls,
        source: str,
        *,
        ingestion_date: date | None = None,
        dead_letter: bool = False,
    ) -> "IngestionTarget":
        return cls(
            source=source,
            ingestion_date=ingestion_date or datetime.now(UTC).date(),
            object_id=str(uuid4()),
            dead_letter=dead_letter,
        )


def build_s3_key(target: IngestionTarget) -> str:
    settings = get_settings()
    bucket = settings.aws_s3_dlq_bucket if target.dead_letter else settings.aws_s3_raw_bucket
    base = f"s3://{bucket}"
    return (
        f"{base}/source={target.source}/"
        f"ingestion_date={target.ingestion_date.isoformat()}/{target.object_id}.json"
    )


def build_storage_path(target: IngestionTarget, *, extension: str = ".json") -> Path:
    base_dir = DLQ_DATA_DIR if target.dead_letter else RAW_DATA_DIR
    suffix = extension if extension.startswith(".") else f".{extension}"
    return (
        base_dir
        / f"source={target.source}"
        / f"ingestion_date={target.ingestion_date.isoformat()}"
        / f"{target.object_id}{suffix}"
    )


def build_retry_policy():
    return retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(5))
