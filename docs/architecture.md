# Architecture

FinLens is organized as a layered analytical platform rather than a single dashboard script.

```text
Source APIs
  -> ingestion clients
  -> raw artifacts / Bronze
  -> normalized Silver tables
  -> Gold marts
  -> Streamlit dashboard
  -> FastAPI health and telemetry endpoints
```

## Design Principles

- Preserve raw source payloads before transformation.
- Normalize source-specific fields into project-owned structures.
- Expose dashboard data only through Gold-layer marts.
- Keep missing connector credentials visible as readiness gaps.
- Prefer reproducible local execution before cloud deployment.

## Runtime Surfaces

- `streamlit_app/` is the analyst and recruiter-facing presentation surface.
- `api/` is the machine-facing service surface for health, metrics, failures, and telemetry.
- `src/finlens/` contains shared configuration, state, storage, telemetry, and warehouse helpers.
- `airflow/` contains orchestration assets.
- `dbt/`, `duckdb/`, and `snowflake/` document the transformation and warehouse boundary.

## Deployment Boundary

The repository includes local-first execution paths and production-oriented scaffolding. Account-specific infrastructure, credentials, and runtime secrets are intentionally externalized.
