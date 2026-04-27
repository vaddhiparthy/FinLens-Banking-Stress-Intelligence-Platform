from datetime import datetime

from airflow.operators.bash import BashOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_ingest_qbp",
    start_date=datetime(2026, 4, 23),
    schedule="0 3 1 */3 *",
    catchup=False,
    default_args=default_args,
) as dag:
    BashOperator(
        task_id="ingest_qbp",
        bash_command=(
            "cd /opt/finlens && "
            "python scripts/run_local_pipeline.py --sources qbp --skip-warehouse"
        ),
    )
