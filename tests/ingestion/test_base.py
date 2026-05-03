from datetime import date

from finlens.config import get_settings
from finlens.ingestion.base import IngestionTarget, build_s3_key, build_storage_path


def test_build_s3_key_uses_expected_partition_layout(monkeypatch) -> None:
    monkeypatch.setenv("AWS_S3_RAW_BUCKET", "finlens-raw")
    get_settings.cache_clear()
    target = IngestionTarget(
        source="fdic",
        ingestion_date=date(2026, 4, 23),
        object_id="unit-test",
    )

    try:
        assert (
            build_s3_key(target)
            == "s3://finlens-raw/source=fdic/ingestion_date=2026-04-23/unit-test.json"
        )
    finally:
        get_settings.cache_clear()


def test_build_storage_path_uses_dlq_directory_when_requested() -> None:
    target = IngestionTarget(
        source="fred",
        ingestion_date=date(2026, 4, 23),
        object_id="unit-test",
        dead_letter=True,
    )

    path = build_storage_path(target)

    assert path.parts[-5:] == (
        "data",
        "dlq",
        "source=fred",
        "ingestion_date=2026-04-23",
        "unit-test.json",
    )
