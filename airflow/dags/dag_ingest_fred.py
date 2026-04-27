from datetime import datetime

from airflow.operators.bash import BashOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_ingest_fred",
    start_date=datetime(2026, 4, 23),
    schedule="@hourly",
    catchup=False,
    default_args=default_args,
) as dag:
    BashOperator(
        task_id="ingest_fred",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/run_local_pipeline.py "
            "--sources fred --skip-warehouse"
        ),
    )
