# FinLens

FinLens is a resume-grade banking stress intelligence platform. The product is intentionally
small on the business side and deliberate on the engineering side: stable public data, explicit
source contracts, a Gold-layer dashboard boundary, and a technical surface that documents the
platform as an operational data system.

Target public domain:

- `https://surya.vaddhiparthy.com/finlens/`

## Active Product

Business Surface:

- `Stress Pulse`
- `Failure Forensics`
- `Macro Transmission`
- `Predictive Analytics` (planned)
- `Wiki`

Technical Surface:

- `Live Pipeline`
- `Source Contracts`
- `Engineering Stack`
- `Data Quality`
- `Architecture Decisions`
- `Administration`
- `Wiki`

Dormant:

- `Stress Lab`
- sidebar / hamburger navigation

## Resume Stack

The intended stack is:

- `AWS S3` for raw / bronze artifact storage
- `Airflow` for orchestration
- `dbt` for silver and gold transformations
- `Terraform` for cloud resource provisioning
- `Snowflake` for the warehouse target
- `FastAPI` for health, telemetry, and machine-facing endpoints
- `Streamlit` for the business and technical presentation surfaces
- `Cloudflare` for the public edge and optional Turnstile protection
- `Postgres` for home control-plane sync

The code is built so missing account values are reported as connector gaps instead of blocking
the local UI.

The `Architecture Decisions` tab in the technical surface is the in-app data architecture handbook.
It focuses on S3 zones, Airflow DAG design, dbt model contracts, Snowflake warehouse structure,
Terraform boundaries, quality strategy, and lineage rather than web-development internals.

## Source Policy

Approved active sources:

- `FDIC BankFind`
- `FDIC QBP`
- `FRED / ALFRED`
- `NIC` current parent metadata only

Removed from active scope:

- SEC / EDGAR
- FR Y-9C
- SLOOS
- UBPR
- Filing Surveillance
- active Stress Lab modeling

## Architecture Rule

Dashboards bind only to Gold-layer data contracts.

- Bronze preserves raw source payloads.
- Silver normalizes sources into project-owned canonical structures.
- Gold exposes dashboard-ready facts and metrics.
- Streamlit reads Gold, not raw source fields.

## Local Startup

Activate the environment:

```powershell
. .\scripts\use_finlens_env.ps1
```

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
- Uptime Kuma health check: `http://127.0.0.1:8010/healthz`

## Production Status

Production endpoint:

- `https://surya.vaddhiparthy.com/finlens/`

Operational endpoints:

- `https://finlens-api.vaddhiparthy.vip/healthz`
- `https://uptime.vaddhiparthy.vip`

Current live data posture:

- FDIC failed-bank ingestion is active and populated.
- FRED macro ingestion is active and populated.
- Bronze-to-Silver and Silver-to-Gold local marts are populated through DuckDB.
- QBP and NIC populate when compatible source contracts are configured.
- Stress Pulse uses live aggregate data when QBP is present and otherwise fails closed.

Cloud and platform wiring:

- AWS S3 bucket settings are configured through environment variables.
- Snowflake warehouse/database settings are configured through environment variables.
- Postgres control-plane sync uses the `finlens` schema.
- Cloudflare DNS routes the public app, API, and monitoring hostnames to the Hetzner VPS.

## Repository Layout

- `streamlit_app/` - active presentation layer
- `api/` - health and telemetry service
- `src/finlens/` - shared runtime configuration, state, telemetry, warehouse helpers
- `ingestion/` - active source clients for FDIC, FRED, QBP, and NIC
- `airflow/` - orchestration assets
- `dbt/` - transformation models
- `snowflake/` - warehouse DDL and load scaffolding
- `terraform/` - infrastructure scaffolding
- `docs/` - GitHub-style project documentation and ADRs
- `scripts/` - local startup, smoke, sync, and utility scripts
- `tests/` - automated validation

## Validation

```powershell
. .\scripts\use_finlens_env.ps1
python -m ruff check .
python -m pytest -q
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```
