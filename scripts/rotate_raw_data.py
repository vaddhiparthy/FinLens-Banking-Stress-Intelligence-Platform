"""Retain one version of raw data per source on the VPS; purge older ingestion_date partitions.

The local pipeline calls this automatically after a run. Standalone usage:

    python scripts/rotate_raw_data.py             # keep the newest version per source, delete older
    python scripts/rotate_raw_data.py --keep 2    # keep the newest two
    python scripts/rotate_raw_data.py --dry-run   # report what would be deleted, delete nothing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _sub in ("", "src"):
    _p = str(REPO_ROOT / _sub) if _sub else str(REPO_ROOT)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from finlens.retention import rotate_raw_and_dlq  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", type=int, default=1,
                        help="versions to retain per source (default 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report without deleting")
    args = parser.parse_args()

    report = rotate_raw_and_dlq(keep=args.keep, dry_run=args.dry_run)
    verb = "would remove" if args.dry_run else "removed"
    total = 0
    for zone, rotations in report.items():
        for rot in rotations:
            total += len(rot.removed)
            removed = ", ".join(rot.removed) if rot.removed else "(none)"
            print(f"[{zone}] {rot.source}: kept {rot.kept} | {verb} {removed}")
    print(f"{'Would remove' if args.dry_run else 'Removed'} {total} stale partition(s).")


if __name__ == "__main__":
    main()
