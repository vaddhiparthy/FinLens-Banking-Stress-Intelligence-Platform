from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from finlens.paths import RAW_DATA_DIR, ROOT_DIR
from finlens.state import load_state
from finlens.warehouse import local_duckdb_path


def source_landing_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_dir in sorted(RAW_DATA_DIR.glob("source=*")):
        source = source_dir.name.replace("source=", "")
        files = sorted(source_dir.glob("ingestion_date=*/*.json"))
        if not files:
            continue
        latest = max(files, key=lambda path: path.stat().st_mtime)
        payload = json.loads(latest.read_text(encoding="utf-8"))
        record_count = payload.get("record_count")
        if record_count is None and isinstance(payload.get("records"), list):
            record_count = len(payload["records"])
        artifact_path = payload.get("artifact_path")
        if record_count is None and artifact_path:
            artifact = Path(artifact_path)
            if not artifact.is_absolute():
                artifact = ROOT_DIR / artifact
            if artifact.exists() and artifact.suffix.lower() == ".json":
                artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
                if isinstance(artifact_payload, list):
                    record_count = len(artifact_payload)
        rows.append(
            {
                "Source": source.upper(),
                "Raw files": len(files),
                "Latest artifact": latest.name,
                "Latest record count": record_count if record_count is not None else "—",
                "Ingested at": payload.get("ingested_at", "—"),
                "Storage path": str(latest.relative_to(ROOT_DIR)),
            }
        )
    return rows


def warehouse_table_names() -> list[str]:
    import duckdb

    db_path = local_duckdb_path()
    if not db_path.exists():
        return []
    with duckdb.connect(str(db_path), read_only=True) as conn:
        rows = conn.execute(
            """
            select table_schema || '.' || table_name as table_ref
            from information_schema.tables
            where table_type = 'BASE TABLE'
              and table_schema not in ('information_schema', 'pg_catalog')
            order by table_schema, table_name
            """
        ).fetchall()
    return [row[0] for row in rows]


def warehouse_table_preview(table_ref: str, *, limit: int = 6, offset: int = 0) -> dict[str, Any]:
    import duckdb

    if table_ref not in warehouse_table_names():
        return {"rows": [], "columns": [], "total_rows": 0}
    schema, table = table_ref.split(".", 1)
    db_path = local_duckdb_path()
    with duckdb.connect(str(db_path), read_only=True) as conn:
        total_rows = conn.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0]
        frame = conn.execute(
            f'select * from "{schema}"."{table}" limit ? offset ?',
            [limit, offset],
        ).df()
    return {
        "rows": frame.to_dict(orient="records"),
        "columns": list(frame.columns),
        "total_rows": int(total_rows),
    }


def warehouse_table_rows() -> list[dict[str, Any]]:
    import duckdb

    db_path = local_duckdb_path()
    if not db_path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with duckdb.connect(str(db_path), read_only=True) as conn:
        tables = conn.execute(
            """
            select table_schema, table_name, table_type
            from information_schema.tables
            where table_type in ('BASE TABLE', 'VIEW')
              and table_schema not in ('information_schema', 'pg_catalog')
            order by table_schema, table_name
            """
        ).fetchall()
        # Map each DuckDB schema to its medallion layer rather than the old
        # "raw -> Bronze, everything-else -> Gold" rule that mislabelled staging/ml as Gold.
        layer_by_schema = {
            "raw": "Bronze / raw",
            "staging": "Silver / staging",
            "snapshots": "Silver / snapshots",
            "intermediate": "Intermediate",
            "marts": "Gold / mart",
            "ml": "ML feature store",
        }
        for schema, table, table_type in tables:
            count = conn.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0]
            column_count = conn.execute(
                """
                select count(*)
                from information_schema.columns
                where table_schema = ? and table_name = ?
                """,
                [schema, table],
            ).fetchone()[0]
            rows.append(
                {
                    "Layer": layer_by_schema.get(schema, schema),
                    "Object": "view" if table_type == "VIEW" else "table",
                    "Schema": schema,
                    "Table": table,
                    "Rows": int(count),
                    "Columns": int(column_count),
                }
            )
    return rows


def dbt_artifact_summary() -> dict[str, Any]:
    run_results_path = ROOT_DIR / "dbt" / "target" / "run_results.json"
    manifest_path = ROOT_DIR / "dbt" / "target" / "manifest.json"
    report = load_state("dbt_build_report", default={})
    report_summary = report.get("artifact_summary", {}) if isinstance(report, dict) else {}

    # When the live dbt artifact exists, count ONLY from it. Do NOT seed the counts from the
    # stored snapshot's artifact_summary: that snapshot is itself produced by this function, so
    # seeding from it makes each build accumulate on the previous one (the double-count bug).
    if run_results_path.exists():
        run_results = json.loads(run_results_path.read_text(encoding="utf-8"))
        manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest_path.exists()
            else {"nodes": {}}
        )
        nodes = manifest.get("nodes", {})
        models_success = tests_success = failures = total_nodes = 0
        for result in run_results.get("results", []):
            unique_id = result.get("unique_id", "")
            status = result.get("status")
            node = nodes.get(unique_id, {})
            resource_type = node.get("resource_type") or unique_id.split(".")[0]
            if status not in {"success", "pass"}:
                failures += 1
            if resource_type == "model" and status == "success":
                models_success += 1
            if resource_type == "test" and status == "pass":
                tests_success += 1
            total_nodes += 1
        generated_at = run_results.get("metadata", {}).get("generated_at")
        return {
            "build_status": "Success" if failures == 0 else "Failed",
            "target": (run_results.get("args", {}) or {}).get("target")
            or (report.get("target") if isinstance(report, dict) else None)
            or "local",
            "captured_at": generated_at
            or (report.get("captured_at", "—") if isinstance(report, dict) else "—"),
            "models_success": models_success,
            "tests_success": tests_success,
            "failures": failures,
            "total_nodes": total_nodes,
            "artifact_available": True,
        }

    # No live artifact (e.g. fresh deploy): fall back to the last recorded snapshot, clearly
    # carrying its own captured_at so the surface can label it as a prior run, not "now".
    return {
        "build_status": report_summary.get("build_status")
        or (report.get("status", "Unknown") if isinstance(report, dict) else "Unknown"),
        "target": report_summary.get("target")
        or (report.get("target", "—") if isinstance(report, dict) else "—"),
        "captured_at": report_summary.get("captured_at")
        or (report.get("captured_at", "—") if isinstance(report, dict) else "—"),
        "models_success": int(report_summary.get("models_success") or 0),
        "tests_success": int(report_summary.get("tests_success") or 0),
        "failures": int(report_summary.get("failures") or 0),
        "total_nodes": int(report_summary.get("total_nodes") or 0),
        "artifact_available": bool(report_summary.get("artifact_available", False)),
    }


def dbt_result_rows() -> list[dict[str, Any]]:
    run_results_path = ROOT_DIR / "dbt" / "target" / "run_results.json"
    manifest_path = ROOT_DIR / "dbt" / "target" / "manifest.json"
    if not run_results_path.exists():
        report = load_state("dbt_build_report", default={})
        stdout = str(report.get("stdout_tail", "")) if isinstance(report, dict) else ""
        rows: list[dict[str, Any]] = []
        for line in stdout.splitlines():
            clean = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            if " OK " not in clean and " PASS " not in clean:
                continue
            match = re.search(
                r"\b(?P<status>OK|PASS)\b\s+(?:created\s+)?(?:sql\s+)?"
                r"(?P<resource>incremental model|table model|view model|model|snapshot|test)?\s*"
                r"(?P<name>[A-Za-z0-9_.-]+)",
                clean,
            )
            if not match:
                continue
            status = match.group("status").lower()
            resource_type = match.group("resource") or ("test" if status == "pass" else "model")
            name = match.group("name")
            rows.append(
                {
                    "Resource type": resource_type,
                    "Name": name,
                    "Status": status,
                    "Execution seconds": "reported",
                    "Adapter response": "Parsed from latest dbt build report",
                }
            )
        return rows

    run_results = json.loads(run_results_path.read_text(encoding="utf-8"))
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"nodes": {}}
    )
    nodes = manifest.get("nodes", {})
    rows: list[dict[str, Any]] = []
    for result in run_results.get("results", []):
        unique_id = result.get("unique_id", "")
        node = nodes.get(unique_id, {})
        rows.append(
            {
                "Resource type": node.get("resource_type") or unique_id.split(".")[0],
                "Name": node.get("name") or unique_id,
                "Status": result.get("status", "unknown"),
                "Execution seconds": round(float(result.get("execution_time") or 0), 3),
                "Adapter response": result.get("adapter_response", {}).get("message", "—"),
            }
        )
    return rows


def airflow_run_rows() -> list[dict[str, Any]]:
    payload = load_state("airflow_run_report", default={})
    rows = payload.get("dag_runs", []) if isinstance(payload, dict) else []
    return rows if isinstance(rows, list) else []
