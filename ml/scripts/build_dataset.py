"""Build the modeling dataset end-to-end and materialize it to DuckDB.

Pipeline: fetch per-CERT FDIC financials -> panel -> CAMELS features -> hazard
labels (H=4 and H=8) -> immutable DuckDB table ``ml.training_dataset``.

Run:  python ml/scripts/build_dataset.py --start 2008Q1 [--end 2025Q4]

$0: uses only the free FDIC API; no AWS/Snowflake. Macro (ALFRED vintage) is an
optional enhancement gated on a free FRED key and is intentionally NOT joined here
(latest-vintage macro would leak); the core model uses bank-level CAMELS features,
which the literature shows carry most of the signal (capital + earnings dominate).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "src", REPO / "ml"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def main() -> None:
    import duckdb

    from finlens_ml.config import get_ml_settings
    from finlens_ml.data import build_panel, load_financials_frame
    from finlens_ml.features import FEATURE_COLUMNS, build_features
    from finlens_ml.labels import attach_labels, fetch_failures

    from ingestion.fdic_institutions import fetch_financials

    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2008Q1")
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    print(f"[1/5] fetching FDIC financials {args.start}..{args.end or 'latest'}", flush=True)
    end = args.end or _latest_quarter()
    records = fetch_financials(args.start, end)
    print(f"      fetched {len(records):,} CERT-quarter rows", flush=True)

    print("[2/5] building panel", flush=True)
    panel = build_panel(load_financials_frame(records))

    print("[3/5] engineering features", flush=True)
    feats = build_features(panel)

    print("[4/5] labeling (H=4, H=8)", flush=True)
    failures = fetch_failures()
    feats = attach_labels(feats, failures, horizon_q=4)
    feats = attach_labels(feats, failures, horizon_q=8)

    print("[5/5] materializing ml.training_dataset", flush=True)
    settings = get_ml_settings()
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(settings.duckdb_path)) as conn:
        conn.execute("create schema if not exists ml")
        conn.register("ds", feats)
        conn.execute("create or replace table ml.training_dataset as select * from ds")
        n = conn.execute("select count(*) from ml.training_dataset").fetchone()[0]
        pos4 = conn.execute("select count(*) from ml.training_dataset where label_4=1").fetchone()[0]
        lab4 = conn.execute("select count(*) from ml.training_dataset where label_4 is not null").fetchone()[0]

    missing = [c for c in FEATURE_COLUMNS if c not in feats.columns]
    print(
        f"DONE: rows={n:,} certs={feats['cert'].nunique():,} "
        f"quarters={feats['quarter'].nunique()} | H4 labelable={lab4:,} positives={pos4:,} "
        f"base_rate={pos4 / lab4 * 100:.3f}% | missing_features={missing}",
        flush=True,
    )


def _latest_quarter() -> str:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    prior_q = (now.month - 1) // 3
    y, q = (now.year, prior_q) if prior_q >= 1 else (now.year - 1, 4)
    return f"{y}Q{q}"


if __name__ == "__main__":
    main()
