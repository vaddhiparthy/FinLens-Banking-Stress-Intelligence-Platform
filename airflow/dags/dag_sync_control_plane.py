from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from airflow.timetables.trigger import CronTriggerTimetable
from common import default_args

import subprocess

TERMINAL_REPORT_COLLECTOR = 'import sys\nsys.path[:0] = ["/opt/finlens", "/opt/finlens/src"]\nimport os\nimport psycopg\nfrom scripts.collect_airflow_evidence import collect\ndsn = os.environ.get("AIRFLOW_METADATA_DSN") or os.environ.get("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", "")\nfor scheme in ("postgresql+psycopg2://", "postgresql+psycopg://"):\n    if dsn.startswith(scheme):\n        dsn = "postgresql://" + dsn[len(scheme):]\nif not dsn.startswith(("postgresql://", "postgres://")):\n    raise RuntimeError("Airflow metadata connection is missing or unsupported")\ndef bounded_read_connection(dsn, **kwargs):\n    kwargs["connect_timeout"] = 5\n    kwargs["options"] = kwargs.get("options", "") + " -c statement_timeout=10000 -c lock_timeout=2000"\n    return psycopg.connect(dsn, **kwargs)\ncollect(metadata_dsn=dsn, connect=bounded_read_connection)\n'

def refresh_terminal_airflow_report(context):
    dag = context.get("dag")
    if getattr(dag, "dag_id", None) != "dag_sync_control_plane" or not context.get("run_id"):
        raise ValueError("Terminal report refresh requires the control-sync run context")
    subprocess.run(
        ["/opt/finlens/.venv/bin/python", "-I", "-B", "-c", TERMINAL_REPORT_COLLECTOR],
        cwd="/opt/finlens",
        check=True,
    )

with DAG(
    dag_id="dag_sync_control_plane",
    start_date=datetime(2026, 8, 24),
    schedule=CronTriggerTimetable(
        "0 5 * * *",
        timezone="UTC",
        run_immediately=False,
    ),
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    on_success_callback=refresh_terminal_airflow_report,
    on_failure_callback=refresh_terminal_airflow_report,
    dagrun_timeout=timedelta(minutes=30),
) as dag:
    sync_control_plane = BashOperator(
        task_id="sync_control_plane_to_postgres",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/collect_airflow_evidence.py && "
            "/opt/finlens/.venv/bin/python scripts/sync_control_plane_to_postgres.py"
        ),
    )

    retain_control_plane = BashOperator(
        task_id="retain_control_plane_postgres",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/retain_control_plane_postgres.py "
            "--snapshot-days 90 --telemetry-days 365 --max-batch 500"
        ),
    )

    sync_control_plane >> retain_control_plane
