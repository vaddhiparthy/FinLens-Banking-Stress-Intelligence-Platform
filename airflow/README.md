# Airflow

The deployment uses the pinned official Airflow 3.3.1 Python 3.11 image with
LocalExecutor, PostgreSQL metadata, FAB authentication, a dedicated API server,
scheduler, and the required standalone DAG processor. Runtime package versions
are recorded in `requirements.txt`; they are supplied by the constrained
official image and are not reinstalled in a second dependency layer.
