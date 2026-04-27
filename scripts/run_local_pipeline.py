from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _source_list(raw: str | None) -> list[str] | None:
    from finlens.bootstrap import SOURCE_DEFINITIONS

    if raw is None:
        return None
    values = [item.strip().lower() for item in raw.split(",") if item.strip()]
    unknown = [item for item in values if item not in SOURCE_DEFINITIONS]
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise argparse.ArgumentTypeError(f"Unknown source key(s): {joined}")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate configured connectors and run the active FinLens local pipeline."
    )
    parser.add_argument(
        "--check-connectors",
        action="store_true",
        help="Validate active connectors and print readiness without running ingestion.",
    )
    parser.add_argument(
        "--sources",
        type=_source_list,
        help="Optional comma-separated source override (e.g. fdic,fred,qbp,nic).",
    )
    parser.add_argument(
        "--skip-warehouse",
        action="store_true",
        help="Skip rebuilding the local DuckDB demo warehouse after ingestion.",
    )
    parser.add_argument(
        "--start-streamlit",
        action="store_true",
        help="Start the Streamlit app after ingestion and warehouse bootstrap.",
    )
    parser.add_argument(
        "--allow-missing-connectors",
        action="store_true",
        help="Run only ready enabled sources instead of failing on missing optional connectors.",
    )
    parser.add_argument(
        "--streamlit-port",
        type=int,
        default=8501,
        help="Port to use when starting Streamlit. Default: 8501.",
    )
    return parser


def _print_connector_report(selected_sources: list[str] | None) -> None:
    from finlens.bootstrap import save_connector_report, source_checks
    from finlens.config import get_settings

    settings = get_settings()
    checks = source_checks(settings, selected_sources=selected_sources)
    save_connector_report(checks)
    print("FinLens connector report")
    print("------------------------")
    print(f"Active sources: {', '.join(selected_sources or settings.active_source_list)}")
    for check in checks:
        if not check.enabled:
            continue
        missing = ", ".join(check.missing_env) if check.missing_env else "-"
        print(
            f"{check.key:<4} status={check.status:<18} "
            f"cadence={check.cadence:<10} missing={missing}"
        )


def _ready_sources(selected_sources: list[str] | None) -> list[str]:
    from finlens.bootstrap import source_checks
    from finlens.config import get_settings

    checks = source_checks(get_settings(), selected_sources=selected_sources)
    return [check.key for check in checks if check.enabled and check.ready]


def _start_streamlit(port: int) -> int:
    from finlens.logging import get_logger

    logger = get_logger(__name__)
    app_path = REPO_ROOT / "streamlit_app" / "app.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
    ]
    logger.info("start_streamlit", command=" ".join(command))
    return subprocess.call(command)


def main() -> None:
    from finlens.bootstrap import run_active_sources
    from finlens.logging import get_logger
    from finlens.warehouse import initialise_local_duckdb

    logger = get_logger(__name__)
    args = build_parser().parse_args()
    selected_sources = args.sources
    report_sources = selected_sources

    _print_connector_report(selected_sources)
    if args.check_connectors:
        return

    if args.allow_missing_connectors:
        selected_sources = _ready_sources(selected_sources)

    logger.info("run_active_sources", selected_sources=selected_sources)
    results = run_active_sources(selected_sources=selected_sources)
    if args.allow_missing_connectors:
        _print_connector_report(report_sources)
    print(f"Completed source runs: {', '.join(results) if results else '(none)'}")

    if not args.skip_warehouse:
        logger.info("run_local_warehouse")
        db_path = initialise_local_duckdb()
        print(f"Local warehouse ready at: {db_path}")

    if args.start_streamlit:
        raise SystemExit(_start_streamlit(args.streamlit_port))


if __name__ == "__main__":
    main()
