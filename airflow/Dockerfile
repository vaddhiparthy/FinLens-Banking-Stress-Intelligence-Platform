FROM apache/airflow:2.9.3-python3.11

COPY airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY src /opt/finlens/src
COPY ingestion /opt/finlens/ingestion
COPY dbt /opt/finlens/dbt
COPY scripts /opt/finlens/scripts

ENV PYTHONPATH=/opt/finlens/src:/opt/finlens
