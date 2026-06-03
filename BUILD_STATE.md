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

- `https://surya.vaddhiparthy.com/finlens/`

## Active Product Scope

Business Surface:

- `Stress Pulse`
- `Failure Forensics`
- `Macro Transmission`
- `Predictive Analytics` (live, model-backed: insert a bank, hold out a real failure, what-if)
- `Wiki`

Data Engineering Surface:

- `Live Pipeline`
- `Source Contracts`
- `Engineering Stack`
- `Data Quality`
- `Architecture Decisions`
- `Administration`
- `Wiki`

AI Engineering Surface (`pages/7_AI_Engineering.py`):

- `AI Pipeline`
- `Feature Contracts`
- `AI Stack`
- `Model Quality` (real out-of-time metrics, calibration, drift)
- `Model Decisions`
- `Administration`
- `AI Wiki`

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

- Streamlit is live at `https://surya.vaddhiparthy.com/finlens/`.
- FastAPI health is live at `https://finlens-api.vaddhiparthy.vip/healthz`.
- Uptime Kuma is live at `https://uptime.vaddhiparthy.vip`.
- FDIC ingest is populated.
- FRED ingest is populated.
- QBP and NIC source artifacts are populated when the compatible source URLs are configured.
- Stress Pulse uses live aggregate data when the QBP artifact is present and otherwise fails closed.
- WireGuard connects the Hetzner VPS to the home private network with split-tunnel routes only.
- Postgres control-plane sync is configured against the `finlens` schema.

## Remaining Optional Inputs

- Cloudflare Turnstile values if form protection is enabled later

## Dormant Features

- sidebar / hamburger via `SIDEBAR_ENABLED = False`
- (the fabricated `Stress Lab` demo was removed; replaced by the real model-backed
  Predictive Analytics tab and the AI Engineering surface)

## Verification Baseline

- `python -m ruff check .`
- `python -m pytest -q`
- `scripts/smoke_test.ps1`
