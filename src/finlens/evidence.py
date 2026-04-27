from __future__ import annotations

import json
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
            select table_schema, table_name
            from information_schema.tables
            where table_type = 'BASE TABLE'
              and table_schema not in ('information_schema', 'pg_catalog')
            order by table_schema, table_name
            """
        ).fetchall()
        for schema, table in tables:
            count = conn.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0]
            column_count = conn.execute(
                """
                select count(*)
                from information_schema.columns
                where table_schema = ? and table_name = ?
                """,
                [schema, table],
            ).fetchone()[0]
            layer = "Bronze/raw" if schema == "raw" else "Gold mart"
            rows.append(
                {
                    "Layer": layer,
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
    summary: dict[str, Any] = {
        "build_status": report.get("status", "Unknown") if isinstance(report, dict) else "Unknown",
        "target": report.get("target", "—") if isinstance(report, dict) else "—",
        "captured_at": report.get("captured_at", "—") if isinstance(report, dict) else "—",
        "models_success": 0,
        "tests_success": 0,
        "failures": 0,
        "total_nodes": 0,
        "artifact_available": run_results_path.exists(),
    }
    if not run_results_path.exists():
        return summary

    run_results = json.loads(run_results_path.read_text(encoding="utf-8"))
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"nodes": {}}
    )
    nodes = manifest.get("nodes", {})
    for result in run_results.get("results", []):
        unique_id = result.get("unique_id", "")
        status = result.get("status")
        node = nodes.get(unique_id, {})
        resource_type = node.get("resource_type") or unique_id.split(".")[0]
        if status not in {"success", "pass"}:
            summary["failures"] += 1
        if resource_type == "model" and status == "success":
            summary["models_success"] += 1
        if resource_type == "test" and status == "pass":
            summary["tests_success"] += 1
        summary["total_nodes"] += 1
    return summary


def dbt_result_rows() -> list[dict[str, Any]]:
    run_results_path = ROOT_DIR / "dbt" / "target" / "run_results.json"
    manifest_path = ROOT_DIR / "dbt" / "target" / "manifest.json"
    if not run_results_path.exists():
        return []

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
