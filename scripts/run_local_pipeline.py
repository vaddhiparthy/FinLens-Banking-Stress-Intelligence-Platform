from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
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
        "--probe-platform",
        action="store_true",
        help="Run Airflow/dbt/S3/Snowflake/Postgres readiness probes and store the results.",
    )
    parser.add_argument(
        "--run-dbt-build",
        action="store_true",
        help="Run dbt build against the selected target after the local warehouse is ready.",
    )
    parser.add_argument(
        "--dbt-target",
        default="local",
        help="dbt target to use with --run-dbt-build. Default: local.",
    )
    parser.add_argument(
        "--sync-postgres",
        action="store_true",
        help="Sync telemetry and control-plane snapshots to Postgres after the run.",
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


def _run_dbt_build(target: str) -> dict:
    from finlens.state import save_state
    from finlens.warehouse import local_duckdb_path

    env = os.environ.copy()
    env["FINLENS_DUCKDB_PATH"] = str(local_duckdb_path())
    command = [
        "dbt",
        "build",
        "--project-dir",
        str(REPO_ROOT / "dbt"),
        "--profiles-dir",
        str(REPO_ROOT / "dbt"),
        "--target",
        target,
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = {
        "status": "Success" if completed.returncode == 0 else "Failed",
        "target": target,
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "captured_at": datetime.now(UTC).isoformat(),
    }
    save_state("dbt_build_report", payload)
    if completed.returncode != 0:
        raise RuntimeError(f"dbt build failed with return code {completed.returncode}")
    return payload


def main() -> None:
    from finlens.bootstrap import run_active_sources
    from finlens.logging import get_logger
    from finlens.pipeline_runs import PipelineRunRecorder
    from finlens.platform_probes import probe_platform_stack, summarize_probe
    from finlens.state import save_state
    from finlens.warehouse import initialise_local_duckdb

    logger = get_logger(__name__)
    args = build_parser().parse_args()
    selected_sources = args.sources
    report_sources = selected_sources
    recorder = PipelineRunRecorder("local_pipeline")

    recorder.record(
        "Connector readiness",
        lambda: _print_connector_report(selected_sources),
        detail=lambda _: "Connector report refreshed",
    )
    if args.check_connectors:
        recorder.finish()
        return

    if args.allow_missing_connectors:
        selected_sources = _ready_sources(selected_sources)

    logger.info("run_active_sources", selected_sources=selected_sources)
    results = recorder.record(
        "Source ingestion",
        lambda: run_active_sources(selected_sources=selected_sources),
        detail=lambda result: (
            f"Completed sources: {', '.join(result) if result else '(none)'}"
        ),
        metadata=lambda result: {"sources": list(result)},
    )
    if args.allow_missing_connectors:
        _print_connector_report(report_sources)
    print(f"Completed source runs: {', '.join(results) if results else '(none)'}")

    if not args.skip_warehouse:
        logger.info("run_local_warehouse")
        db_path = recorder.record(
            "DuckDB gold rebuild",
            initialise_local_duckdb,
            detail=lambda path: f"Local warehouse ready at {path}",
            metadata=lambda path: {"duckdb_path": str(path)},
        )
        print(f"Local warehouse ready at: {db_path}")

    if args.run_dbt_build:
        dbt_result = recorder.record(
            "dbt build",
            lambda: _run_dbt_build(args.dbt_target),
            detail=lambda result: (
                f"dbt build succeeded for target {result['target']}"
                if result["status"] == "Success"
                else f"dbt build failed for target {result['target']}"
            ),
            metadata=lambda result: result,
            allow_failure=True,
        )
        if dbt_result is not None:
            print(f"dbt build status: {dbt_result['status']}")

    if args.probe_platform:
        probes = recorder.record(
            "Platform probes",
            probe_platform_stack,
            detail=lambda result: "; ".join(
                summarize_probe(name, payload) for name, payload in result.items()
            ),
            metadata=lambda result: result,
            allow_failure=True,
        )
        if probes is not None:
            save_state("platform_probe_report", probes)
            print("Platform probes")
            print("----------------")
            for name, payload in probes.items():
                print(summarize_probe(name, payload))

    if args.sync_postgres:
        from scripts.sync_control_plane_to_postgres import sync

        sync_result = recorder.record(
            "Postgres control-plane sync",
            sync,
            detail=lambda result: (
                f"Synced {result['synced_events']} events to schema {result['schema']}"
            ),
            metadata=lambda result: result,
            allow_failure=True,
        )
        if sync_result is not None:
            print(f"Postgres sync complete: {sync_result}")

    recorder.finish()

    if args.start_streamlit:
        raise SystemExit(_start_streamlit(args.streamlit_port))


if __name__ == "__main__":
    main()
