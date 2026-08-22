from datetime import datetime

from airflow.operators.bash import BashOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_ingest_nic",
    start_date=datetime(2026, 4, 23),
    # Refresh the current-institution reference on the quarterly FinLens cycle,
    # one hour before the QBP-triggered transform chain.
    schedule="0 2 1 3,6,9,12 *",
    catchup=False,
    default_args=default_args,
) as dag:
    BashOperator(
        task_id="ingest_nic",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/run_local_pipeline.py "
            "--sources nic --skip-warehouse"
        ),
    )
