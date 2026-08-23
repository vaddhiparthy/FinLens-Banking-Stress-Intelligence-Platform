from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from airflow.timetables.trigger import CronTriggerTimetable
from common import default_args

with DAG(
    dag_id="dag_sync_control_plane",
    start_date=datetime(2026, 4, 23),
    schedule=CronTriggerTimetable(
        "0 5 * * *",
        timezone="UTC",
        run_immediately=False,
    ),
    catchup=False,
    default_args=default_args,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=30),
) as dag:
    sync_control_plane = BashOperator(
        task_id="sync_control_plane_to_postgres",
        bash_command=(
            "cd /opt/finlens && "
            "airflow dags list-runs dag_transform_and_quality --output json "
            ">/tmp/finlens_airflow_check.json && "
            "/opt/finlens/.venv/bin/python scripts/collect_airflow_evidence.py && "
            "/opt/finlens/.venv/bin/python scripts/sync_control_plane_to_postgres.py"
        ),
    )

    retain_control_plane = BashOperator(
        task_id="retain_control_plane_postgres",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/retain_control_plane_postgres.py "
            "--apply --snapshot-days 90 --telemetry-days 365 --max-batch 500"
        ),
    )

    sync_control_plane >> retain_control_plane

