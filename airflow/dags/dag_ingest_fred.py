from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from common import default_args

with DAG(
    dag_id="dag_ingest_fred",
    start_date=datetime(2026, 4, 23),
    schedule="@daily",
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
