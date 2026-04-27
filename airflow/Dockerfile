FROM apache/airflow:2.9.3-python3.11

COPY airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

USER root
RUN mkdir -p /opt/finlens && chown -R airflow:0 /opt/finlens

USER airflow
WORKDIR /opt/finlens

COPY --chown=airflow:0 pyproject.toml uv.lock README.md /opt/finlens/
COPY --chown=airflow:0 src /opt/finlens/src
COPY --chown=airflow:0 ingestion /opt/finlens/ingestion
COPY --chown=airflow:0 dbt /opt/finlens/dbt
COPY --chown=airflow:0 scripts /opt/finlens/scripts

RUN python -m venv /opt/finlens/.venv \
    && /opt/finlens/.venv/bin/pip install --no-cache-dir uv \
    && /opt/finlens/.venv/bin/uv pip install --python /opt/finlens/.venv/bin/python .

ENV PYTHONPATH=/opt/finlens/src:/opt/finlens
ENV PATH=/opt/finlens/.venv/bin:${PATH}
