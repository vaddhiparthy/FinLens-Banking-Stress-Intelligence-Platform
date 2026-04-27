from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finlens.aws import upload_artifact_if_configured
from finlens.config import get_settings
from finlens.http import build_session, get_json
from finlens.ingestion.base import IngestionTarget, build_storage_path
from finlens.logging import get_logger
from finlens.state import load_state, save_state
from finlens.storage import write_json

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class FredSeriesResult:
    series_id: str
    updated: bool
    output_path: Path | None
    last_updated: str | None
    s3_uri: str | None = None


def _series_url(series_id: str) -> str:
    settings = get_settings()
    return f"{settings.fred_base_url}/series"


def _observations_url(series_id: str) -> str:
    settings = get_settings()
    return f"{settings.fred_base_url}/series/observations"


def _base_params(series_id: str) -> dict[str, str]:
    settings = get_settings()
    settings.require("fred_api_key")
    return {
        "api_key": settings.fred_api_key or "",
        "file_type": "json",
        "series_id": series_id,
    }


def fetch_series_metadata(series_id: str) -> dict[str, Any]:
    session = build_session()
    payload = get_json(session, _series_url(series_id), params=_base_params(series_id))
    series = payload.get("seriess", [])
    if not series:
        raise ValueError(f"No FRED metadata returned for series_id={series_id}")
    return dict(series[0])


def fetch_series_observations(series_id: str) -> dict[str, Any]:
    session = build_session()
    return get_json(session, _observations_url(series_id), params=_base_params(series_id))


def load_fred_watermarks() -> dict[str, str]:
    return load_state("fred_watermarks", default={})


def save_fred_watermarks(watermarks: dict[str, str]) -> Path:
    return save_state("fred_watermarks", watermarks)


def ingest_fred_series(series_id: str) -> FredSeriesResult:
    metadata = fetch_series_metadata(series_id)
    last_updated = metadata.get("last_updated")
    watermarks = load_fred_watermarks()

    if watermarks.get(series_id) == last_updated and last_updated is not None:
        LOGGER.info("fred_series_skipped", series_id=series_id, last_updated=last_updated)
        return FredSeriesResult(
            series_id=series_id,
            updated=False,
            output_path=None,
            last_updated=last_updated,
            s3_uri=None,
        )

    observations = fetch_series_observations(series_id)
    payload = {
        "source": "fred",
        "series_id": series_id,
        "ingested_at": datetime.now(UTC).isoformat(),
        "metadata": metadata,
        "observations": observations.get("observations", []),
    }

    target = IngestionTarget.create("fred")
    output_path = write_json(build_storage_path(target), payload)
    s3_uri = upload_artifact_if_configured(output_path, target)
    watermarks[series_id] = last_updated or datetime.now(UTC).isoformat()
    save_fred_watermarks(watermarks)
    LOGGER.info("fred_series_ingested", series_id=series_id, output_path=str(output_path))
    return FredSeriesResult(
        series_id=series_id,
        updated=True,
        output_path=output_path,
        last_updated=watermarks[series_id],
        s3_uri=s3_uri,
    )


def ingest_fred_series_batch(series_ids: list[str] | None = None) -> list[FredSeriesResult]:
    settings = get_settings()
    selected_series = series_ids or settings.fred_series_id_list
    return [ingest_fred_series(series_id) for series_id in selected_series]


def main() -> None:
    print([asdict(result) for result in ingest_fred_series_batch()])


if __name__ == "__main__":
    main()
