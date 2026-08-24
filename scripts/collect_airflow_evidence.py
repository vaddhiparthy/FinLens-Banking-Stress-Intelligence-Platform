from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from finlens.state import save_state  # noqa: E402


def collect(metadata_dsn: str | None = None, connect=None) -> dict:
    dags = [
        "dag_ingest_fdic",
        "dag_ingest_fred",
        "dag_ingest_qbp",
        "dag_ingest_nic",
        "dag_sync_control_plane",
        "dag_transform_and_quality",
        "dag_ml_retrain",
    ]
    dsn = metadata_dsn or os.getenv("AIRFLOW_METADATA_DSN", "")
    if not dsn:
        raise RuntimeError("AIRFLOW_METADATA_DSN is required")
    if connect is None:
        import psycopg

        connect = psycopg.connect
    with connect(dsn, options="-c default_transaction_read_only=on") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                select distinct on (dag_id)
                    dag_id, run_id, state, start_date, end_date
                from dag_run
                where dag_id = any(%s)
                order by dag_id, logical_date desc nulls last, id desc
                """,
                (dags,),
            )
            latest_by_dag = {row[0]: row[1:] for row in cursor.fetchall()}

    rows: list[dict] = []
    for dag_id in dags:
        latest = latest_by_dag.get(dag_id)
        rows.append(
            {
                "DAG": dag_id,
                "Latest run": latest[0] if latest else "No run recorded",
                "State": latest[1] if latest else "No run recorded",
                "Started": latest[2].isoformat() if latest and latest[2] else "—",
                "Ended": latest[3].isoformat() if latest and latest[3] else "—",
            }
        )
    payload = {"captured_at": datetime.now(UTC).isoformat(), "dag_runs": rows}
    save_state("airflow_run_report", payload)
    return payload


def main() -> None:
    print(json.dumps(collect(), indent=2))


if __name__ == "__main__":
    main()
