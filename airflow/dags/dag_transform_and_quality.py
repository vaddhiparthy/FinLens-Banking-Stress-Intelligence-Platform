from datetime import datetime

from airflow.operators.bash import BashOperator
from common import default_args

from airflow import DAG

with DAG(
    dag_id="dag_transform_and_quality",
    start_date=datetime(2026, 4, 23),
    schedule="0 4 * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/finlens/dbt && dbt build --profiles-dir . --target snowflake",
    )

    ge_checkpoint = BashOperator(
        task_id="ge_on_load",
        bash_command="python /opt/finlens/great_expectations/run_checkpoint.py on_load",
    )

    export_marts = BashOperator(
        task_id="export_marts",
        bash_command=(
            "cd /opt/finlens && "
            "python scripts/run_local_pipeline.py --sources fdic,fred,qbp,nic"
        ),
    )

    dbt_build >> ge_checkpoint >> export_marts
