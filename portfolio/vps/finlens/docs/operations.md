# Operations

FinLens is structured to behave like a small production data platform.

## Local Operations

Start the presentation app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_finlens.ps1
```

Start the API service:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_api.ps1
```

## Health

Local health surfaces:

- Streamlit: `http://127.0.0.1:8501`
- API health: `http://127.0.0.1:8010/health`
- Uptime-style health: `http://127.0.0.1:8010/healthz`

## Secrets

Secrets are not committed. Use `.env`, local secret stores, deployment secret managers, or CI/CD secret mechanisms.

## Production Presentation

Public project page:

- <https://surya.vaddhiparthy.com/finlens/>

The public page is the recruiter-facing presentation surface. This repository remains the engineering evidence behind that surface.
