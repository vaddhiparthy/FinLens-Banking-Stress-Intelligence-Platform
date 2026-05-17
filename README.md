# FinLens: Banking Stress Intelligence Platform

FinLens is a public-data banking analytics platform built to demonstrate senior data engineering work: source ingestion, raw-to-curated data modeling, orchestration, quality checks, API health surfaces, and an analyst-facing dashboard.

Live presentation: <https://surya.vaddhiparthy.com/FinLens-Banking-Stress-Intelligence-Platform>

## What It Demonstrates

- Public financial data ingestion from FDIC, FRED/ALFRED, QBP, and NIC metadata sources
- Layered data design with Bronze, Silver, and Gold contracts
- dbt-style analytical modeling and dashboard-ready marts
- Airflow orchestration assets for repeatable pipeline execution
- Great Expectations checks for source and serving-layer validation
- FastAPI health and telemetry endpoints for machine-facing operations
- Streamlit business and technical surfaces for recruiters, analysts, and engineers
- Infrastructure scaffolding for S3, Snowflake, Terraform, Docker, and production deployment

## Architecture

```text
Public Sources
  -> ingestion clients
  -> raw landing / bronze artifacts
  -> normalized silver models
  -> gold analytical marts
  -> Streamlit dashboard + FastAPI health/telemetry
```

The dashboard binds to Gold-layer contracts rather than raw source fields. Raw payloads remain preserved for traceability, while the presentation layer reads curated facts and metrics.

Detailed docs:

- [Architecture](docs/architecture.md)
- [Data Flow](docs/data-flow.md)
- [Validation](docs/validation.md)
- [Operations](docs/operations.md)
- [Data Model](docs/data-model.md)
- [Deployment Stack](docs/deployment-stack.md)
- [Architecture Decision Records](docs/adr/README.md)

## Stack

| Layer | Tools |
| --- | --- |
| Language | Python, SQL |
| Ingestion | FDIC, FRED/ALFRED, QBP, NIC source clients |
| Orchestration | Airflow |
| Transformation | dbt-style SQL models, DuckDB, Snowflake scaffolding |
| Quality | Great Expectations, schema checks, smoke tests |
| Serving | Streamlit, FastAPI |
| Infrastructure | Docker, Terraform, S3-oriented landing zones |
| Operations | Health checks, connector readiness, structured project docs |

## Repository Layout

| Path | Purpose |
| --- | --- |
| `ingestion/` | Source clients for approved public datasets |
| `src/finlens/` | Shared configuration, state, telemetry, storage, and warehouse helpers |
| `dbt/` | Staging, intermediate, mart, and reference models |
| `airflow/` | DAGs and orchestration support |
| `great_expectations/` | Load and serving quality checks |
| `duckdb/` | Local mart DDL and export utilities |
| `snowflake/` | Warehouse DDL and load scaffolding |
| `api/` | FastAPI health, metrics, failure, and telemetry endpoints |
| `streamlit_app/` | Business dashboard and technical documentation UI |
| `terraform/` | Cloud infrastructure scaffolding |
| `docs/` | Architecture, data model, validation, operations, and ADRs |
| `tests/` | Unit and smoke coverage |

## Local Setup

Create or activate a Python environment, then install dependencies from the project metadata.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Copy the environment template if you want to configure optional connectors.

```powershell
Copy-Item .env.example .env
```

Secrets belong in `.env`, local secret stores, or deployment secret managers. They do not belong in committed code or docs.

## Run Locally

Check connector readiness:

```powershell
python .\scripts\run_local_pipeline.py --check-connectors
```

Start the Streamlit app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_finlens.ps1
```

Start the FastAPI service:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_api.ps1
```

Local URLs:

- Streamlit: `http://127.0.0.1:8501`
- FastAPI health: `http://127.0.0.1:8010/health`
- Uptime-style health check: `http://127.0.0.1:8010/healthz`

## Validation

```powershell
python -m ruff check .
python -m pytest -q
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

The smoke test validates imports, core chart generation, and demo stress-lab execution against the active local environment.

## Source Policy

Active source scope:

- FDIC BankFind
- FDIC QBP
- FRED / ALFRED
- NIC current parent metadata

Removed from active scope:

- SEC / EDGAR
- FR Y-9C
- SLOOS
- UBPR
- Filing surveillance
- Active Stress Lab modeling

Out-of-scope features are not documented as active product commitments.

## Production Posture

Production presentation:

- <https://surya.vaddhiparthy.com/FinLens-Banking-Stress-Intelligence-Platform>

Operational shape:

- Streamlit serves the business and technical interface.
- FastAPI exposes health and telemetry endpoints.
- DuckDB supports local Bronze/Silver/Gold mart materialization.
- S3, Snowflake, and Terraform scaffolds show the intended cloud operating model.

Missing account-specific connector values are surfaced as readiness gaps instead of being hidden or hardcoded.
