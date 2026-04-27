# FinLens

FinLens is a public-data banking stress intelligence platform built as an end-to-end data engineering system. The repository contains the ingestion clients, orchestration assets, transformation models, warehouse contracts, serving services, deployment configuration, and technical documentation required to operate the platform from source acquisition through dashboard delivery.

The implementation is intentionally organized around a governed data-platform pattern rather than a single dashboard script. Source payloads are acquired through explicit contracts, preserved in raw form, normalized into canonical structures, transformed into dashboard-ready marts, validated through runtime checks, and served through Streamlit and FastAPI behind a production reverse proxy.

Production application:

```text
https://surya.vaddhiparthy.com/finlens/
```

Health endpoint:

```text
https://finlens-api.vaddhiparthy.vip/healthz
```

## Architecture Overview

The platform follows a Bronze, Silver, Intermediate, and Gold pattern.

| Layer | Responsibility | Primary implementation |
|---|---|---|
| Source contracts | Define approved feeds, required configuration, cadence, and readiness | `src/finlens/bootstrap.py`, `src/finlens/config.py` |
| Bronze | Preserve source-shaped records and runtime artifacts | local `data/`, optional AWS S3 mirror |
| Silver | Normalize dates, names, identifiers, types, and source-specific shapes | dbt staging models and DuckDB export path |
| Intermediate | Hold reusable joins and business logic that should not be duplicated across marts | `dbt/models/intermediate/` |
| Gold | Publish dashboard-ready facts and metrics consumed by Streamlit and FastAPI | `dbt/models/marts/`, `src/finlens/warehouse.py` |
| Serving | Render human-facing and machine-facing interfaces over governed outputs | `streamlit_app/`, `api/` |
| Operations | Expose health, pipeline status, telemetry, source readiness, and sync status | FastAPI, Streamlit technical surface, Postgres sync |

The core rule is simple: presentation code reads Gold-layer contracts. It does not bind directly to raw source payloads or source-specific field names.

## Implemented Stack

| Tool | Role in FinLens | Repository location |
|---|---|---|
| Python | Source clients, runtime configuration, pipeline utilities, API services | `src/finlens/`, `ingestion/`, `scripts/`, `api/` |
| Streamlit | Business and technical presentation surfaces | `streamlit_app/` |
| FastAPI | Health, telemetry, and machine-readable platform endpoints | `api/` |
| DuckDB | Local analytical runtime and low-cost mart engine | `.duckdb/`, `duckdb/`, `src/finlens/warehouse.py` |
| dbt | Staging, intermediate, mart models, and structural tests | `dbt/` |
| Airflow | Scheduled ingestion, transformation, quality, and sync orchestration | `airflow/` |
| Snowflake | Cloud warehouse target and deployment-grade database contract | `snowflake/`, `dbt/profiles.yml` |
| AWS S3 | Optional raw artifact mirror for durable Bronze storage | `src/finlens/aws.py`, `terraform/` |
| Terraform | Infrastructure-as-code boundary for cloud storage resources | `terraform/` |
| Postgres | Control-plane and telemetry sync target | `scripts/sync_control_plane_to_postgres.py` |
| Docker Compose | Production runtime composition | `docker-compose.prod.yml` |
| Caddy | Reverse proxy and TLS termination | `deploy/Caddyfile` |
| Cloudflare | DNS and public edge routing | environment-driven deployment configuration |

## Data Sources

The active source set is deliberately constrained to public, stable sources.

| Source | Purpose | Runtime contract |
|---|---|---|
| FDIC BankFind failed-bank records | Failure inventory, timeline, geography, and acquirer context | `FDIC_FAILED_BANKS_URL` |
| FRED macroeconomic series | Macro context, indicator history, and lag exploration | `FRED_API_KEY`, `FRED_SERIES_IDS` |
| FDIC QBP aggregate banking data | Industry-level stress pulse metrics and reconciliation anchor | `FDIC_QBP_SOURCE_URL` |
| NIC current parent metadata | Current institution metadata and parent context | `NIC_CURRENT_PARENT_SOURCE_URL` |

The source policy excludes SEC EDGAR, FR Y-9C, SLOOS, UBPR, and filing surveillance from the active implementation. Those sources add identifier, schema, or semantic maintenance overhead that is not necessary for the current operating surface.

## Runtime Flow

The pipeline is designed so each stage produces inspectable evidence.

```text
FDIC / FRED / QBP / NIC
        |
        v
Bronze source artifacts
        |
        v
Silver canonical structures
        |
        v
Intermediate reusable models
        |
        v
Gold marts
        |
        v
Streamlit surfaces / FastAPI endpoints / Postgres sync
```

The technical surface exposes this flow through pipeline status rows, source activation state, warehouse table inventory, dbt result summaries, reconciliation tables, source landing records, and read-only table previews.

## Data Modeling

The dbt project is organized into reference, staging, intermediate, mart, and snapshot layers.

```text
dbt/
  models/
    reference/
      dim_date.sql
      dim_state.sql
    staging/
      stg_fdic_failed_banks.sql
      stg_fdic_qbp.sql
      stg_fred_observations.sql
      stg_nic_current_parent.sql
      sources.yml
    intermediate/
      int_failures_with_macro_context.sql
    marts/
      fct_bank_failures.sql
      fct_financial_metrics.sql
      fct_stress_pulse.sql
      schema.yml
  snapshots/
    dim_bank_snapshot.sql
```

The current mart contract supports:

- Failed-bank facts with cleaned names, dates, states, acquirer fields, asset values, and failure-year attributes.
- Financial and macro observations shaped for time-series rendering.
- Stress Pulse aggregates when QBP source data is available.
- Technical control-room surfaces that inspect pipeline artifacts and serving readiness.

## Orchestration

Airflow DAGs are included for scheduled operation of the same scripts used locally.

| DAG | Responsibility |
|---|---|
| `dag_ingest_fdic` | Acquire FDIC failed-bank records |
| `dag_ingest_fred` | Acquire configured FRED series |
| `dag_ingest_qbp` | Acquire QBP source artifact when configured |
| `dag_ingest_nic` | Acquire NIC current-parent metadata when configured |
| `dag_transform_and_quality` | Run transformation and quality steps |
| `dag_sync_control_plane` | Sync control-plane and telemetry records to Postgres |

The Airflow layer is not a separate business logic implementation. It calls the same project scripts so local, scheduled, and production execution paths remain aligned.

## Warehouse and Storage Strategy

FinLens supports two execution modes:

| Mode | Purpose |
|---|---|
| DuckDB local/runtime mode | Keeps the project testable and low-cost without requiring cloud warehouse execution for every read |
| Snowflake target mode | Provides the cloud warehouse contract for raw, staging, intermediate, and marts databases |

Snowflake DDL lives under:

```text
snowflake/
  ddl/
  load/
```

The Snowflake contract separates loading and transformation warehouses:

```text
FINLENS_LOADING_WH
FINLENS_TRANSFORMING_WH
```

The database layout mirrors the modeling lifecycle:

```text
FINLENS_RAW
FINLENS_STAGING
FINLENS_INTERMEDIATE
FINLENS_MARTS
```

AWS S3 is treated as the durable Bronze mirror. Local runtime data remains outside the Docker image and is mounted at runtime, which keeps container builds lean and prevents local source artifacts from being baked into public images.

## Serving Surfaces

The Streamlit application is divided into a business surface, a technical surface, and a shared knowledge bank.

Business surface:

- `Stress Pulse`
- `Failure Forensics`
- `Macro Transmission`
- `Predictive Analytics` planned surface
- `Wiki`

Technical surface:

- `Live Pipeline`
- `Source Contracts`
- `Engineering Stack`
- `Data Quality`
- `Architecture Decisions`
- `Administration`
- `Wiki`

Dormant surface:

- `Stress Lab`, controlled by `STRESS_LAB_ENABLED`

The technical surface is the primary engineering demonstration. It is designed to show source readiness, tool activation, pipeline status, transformation rules, dbt outcomes, warehouse inventory, reconciliation posture, source landing records, operational endpoints, and control-plane sync state.

## FastAPI Service

FastAPI provides the machine-facing control interface.

Current endpoints:

```text
/health
/healthz
/telemetry/events
/telemetry/summary
/failures
/metrics
```

The `/healthz` endpoint is used by monitoring and returns environment, data mode, stress-pulse mode, Postgres sync readiness, connector readiness, and pipeline status.

## Quality Controls

The quality strategy is split by responsibility.

| Control type | Owner | Purpose |
|---|---|---|
| Source readiness | Connector contracts | Verify required runtime configuration and source activation |
| Structural tests | dbt | Validate model-level assumptions such as not-null and accepted values |
| Reconciliation | Technical surface and runtime checks | Compare produced aggregates against external authority where definitions align |
| Pipeline status | `src/finlens/pipeline_status.py` | Normalize source, transformation, and serving states into one operational vocabulary |
| Read-only inspection | Interactive data browser | Preview table outputs without mutating data |
| Health checks | FastAPI | Provide service-level and connector-level monitoring output |

The project avoids presenting missing or inactive sources as successful. Disabled, missing, pending, and failed states are surfaced explicitly.

## Configuration

Secrets and environment-specific values are read through `finlens.config.Settings`.

Local secret values belong in `.env`; committed examples belong in `.env.example`.

Important configuration groups:

| Group | Variables |
|---|---|
| Source configuration | `FDIC_FAILED_BANKS_URL`, `FRED_API_KEY`, `FRED_SERIES_IDS`, `FDIC_QBP_SOURCE_URL`, `NIC_CURRENT_PARENT_SOURCE_URL` |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, bucket names |
| Snowflake | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, warehouses, databases |
| Postgres sync | `POSTGRES_SYNC_DSN`, `POSTGRES_SYNC_SCHEMA` |
| Public routes | `FINLENS_PUBLIC_BASE_URL`, `FINLENS_API_BASE_URL`, domain values |

No secret values should be committed to source control, markdown, SQL, shell history, or Docker build context.

## Repository Layout

```text
.
├── airflow/              # Airflow image, DAGs, and scheduler/webserver assets
├── api/                  # FastAPI service
├── dbt/                  # dbt models, tests, profiles, and snapshots
├── deploy/               # Caddy reverse proxy configuration
├── docs/                 # Repository documentation and architecture decisions
├── duckdb/               # DuckDB DDL and mart export utilities
├── ingestion/            # Source-specific ingestion clients
├── scripts/              # Local pipeline, smoke, startup, dbt, and sync utilities
├── snowflake/            # Snowflake DDL and load SQL
├── src/finlens/          # Shared application runtime package
├── streamlit_app/        # Streamlit application and surface modules
├── terraform/            # Infrastructure-as-code modules
├── tests/                # Automated validation
├── docker-compose.prod.yml
├── Dockerfile.streamlit
├── pyproject.toml
└── uv.lock
```

Generated runtime state is intentionally ignored:

```text
.env
.venv/
data/
.duckdb/
dbt/target/
dbt/logs/
__pycache__/
.pytest_cache/
.ruff_cache/
```

## Local Development

Install dependencies:

```powershell
uv sync
```

Load environment values:

```powershell
. .\scripts\use_finlens_env.ps1
```

Check connector readiness:

```powershell
python .\scripts\run_local_pipeline.py --check-connectors
```

Run the local pipeline:

```powershell
python .\scripts\run_local_pipeline.py
```

Start Streamlit:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_finlens.ps1
```

Start FastAPI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_api.ps1
```

Local URLs:

```text
Streamlit: http://127.0.0.1:8501
FastAPI:   http://127.0.0.1:8010
Health:    http://127.0.0.1:8010/healthz
```

## Production Runtime

Production is composed with Docker Compose.

Primary services:

| Service | Purpose |
|---|---|
| `finlens-streamlit-public` | Public Streamlit route under `/finlens/` |
| `finlens-streamlit` | Internal/root Streamlit service |
| `finlens-api` | FastAPI service |
| `finlens-control-postgres` | Control-plane sync database |
| `airflow-postgres` | Airflow metadata database |
| `airflow-webserver` | Airflow web UI |
| `airflow-scheduler` | Airflow scheduler |
| `uptime-kuma` | Monitoring UI |
| `caddy` | TLS and reverse proxy |

Runtime data is mounted into containers:

```text
./data    -> /app/data or /opt/finlens/data
./.duckdb -> /app/.duckdb or /opt/finlens/.duckdb
```

This design keeps the image build clean while preserving state across container restarts.

## Validation

Run the full local validation baseline:

```powershell
uv run ruff check streamlit_app src api scripts tests ingestion duckdb airflow
uv run python -m compileall streamlit_app src api scripts ingestion duckdb airflow
uv run pytest
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```

Expected test baseline:

```text
26 tests passing
```

Production verification:

```powershell
curl.exe -I -L https://surya.vaddhiparthy.com/finlens/
curl.exe -fsS https://finlens-api.vaddhiparthy.vip/healthz
```

## Design Principles

1. Presentation code binds to governed Gold outputs, not raw source payloads.
2. Source contracts are explicit and inspectable.
3. Missing connector values are reported as operational gaps, not hidden behind synthetic success.
4. Local execution remains possible without cloud spend.
5. Cloud warehouse and storage contracts remain present for deployment-grade operation.
6. Docker images do not bake in local runtime data or secrets.
7. Technical surfaces expose operating evidence instead of static screenshots.
8. Documentation describes implemented behavior and clearly marks planned work.

## Planned Extension

The planned predictive analytics surface will remain dormant until the model, scoring mart, coefficients, validation records, and interpretation guardrails are implemented. The intended design is to score observable public-data stress in a transparent Gold mart, not to publish supervisory ratings or failure predictions.

The intended implementation boundary is:

```text
public source data -> feature mart -> transparent model training -> coefficient artifact -> scored Gold mart -> Streamlit read-only surface
```

No runtime request path should train or execute the model directly. Scoring should be precomputed, versioned, and served as a governed mart.
