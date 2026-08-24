from pathlib import Path

import pytest

from ingestion import qbp


def test_resolve_source_discovers_newest_release_and_workbook(monkeypatch) -> None:
    release_url = (
        "https://www.fdic.gov/quarterly-banking-profile/"
        "quarterly-banking-profile-q1-2026"
    )
    workbook_url = (
        "https://www.fdic.gov/quarterly-banking-profile/"
        "qbp-time-series-spreadsheet-first-quarter-2026.xlsx"
    )
    pages = {
        "https://www.fdic.gov/quarterly-banking-profile": b"""
            <a href="/quarterly-banking-profile/quarterly-banking-profile-q4-2025">Q4</a>
            <a href="/quarterly-banking-profile/quarterly-banking-profile-q1-2026">Q1</a>
        """,
        release_url: (
            b'<a href="/quarterly-banking-profile/'
            b'qbp-time-series-spreadsheet-first-quarter-2026.xlsx">Data</a>'
        ),
        workbook_url: b"xlsx",
    }
    monkeypatch.setattr(qbp, "_read_url", pages.__getitem__)

    payload, url = qbp._resolve_source("https://www.fdic.gov/quarterly-banking-profile")

    assert payload == b"xlsx"
    assert url.endswith("qbp-time-series-spreadsheet-first-quarter-2026.xlsx")


def test_find_row_ignores_duplicate_chart_labels_outside_label_columns() -> None:
    rows = {
        90: {
            2: "Quarterly Yield on Earning Assets",
            20: "Quarterly Cost of Funding Earning Assets",
        },
        98: {2: "All Insured Institutions"},
        101: {2: "Quarterly Cost of Funding Earning Assets"},
        109: {2: "All Insured Institutions"},
    }

    assert qbp._find_row(rows, "Quarterly Cost of Funding Earning Assets") == 101
    assert qbp._all_insured_metric_row(rows, "Quarterly Cost of Funding Earning Assets") == 109


def test_invalid_workbook_is_rejected() -> None:
    with pytest.raises(ValueError, match="valid XLSX"):
        qbp._normalize_qbp_workbook(b"not a workbook")


def test_local_xlsx_source_is_read_without_network(tmp_path: Path, monkeypatch) -> None:
    workbook = tmp_path / "qbp.xlsx"
    workbook.write_bytes(b"local")
    monkeypatch.setattr(qbp, "_read_url", lambda _: pytest.fail("network access was used"))

    payload, source = qbp._resolve_source(str(workbook))

    assert payload == b"local"
    assert source == str(workbook)
