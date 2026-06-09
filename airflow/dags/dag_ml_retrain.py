"""Quarterly ML retraining + promotion DAG.

Mirrors a bank's retraining loop at $0: rebuild the point-in-time dataset, retrain +
calibrate the hazard model (logging to MLflow + setting the champion alias), then run the
model metric gate. If the gate fails, the new version is NOT promoted (the prior champion
alias stays — an auditable, reversible promotion). Quarterly cadence matches Call-Report
filing; a drift-threshold trigger can also fire this DAG from the monitoring job.
"""

from datetime import datetime

from airflow.operators.bash import BashOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_ml_retrain",
    start_date=datetime(2026, 4, 23),
    schedule=None,  # chain-triggered by the quarterly QBP -> transform pipeline
    catchup=False,
    default_args=default_args,
    tags=["ml", "retrain"],
) as dag:
    build = BashOperator(
        task_id="build_dataset",
        bash_command="cd /opt/finlens && /opt/finlens/.venv/bin/python ml/scripts/build_dataset.py --start 2008Q1",
    )
    train = BashOperator(
        task_id="train_and_register",
        bash_command="cd /opt/finlens && /opt/finlens/.venv/bin/python ml/finlens_ml/train.py --horizon 4",
    )
    gate = BashOperator(
        task_id="metric_gate",  # blocks promotion if the model regresses / shows leakage
        bash_command="cd /opt/finlens && /opt/finlens/.venv/bin/python ml/scripts/metric_gate.py",
    )
    export = BashOperator(
        task_id="export_web_data",
        bash_command="cd /opt/finlens && /opt/finlens/.venv/bin/python ml/scripts/export_web_data.py",
    )
    build >> train >> gate >> export
