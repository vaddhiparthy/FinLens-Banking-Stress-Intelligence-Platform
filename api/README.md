# API

FastAPI is now the machine-facing layer for FinLens.

Current responsibilities:
- `/health`
- `/healthz`
- `/telemetry/events`
- `/telemetry/summary`

Intended uses:
- Uptime Kuma health monitoring
- machine-readable pipeline/control-plane checks
- telemetry capture and later sync into home Postgres

Local endpoint:
- `http://127.0.0.1:8010`

Deployment target:
- API endpoint behind the `finlens.vaddhiparthy.vip` deployment shape, either as a sibling
  service or as a separately routed API host.
