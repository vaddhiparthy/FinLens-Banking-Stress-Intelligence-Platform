from pathlib import Path

import ingestion.fred as fred


def test_fred_batch_uses_series_from_settings(monkeypatch) -> None:
    class StubSettings:
        fred_series_id_list = ["GDP", "UNRATE"]

    seen: list[str] = []
    monkeypatch.setattr(fred, "get_settings", lambda: StubSettings())
    monkeypatch.setattr(
        fred,
        "ingest_fred_series",
        lambda series_id: seen.append(series_id)
        or fred.FredSeriesResult(series_id, True, None, None),
    )

    results = fred.ingest_fred_series_batch()

    assert [result.series_id for result in results] == ["GDP", "UNRATE"]
    assert seen == ["GDP", "UNRATE"]


def test_fred_series_skips_when_watermark_matches(monkeypatch) -> None:
    monkeypatch.setattr(
        fred,
        "fetch_series_metadata",
        lambda series_id: {"id": series_id, "last_updated": "2026-04-22 00:00:00-05"},
    )
    monkeypatch.setattr(
        fred,
        "load_fred_watermarks",
        lambda: {"GDP": "2026-04-22 00:00:00-05"},
    )

    result = fred.ingest_fred_series("GDP")

    assert result.updated is False
    assert result.output_path is None


def test_fred_series_writes_payload_and_state(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        fred,
        "fetch_series_metadata",
        lambda series_id: {"id": series_id, "last_updated": "2026-04-23 00:00:00-05"},
    )
    monkeypatch.setattr(
        fred,
        "fetch_series_observations",
        lambda series_id: {"observations": [{"date": "2026-01-01", "value": "1.0"}]},
    )
    monkeypatch.setattr(fred, "load_fred_watermarks", lambda: {})
    monkeypatch.setattr(
        fred,
        "save_fred_watermarks",
        lambda watermarks: tmp_path / "watermarks.json",
    )
    monkeypatch.setattr(fred, "build_storage_path", lambda target: tmp_path / "fred.json")

    result = fred.ingest_fred_series("GDP")

    assert result.updated is True
    assert result.output_path == tmp_path / "fred.json"
