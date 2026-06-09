from datetime import datetime

from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_ingest_qbp",
    start_date=datetime(2026, 4, 23),
    schedule="0 3 1 */3 *",
    catchup=False,
    default_args=default_args,
) as dag:
    ingest = BashOperator(
        task_id="ingest_qbp",
        bash_command=(
            "cd /opt/finlens && "
            "/opt/finlens/.venv/bin/python scripts/run_local_pipeline.py "
            "--sources qbp --skip-warehouse"
        ),
    )
    # Quarterly chain: once fresh QBP financials land, rebuild the warehouse.
    # Model retraining is intentionally skipped (trained offline + committed).
    transform = TriggerDagRunOperator(
        task_id="trigger_transform",
        trigger_dag_id="dag_transform_and_quality",
        wait_for_completion=True,
        poke_interval=60,
        reset_dag_run=True,
    )
    ingest >> transform
