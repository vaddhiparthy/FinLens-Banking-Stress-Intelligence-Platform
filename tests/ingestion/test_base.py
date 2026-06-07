from datetime import date

from finlens.ingestion.base import IngestionTarget, build_storage_path


def test_build_storage_path_uses_expected_partition_layout() -> None:
    target = IngestionTarget(
        source="fdic",
        ingestion_date=date(2026, 4, 23),
        object_id="unit-test",
    )

    path = build_storage_path(target)

    assert path.parts[-5:] == (
        "data",
        "raw",
        "source=fdic",
        "ingestion_date=2026-04-23",
        "unit-test.json",
    )


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
