"""Raw-data rotation policy.

The VPS local filesystem is the Bronze landing zone (no cloud object store). Without a
retention policy the ``data/raw/source=*/ingestion_date=*`` tree grows one partition per run.
This module keeps exactly ``keep`` newest ``ingestion_date`` partitions per source (default 1)
and purges the rest, for both the raw and DLQ zones. ISO ``YYYY-MM-DD`` partition names sort
chronologically as text, so newest-first is a plain reverse string sort.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path

from finlens.logging import get_logger
from finlens.paths import DLQ_DATA_DIR, RAW_DATA_DIR

LOGGER = get_logger(__name__)


def _clear_readonly_and_retry(func, path, _exc):
    # On Windows a read-only file makes shutil.rmtree raise PermissionError;
    # clear the bit and retry.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _force_rmtree(path: Path) -> None:
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_clear_readonly_and_retry)
    else:  # pragma: no cover - onexc replaced onerror in 3.12
        shutil.rmtree(path, onerror=_clear_readonly_and_retry)


@dataclass
class SourceRotation:
    source: str
    kept: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


def _date_partitions(source_dir: Path) -> list[Path]:
    parts = [p for p in source_dir.glob("ingestion_date=*") if p.is_dir()]
    return sorted(parts, key=lambda p: p.name, reverse=True)  # newest ISO date first


def rotate_partitions(
    base_dir: Path, *, keep: int = 1, dry_run: bool = False
) -> list[SourceRotation]:
    """Retain the newest ``keep`` ingestion_date partitions per source under ``base_dir``."""
    if keep < 1:
        raise ValueError(
            "keep must be >= 1 (the policy always retains at least the latest version)"
        )
    results: list[SourceRotation] = []
    if not base_dir.exists():
        return results
    for source_dir in sorted(base_dir.glob("source=*")):
        if not source_dir.is_dir():
            continue
        rot = SourceRotation(source=source_dir.name.split("=", 1)[-1])
        for index, part in enumerate(_date_partitions(source_dir)):
            date_value = part.name.split("=", 1)[-1]
            if index < keep:
                rot.kept.append(date_value)
            else:
                rot.removed.append(date_value)
                if not dry_run:
                    _force_rmtree(part)
        results.append(rot)
        if rot.removed:
            LOGGER.info(
                "rotated_source", base=str(base_dir), source=rot.source,
                kept=rot.kept, removed=rot.removed, dry_run=dry_run,
            )
    return results


def rotate_raw_and_dlq(*, keep: int = 1, dry_run: bool = False) -> dict[str, list[SourceRotation]]:
    """Apply the rotation policy to both the raw landing zone and the DLQ zone."""
    return {
        "raw": rotate_partitions(RAW_DATA_DIR, keep=keep, dry_run=dry_run),
        "dlq": rotate_partitions(DLQ_DATA_DIR, keep=keep, dry_run=dry_run),
    }
