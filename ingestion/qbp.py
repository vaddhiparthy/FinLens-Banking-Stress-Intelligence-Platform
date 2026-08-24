from __future__ import annotations

import hashlib
import html
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from finlens.config import get_settings
from finlens.http import build_session, get_bytes
from finlens.ingestion.base import IngestionTarget, build_storage_path
from finlens.logging import get_logger
from finlens.paths import RAW_DATA_DIR
from finlens.storage import write_bytes, write_json

LOGGER = get_logger(__name__)

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
QUARTER_PATTERN = re.compile(r"\d{4}Q[1-4]")
RELEASE_PATTERN = re.compile(
    r"""href=["']([^"']*quarterly-banking-profile-q([1-4])-(\d{4})[^"']*)["']""",
    re.IGNORECASE,
)
WORKBOOK_PATTERN = re.compile(
    r"""href=["']([^"']*qbp-time-series-spreadsheet[^"']*\.xlsx)["']""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QbpIngestionResult:
    artifact_path: Path
    metadata_path: Path
    source_url: str
    size_bytes: int


def _read_url(url: str) -> bytes:
    session = build_session()
    return get_bytes(session, url)


def _resolve_source(source_url: str) -> tuple[bytes, str]:
    parsed = urlparse(source_url)
    if parsed.scheme == "file":
        path = Path(parsed.path)
        return path.read_bytes(), source_url
    path = Path(source_url)
    if path.exists():
        return path.read_bytes(), str(path)
    if parsed.path.lower().endswith(".xlsx"):
        return _read_url(source_url), source_url

    page_url = source_url
    page = _read_url(page_url).decode("utf-8", errors="replace")
    workbook_matches = WORKBOOK_PATTERN.findall(page)
    if not workbook_matches:
        releases = []
        for href, quarter, year in RELEASE_PATTERN.findall(page):
            releases.append((int(year), int(quarter), urljoin(page_url, html.unescape(href))))
        if not releases:
            raise ValueError("FDIC QBP page did not expose a quarterly release link")
        _, _, page_url = max(releases)
        page = _read_url(page_url).decode("utf-8", errors="replace")
        workbook_matches = WORKBOOK_PATTERN.findall(page)
    if not workbook_matches:
        raise ValueError("FDIC QBP release did not expose its time-series workbook")
    workbook_url = urljoin(page_url, html.unescape(workbook_matches[0]))
    return _read_url(workbook_url), workbook_url


def _column_number(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        return 0
    result = 0
    for char in match.group(1):
        result = result * 26 + ord(char) - 64
    return result


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def _worksheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    sheets = workbook.find(f"{{{MAIN_NS}}}sheets")
    if sheets is None:
        return {}
    result: dict[str, str] = {}
    for sheet in sheets:
        target = targets[sheet.attrib[f"{{{REL_NS}}}id"]].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        if "/worksheets/" in target:
            result[sheet.attrib["name"]] = target
    return result


def _cell_value(cell: ET.Element, strings: list[str]) -> object:
    cell_type = cell.attrib.get("t")
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    raw = value_node.text if value_node is not None else None
    if cell_type == "s" and raw is not None:
        return strings[int(raw)]
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN_NS}}}is")
        return "" if inline is None else "".join(
            node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t")
        )
    return raw


def _read_sheet(
    archive: zipfile.ZipFile,
    path: str,
    strings: list[str],
) -> dict[int, dict[int, object]]:
    root = ET.fromstring(archive.read(path))
    sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
    rows: dict[int, dict[int, object]] = {}
    if sheet_data is None:
        return rows
    for row in sheet_data.findall(f"{{{MAIN_NS}}}row"):
        row_number = int(row.attrib["r"])
        values: dict[int, object] = {}
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            values[_column_number(cell.attrib.get("r", ""))] = _cell_value(cell, strings)
        rows[row_number] = values
    return rows


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _number(value: object) -> float | None:
    try:
        if value in (None, "", "N/A"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _quarter_columns(rows: dict[int, dict[int, object]]) -> dict[str, int]:
    candidates: list[dict[str, int]] = []
    for values in rows.values():
        candidate = {
            _text(value): column
            for column, value in values.items()
            if QUARTER_PATTERN.fullmatch(_text(value))
        }
        if candidate:
            candidates.append(candidate)
    if not candidates:
        raise ValueError("Worksheet has no quarterly header")
    return max(candidates, key=len)


def _find_row(rows: dict[int, dict[int, object]], label: str, *, start: int = 0) -> int:
    expected = _text(label).casefold()
    for row_number in sorted(rows):
        if row_number < start:
            continue
        if any(
            column <= 2 and _text(value).casefold() == expected
            for column, value in rows[row_number].items()
        ):
            return row_number
    raise ValueError(f"Required FDIC QBP label missing: {label}")


def _all_insured_metric_row(
    rows: dict[int, dict[int, object]],
    metric_label: str,
) -> int:
    metric_row = _find_row(rows, metric_label)
    for row_number in range(metric_row + 1, metric_row + 12):
        if any(
            column <= 2 and _text(value).casefold() == "all insured institutions"
            for column, value in rows.get(row_number, {}).items()
        ):
            return row_number
    raise ValueError(f"All Insured Institutions row missing for {metric_label}")


def _series(
    rows: dict[int, dict[int, object]],
    quarter_columns: dict[str, int],
    row_number: int,
) -> dict[str, float | None]:
    values = rows[row_number]
    return {quarter: _number(values.get(column)) for quarter, column in quarter_columns.items()}


def _normalize_qbp_workbook(payload: bytes) -> tuple[bytes, dict[str, object]]:
    try:
        archive = zipfile.ZipFile(BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("FDIC QBP source is not a valid XLSX workbook") from exc
    with archive:
        strings = _shared_strings(archive)
        paths = _worksheet_paths(archive)
        required_sheets = {
            "Balance Sheet",
            "Loan Performance",
            "Quarterly Income",
            "Ratios by Asset Size Groups",
        }
        missing = required_sheets - paths.keys()
        if missing:
            raise ValueError(f"FDIC QBP workbook missing sheets: {', '.join(sorted(missing))}")
        balance = _read_sheet(archive, paths["Balance Sheet"], strings)
        loans = _read_sheet(archive, paths["Loan Performance"], strings)
        income = _read_sheet(archive, paths["Quarterly Income"], strings)
        ratios = _read_sheet(archive, paths["Ratios by Asset Size Groups"], strings)

    quarter_columns = _quarter_columns(balance)
    quarters = sorted(quarter_columns)
    if len(quarters) < 4:
        raise ValueError("FDIC QBP workbook contains fewer than four quarters")
    for sheet_name, rows in {
        "Quarterly Income": income,
        "Loan Performance": loans,
        "Ratios by Asset Size Groups": ratios,
    }.items():
        sheet_quarters = _quarter_columns(rows)
        if set(sheet_quarters) != set(quarter_columns):
            raise ValueError(f"Quarter coverage differs in {sheet_name}")

    net_income = _series(
        income,
        _quarter_columns(income),
        _find_row(income, "Net income (loss) attributable to bank"),
    )
    total_assets = _series(balance, quarter_columns, _find_row(balance, "Total Assets"))
    total_deposits = _series(balance, quarter_columns, _find_row(balance, "Deposits"))
    total_equity = _series(balance, quarter_columns, _find_row(balance, "Total equity capital"))
    afs = _series(
        balance,
        quarter_columns,
        _find_row(balance, "Available for sale on non-equity securities unrealized gain/loss"),
    )
    htm = _series(
        balance,
        quarter_columns,
        _find_row(balance, "Held to maturity on non-equity securities unrealized gain/loss"),
    )
    ratio_quarters = _quarter_columns(ratios)
    roa = _series(
        ratios,
        ratio_quarters,
        _all_insured_metric_row(ratios, "Quarterly Return on Assets"),
    )
    nim = _series(
        ratios,
        ratio_quarters,
        _all_insured_metric_row(ratios, "Quarterly Net Interest Margin"),
    )
    asset_yield = _series(
        ratios,
        ratio_quarters,
        _all_insured_metric_row(ratios, "Quarterly Yield on Earning Assets"),
    )
    funding_cost = _series(
        ratios,
        ratio_quarters,
        _all_insured_metric_row(ratios, "Quarterly Cost of Funding Earning Assets"),
    )
    loan_quarters = _quarter_columns(loans)
    total_loans_row = _find_row(loans, "Total Loans & Leases")
    noncurrent = _series(
        loans,
        loan_quarters,
        _find_row(loans, "Noncurrent rate", start=total_loans_row),
    )
    nco = _series(
        loans,
        loan_quarters,
        _find_row(loans, "Net charge-off rate", start=total_loans_row),
    )

    rows = []
    for quarter in quarters:
        rows.append(
            {
                "quarter": quarter,
                "net_income": None
                if net_income[quarter] is None
                else round(net_income[quarter] / 1000, 3),
                "roa": None if roa[quarter] is None else round(roa[quarter], 4),
                "nim": None if nim[quarter] is None else round(nim[quarter], 4),
                "problem_banks": None,
                "asset_yield": None
                if asset_yield[quarter] is None
                else round(asset_yield[quarter], 4),
                "funding_cost": None
                if funding_cost[quarter] is None
                else round(funding_cost[quarter], 4),
                "noncurrent_rate": None
                if noncurrent[quarter] is None
                else round(noncurrent[quarter] * 100, 4),
                "nco_rate": None if nco[quarter] is None else round(nco[quarter] * 100, 4),
                "afs_losses": None if afs[quarter] is None else round(afs[quarter] / 1000, 3),
                "htm_losses": None if htm[quarter] is None else round(htm[quarter] / 1000, 3),
                "total_assets": None
                if total_assets[quarter] is None
                else round(total_assets[quarter] / 1000, 3),
                "total_deposits": None
                if total_deposits[quarter] is None
                else round(total_deposits[quarter] / 1000, 3),
                "total_equity": None
                if total_equity[quarter] is None
                else round(total_equity[quarter] / 1000, 3),
                "source_code": "FDIC_QBP_TIME_SERIES",
            }
        )
    metadata = {
        "normalization_kind": "fdic_qbp_true_quarterly",
        "first_quarter": quarters[0],
        "last_quarter": quarters[-1],
        "quarter_count": len(quarters),
        "units": {
            "net_income": "USD billions",
            "total_assets": "USD billions",
            "total_deposits": "USD billions",
            "total_equity": "USD billions",
            "afs_losses": "USD billions",
            "htm_losses": "USD billions",
            "roa": "percent",
            "nim": "percent",
            "asset_yield": "percent",
            "funding_cost": "percent",
            "noncurrent_rate": "percent",
            "nco_rate": "percent",
        },
        "problem_banks_note": (
            "Not present in the FDIC QBP time-series workbook; retained as null."
        ),
    }
    return json.dumps(rows, indent=2).encode("utf-8"), metadata


def _preserve_annual_legacy() -> Path | None:
    legacy_dir = RAW_DATA_DIR / "source=qbp_annual_legacy"
    if next(legacy_dir.glob("ingestion_date=*/*.json"), None):
        return None
    source_dir = RAW_DATA_DIR / "source=qbp"
    manifests = [
        path
        for path in source_dir.glob("ingestion_date=*/*.json")
        if not path.name.endswith(".data.json")
    ]
    for manifest_path in sorted(manifests, key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact_path = Path(manifest["artifact_path"])
            payload = artifact_path.read_bytes()
            rows = json.loads(payload.decode("utf-8"))
        except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(rows, list) or not rows:
            continue
        if not all(re.fullmatch(r"\d{4}Q4", str(row.get("quarter", ""))) for row in rows):
            continue
        target = IngestionTarget.create("qbp_annual_legacy")
        legacy_artifact = write_bytes(build_storage_path(target, extension=".data.json"), payload)
        write_json(
            build_storage_path(target),
            {
                "source": "qbp_annual_legacy",
                "dataset": "fdic_banks_summary_annual_legacy",
                "preserved_at": datetime.now(UTC).isoformat(),
                "origin_manifest": str(manifest_path),
                "artifact_path": str(legacy_artifact),
                "row_count": len(rows),
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
        )
        return legacy_artifact
    return None


def ingest_fdic_qbp() -> QbpIngestionResult:
    settings = get_settings()
    settings.require("fdic_qbp_source_url")
    configured_url = settings.fdic_qbp_source_url or ""
    source_payload, resolved_url = _resolve_source(configured_url)
    normalized_payload, normalization_metadata = _normalize_qbp_workbook(source_payload)
    _preserve_annual_legacy()

    target = IngestionTarget.create("qbp")
    source_artifact_path = write_bytes(
        build_storage_path(target, extension=".source.xlsx"),
        source_payload,
    )
    artifact_path = write_bytes(
        build_storage_path(target, extension=".data.json"),
        normalized_payload,
    )
    metadata_path = write_json(
        build_storage_path(target),
        {
            "source": "qbp",
            "dataset": "fdic_quarterly_banking_profile",
            "ingested_at": datetime.now(UTC).isoformat(),
            "configured_source_url": configured_url,
            "source_url": resolved_url,
            "source_artifact_path": str(source_artifact_path),
            "source_sha256": hashlib.sha256(source_payload).hexdigest(),
            "artifact_path": str(artifact_path),
            "artifact_sha256": hashlib.sha256(normalized_payload).hexdigest(),
            "size_bytes": len(normalized_payload),
            **normalization_metadata,
        },
    )
    LOGGER.info(
        "qbp_ingestion_complete",
        artifact_path=str(artifact_path),
        metadata_path=str(metadata_path),
        source_url=resolved_url,
        size_bytes=len(normalized_payload),
    )
    return QbpIngestionResult(
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        source_url=resolved_url,
        size_bytes=len(normalized_payload),
    )


def main() -> None:
    print(asdict(ingest_fdic_qbp()))


if __name__ == "__main__":
    main()
