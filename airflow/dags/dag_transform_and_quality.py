from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from common import default_args

with DAG(
    dag_id="dag_transform_and_quality",
    start_date=datetime(2026, 4, 23),
    schedule="0 4 * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    BashOperator(
        task_id="run_ingestion_transform_quality",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/run_local_pipeline.py "
            "--skip-ingestion --run-dbt-build --probe-platform --sync-postgres"
        ),
    )
