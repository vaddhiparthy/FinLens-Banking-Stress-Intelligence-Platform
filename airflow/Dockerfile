FROM apache/airflow:3.4.0-python3.13@sha256:a8d9d19c563c768b2bc605ef26440f28a9164ea886064e99c599b057432ff572

USER root
RUN mkdir -p /opt/finlens && chown -R airflow:0 /opt/finlens

USER airflow
WORKDIR /opt/finlens

COPY --chown=airflow:0 pyproject.toml uv.lock README.md /opt/finlens/
COPY --chown=airflow:0 src /opt/finlens/src

# Use the existing component helpers when building worker or web images.
ARG FINLENS_AIRFLOW_ROLE=worker
COPY --chown=airflow:0 airflow/runtime_sources/${FINLENS_AIRFLOW_ROLE}/ /opt/finlens/src/
COPY --chown=airflow:0 ingestion /opt/finlens/ingestion
COPY --chown=airflow:0 dbt /opt/finlens/dbt
COPY --chown=airflow:0 scripts /opt/finlens/scripts
COPY --chown=airflow:0 airflow/fix_fab_moment_bundle.py /tmp/fix_fab_moment_bundle.py
COPY --chown=airflow:0 airflow/requirements.txt /tmp/airflow-platform-requirements.txt

RUN python -m pip --isolated install --user --no-deps --only-binary=:all: --no-cache-dir -r /tmp/airflow-platform-requirements.txt \
    && python -m pip --isolated check \
    && rm /tmp/airflow-platform-requirements.txt

RUN python -m venv /opt/finlens/.venv \
    && /opt/finlens/.venv/bin/pip install --no-cache-dir uv \
    && VIRTUAL_ENV=/opt/finlens/.venv /opt/finlens/.venv/bin/uv sync --frozen --no-dev --active \
    && python -m pip --isolated --python /opt/finlens/.venv/bin/python install --no-deps --only-binary=:all: --no-cache-dir 'boto3==1.44.2' 'botocore==1.44.2' 'dbt-core==1.12.7' 'fastapi==0.162.6' 'psycopg==3.3.9' 'psycopg-binary==3.3.9' \
    && python -m pip --isolated --python /opt/finlens/.venv/bin/python check \
    && /opt/finlens/.venv/bin/pip uninstall -y uv setuptools wheel \
    && /opt/finlens/.venv/bin/pip uninstall -y pip \
    && python /tmp/fix_fab_moment_bundle.py \
    && rm /tmp/fix_fab_moment_bundle.py

ENV PYTHONPATH=/opt/finlens/src:/opt/finlens
ENV PATH=/opt/finlens/.venv/bin:${PATH}

ENV PYTHONDONTWRITEBYTECODE=1
RUN airflow config list --defaults > /opt/airflow/airflow.cfg     && chmod 0444 /opt/airflow/airflow.cfg
