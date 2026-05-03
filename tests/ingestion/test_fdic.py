from pathlib import Path

import ingestion.fdic as fdic


def test_build_failed_bank_payload_contains_metadata() -> None:
    payload = fdic.build_failed_bank_payload([{"Bank Name": "Example Bank"}])

    assert payload["source"] == "fdic"
    assert payload["dataset"] == "failed_bank_list"
    assert payload["record_count"] == 1


def test_fetch_failed_bank_rows_parses_csv(monkeypatch) -> None:
    monkeypatch.setattr(
        fdic,
        "get_text",
        lambda session, url: "Bank Name,State\nExample Bank,NC\nExample Bank 2,SC\n",
    )

    rows = fdic.fetch_failed_bank_rows()

    assert rows == [
        {"Bank Name": "Example Bank", "State": "NC"},
        {"Bank Name": "Example Bank 2", "State": "SC"},
    ]


def test_ingest_fdic_failed_banks_writes_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fdic, "fetch_failed_bank_rows", lambda: [{"Bank Name": "Example Bank"}])
    monkeypatch.setattr(fdic, "build_storage_path", lambda target: tmp_path / "fdic.json")

    result = fdic.ingest_fdic_failed_banks()

    assert result.record_count == 1
    assert result.output_path == tmp_path / "fdic.json"
