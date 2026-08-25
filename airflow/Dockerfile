FROM apache/airflow:3.3.1-python3.11@sha256:9417c2bba39de23e375f1fe98f284aee1561cedafd521edf1171b26c3b1e46e5

USER root
RUN mkdir -p /opt/finlens && chown -R airflow:0 /opt/finlens

USER airflow
WORKDIR /opt/finlens

COPY --chown=airflow:0 pyproject.toml uv.lock README.md /opt/finlens/
COPY --chown=airflow:0 src /opt/finlens/src
COPY --chown=airflow:0 ingestion /opt/finlens/ingestion
COPY --chown=airflow:0 dbt /opt/finlens/dbt
COPY --chown=airflow:0 scripts /opt/finlens/scripts
COPY --chown=airflow:0 airflow/fix_fab_moment_bundle.py /tmp/fix_fab_moment_bundle.py

RUN python -m venv /opt/finlens/.venv \
    && /opt/finlens/.venv/bin/pip install --no-cache-dir uv \
    && /opt/finlens/.venv/bin/uv pip install --python /opt/finlens/.venv/bin/python . \
    && python /tmp/fix_fab_moment_bundle.py \
    && rm /tmp/fix_fab_moment_bundle.py

ENV PYTHONPATH=/opt/finlens/src:/opt/finlens
ENV PATH=/opt/finlens/.venv/bin:${PATH}
