from __future__ import annotations

from pathlib import Path
from typing import Any

from finlens.config import get_settings
from finlens.paths import ROOT_DIR


def probe_s3_configuration() -> dict[str, Any]:
    settings = get_settings()
    configured = bool(
        settings.aws_s3_mirror_enabled
        and settings.aws_access_key_id
        and settings.aws_secret_access_key
        and settings.aws_default_region
    )
    result: dict[str, Any] = {
        "configured": configured,
        "mirror_enabled": settings.aws_s3_mirror_enabled,
        "region": settings.aws_default_region,
        "raw_bucket": settings.aws_s3_raw_bucket,
        "marts_bucket": settings.aws_s3_marts_bucket,
    }
    if not configured:
        result["status"] = "Scaffolded"
        result["detail"] = "S3 mirror is not fully enabled for this runtime"
        return result

    try:
        import boto3

        client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )
        client.head_bucket(Bucket=settings.aws_s3_raw_bucket)
    except Exception as exc:
        result["status"] = "Failed"
        result["detail"] = str(exc)
        return result

    result["status"] = "Ready"
    result["detail"] = f"Raw bucket reachable: {settings.aws_s3_raw_bucket}"
    return result


def probe_dbt_project() -> dict[str, Any]:
    dbt_dir = ROOT_DIR / "dbt"
    model_files = sorted((dbt_dir / "models").glob("**/*.sql"))
    test_files = sorted((dbt_dir / "models").glob("**/*.yml"))
    result = {
        "status": "Ready" if model_files else "Missing",
        "model_count": len(model_files),
        "yaml_count": len(test_files),
        "project_path": str(dbt_dir),
        "detail": f"{len(model_files)} SQL models and {len(test_files)} YAML contracts found",
    }
    try:
        import dbt  # noqa: F401

        result["runtime"] = "dbt package importable"
    except Exception:
        result["runtime"] = "dbt package not installed in this runtime"
    return result


def probe_airflow_project() -> dict[str, Any]:
    dags_dir = ROOT_DIR / "airflow" / "dags"
    dags = sorted(path for path in dags_dir.glob("dag_*.py") if path.is_file())
    return {
        "status": "Ready" if dags else "Missing",
        "dag_count": len(dags),
        "dags": [path.stem for path in dags],
        "detail": f"{len(dags)} DAG definitions found",
    }


def probe_snowflake_connection() -> dict[str, Any]:
    settings = get_settings()
    configured = bool(
        settings.snowflake_account
        and settings.snowflake_user
        and settings.snowflake_password
        and settings.snowflake_role
    )
    result: dict[str, Any] = {
        "configured": configured,
        "account": settings.snowflake_account,
        "role": settings.snowflake_role,
        "warehouse": settings.snowflake_transforming_warehouse,
        "database": settings.snowflake_database_marts,
    }
    if not configured:
        result["status"] = "Scaffolded"
        result["detail"] = "Snowflake credentials are not fully configured for this runtime"
        return result

    try:
        import snowflake.connector
    except Exception:
        result["status"] = "Unavailable"
        result["detail"] = "snowflake-connector-python is not installed in this runtime"
        return result

    try:
        conn = snowflake.connector.connect(
            account=settings.snowflake_account,
            user=settings.snowflake_user,
            password=settings.snowflake_password,
            role=settings.snowflake_role,
            warehouse=settings.snowflake_transforming_warehouse,
            database=settings.snowflake_database_marts,
            schema="PUBLIC",
            login_timeout=20,
            network_timeout=20,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "select current_account(), current_role(), current_warehouse(), "
                    "current_database(), current_schema()"
                )
                row = cur.fetchone()
        finally:
            conn.close()
    except Exception as exc:
        result["status"] = "Failed"
        result["detail"] = str(exc)
        return result

    result.update(
        {
            "status": "Ready",
            "current_account": row[0] if row else None,
            "current_role": row[1] if row else None,
            "current_warehouse": row[2] if row else None,
            "current_database": row[3] if row else None,
            "current_schema": row[4] if row else None,
            "detail": "Snowflake session opened successfully",
        }
    )
    return result


def probe_postgres_sync() -> dict[str, Any]:
    settings = get_settings()
    result: dict[str, Any] = {
        "configured": bool(settings.postgres_sync_dsn),
        "schema": settings.postgres_sync_schema,
    }
    if not settings.postgres_sync_dsn:
        result["status"] = "Scaffolded"
        result["detail"] = "POSTGRES_SYNC_DSN is not configured"
        return result

    try:
        import psycopg

        with psycopg.connect(settings.postgres_sync_dsn, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
                cur.fetchone()
    except Exception as exc:
        result["status"] = "Failed"
        result["detail"] = str(exc)
        return result

    result["status"] = "Ready"
    result["detail"] = f"Postgres sync schema target: {settings.postgres_sync_schema}"
    return result


def probe_platform_stack() -> dict[str, Any]:
    return {
        "airflow": probe_airflow_project(),
        "dbt": probe_dbt_project(),
        "s3": probe_s3_configuration(),
        "snowflake": probe_snowflake_connection(),
        "postgres": probe_postgres_sync(),
    }


def summarize_probe(name: str, payload: dict[str, Any]) -> str:
    status = payload.get("status", "Unknown")
    detail = payload.get("detail", "")
    return f"{name}: {status}. {detail}".strip()


def local_path_exists(path: str | Path) -> bool:
    return Path(path).exists()
