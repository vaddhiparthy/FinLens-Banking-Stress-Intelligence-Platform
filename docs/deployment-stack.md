# Deployment Stack

Target public application:

- `https://surya.vaddhiparthy.com/finlens/`

## Runtime Layers

| Layer | Tool | Responsibility |
|---|---|---|
| Edge | Cloudflare | DNS, optional proxying, Turnstile, branded domain |
| Presentation | Streamlit | Business and technical surfaces |
| API | FastAPI | Health, telemetry, and machine-facing status |
| Orchestration | Airflow | Scheduled ingestion, transforms, and sync |
| Raw storage | VPS local filesystem | `data/raw`, partitioned by source and ingestion date; one retained version per source via the rotation policy |
| Modeling | dbt | Silver and Gold transformation contracts |
| Warehouse | Snowflake | Resume-grade warehouse target |
| Infrastructure | Caddy + docker-compose.prod.yml on the VPS | Deployment and ingress (no infrastructure-as-code needed; no cloud resources to provision) |
| Control sync | Postgres | Home copy of telemetry and control-plane snapshots |

## Ready-To-Plug Posture

- FDIC ingestion runs locally now.
- FRED, QBP, and NIC are wired behind connector values and source contracts.
- Raw data is written to the VPS local filesystem under `data/raw` (partitioned by source and ingestion date), with one retained version per source enforced by `scripts/rotate_raw_data.py`.
- Airflow DAGs call the current bootstrap, transform, and sync scripts.
- dbt models reflect the approved source set.
- FastAPI exposes `/health`, `/healthz`, `/telemetry/events`, and `/telemetry/summary`.
- Postgres sync creates the target schema and tables when `POSTGRES_SYNC_DSN` is supplied.

## Current Production State

- Public app: `https://surya.vaddhiparthy.com/finlens/`
- Health endpoint: `https://finlens-api.vaddhiparthy.vip/healthz`
- Monitoring: `https://uptime.vaddhiparthy.vip`
- FDIC, FRED, QBP, and NIC source runs are populated when the corresponding source contracts are enabled.
- Runtime data is mounted into the production containers instead of being hard-coded into images.
- Caddy is the only public ingress path for application traffic.

## Monitoring

Uptime Kuma should watch:

- `https://finlens-api.vaddhiparthy.vip/healthz`
- `vpn.vaddhiparthy.vip`
- `192.168.100.100` over WireGuard
