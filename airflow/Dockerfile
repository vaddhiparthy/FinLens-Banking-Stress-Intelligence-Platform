FROM apache/airflow:3.4.0-python3.13@sha256:a8d9d19c563c768b2bc605ef26440f28a9164ea886064e99c599b057432ff572

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
    && VIRTUAL_ENV=/opt/finlens/.venv /opt/finlens/.venv/bin/uv sync --frozen --no-dev --active \
    && /opt/finlens/.venv/bin/pip uninstall -y uv setuptools wheel \
    && /opt/finlens/.venv/bin/pip uninstall -y pip \
    && python /tmp/fix_fab_moment_bundle.py \
    && rm /tmp/fix_fab_moment_bundle.py

ENV PYTHONPATH=/opt/finlens/src:/opt/finlens
ENV PATH=/opt/finlens/.venv/bin:${PATH}

ENV PYTHONDONTWRITEBYTECODE=1
RUN airflow config list --defaults > /opt/airflow/airflow.cfg     && chmod 0444 /opt/airflow/airflow.cfg
