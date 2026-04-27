# FinLens Build State

## Current Checkpoint

The project is aligned to the resume-grade stack:

- AWS S3
- Airflow
- dbt
- Terraform
- Snowflake
- FastAPI
- Streamlit
- Cloudflare
- Postgres control-plane sync

Target public domain:

- `https://finlens.vaddhiparthy.vip`

## Active Product Scope

Business Surface:

- `Stress Pulse`
- `Failure Forensics`
- `Macro Transmission`

Technical Surface:

- `Live Pipeline Status`
- `Reconciliation`
- `Data Quality`
- `Architecture Decisions`

The Architecture Decisions tab now acts as the internal data architecture handbook. It emphasizes
S3 bronze storage, Airflow orchestration, dbt modeling, Snowflake warehouse design, Terraform
provisioning, data quality, source contracts, lineage, glossary, and official reference links.

## Active Source Scope

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

## Runtime Status

- Streamlit is live at `https://finlens.vaddhiparthy.vip`.
- FastAPI health is live at `https://finlens-api.vaddhiparthy.vip/healthz`.
- Uptime Kuma is live at `https://uptime.vaddhiparthy.vip`.
- FDIC ingest is populated.
- FRED ingest is populated.
- QBP and NIC are intentionally surfaced as connector gaps until compatible source contracts are supplied.
- Stress Pulse shows a pending-source state in live mode instead of synthetic aggregate values.
- WireGuard connects the Hetzner VPS to the home private network with split-tunnel routes only.
- Postgres control-plane sync is configured against the `finlens` schema.

## Remaining Optional Inputs

- `FDIC_QBP_SOURCE_URL`
- `NIC_CURRENT_PARENT_SOURCE_URL`
- Cloudflare Turnstile values if form protection is enabled later

## Dormant Features

- `Stress Lab` via `STRESS_LAB_ENABLED = False`
- sidebar / hamburger via `SIDEBAR_ENABLED = False`

## Verification Baseline

- `python -m ruff check .`
- `python -m pytest -q`
- `scripts/smoke_test.ps1`
