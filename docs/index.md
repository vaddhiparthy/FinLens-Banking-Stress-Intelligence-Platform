# FinLens Documentation

FinLens is documented as a banking data platform with a small product surface and a deliberate
engineering backbone.

## Business Surface

- `Stress Pulse`
- `Failure Forensics`
- `Macro Transmission`

## Technical Surface

- `Live Pipeline Status`
- `Reconciliation`
- `Data Quality`
- `Architecture Decisions`

The Streamlit Architecture Decisions tab is the in-app knowledge surface. These markdown docs are
the repository-facing companion for code review, onboarding, and implementation history.

## Resume Stack

- AWS S3 for bronze artifacts
- Airflow for orchestration
- dbt for transformations
- Terraform for provisioning
- Snowflake for warehouse-grade modeling
- FastAPI for health and telemetry
- Streamlit for presentation
- Cloudflare for the `finlens.vaddhiparthy.vip` edge
- Postgres for home control-plane sync

## Active Source Policy

Approved:

- FDIC BankFind
- FDIC QBP
- FRED / ALFRED
- NIC current parent metadata only

Removed from active scope:

- SEC / EDGAR
- FR Y-9C
- SLOOS
- UBPR
- Filing Surveillance

## Architecture Contract

- Bronze: raw source preservation
- Silver: canonical normalized contracts
- Gold: dashboard-ready business metrics

Dashboards bind only to Gold.
