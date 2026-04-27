from datetime import datetime

from airflow.operators.bash import BashOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_sync_control_plane",
    start_date=datetime(2026, 4, 23),
    schedule="*/30 * * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    BashOperator(
        task_id="sync_control_plane_to_postgres",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/sync_control_plane_to_postgres.py"
        ),
    )
