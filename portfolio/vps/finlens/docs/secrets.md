# Secrets Reference

Secrets are local-only and must live in the root `.env` file or, later, GitHub Actions secrets.

No secret values belong in committed code, markdown, YAML, SQL, notebooks, or shell history.

## Active Variables

| Variable | Purpose | Used by |
|---|---|---|
| `FINLENS_ENVIRONMENT` | Runtime environment label | shared config |
| `ROOT_DOMAIN` | parent DNS zone, default `vaddhiparthy.vip` | deployment config |
| `PROJECT_DOMAIN` | primary project domain | deployment config |
| `FINLENS_PUBLIC_BASE_URL` | public Streamlit app URL | Streamlit / docs / health metadata |
| `FINLENS_API_BASE_URL` | public FastAPI URL if hosted separately | API links / telemetry |
| `FDIC_FAILED_BANKS_URL` | FDIC BankFind source URL | `ingestion/fdic.py` |
| `FRED_API_KEY` | FRED authentication | `ingestion/fred.py` |
| `FRED_BASE_URL` | FRED API base URL | `ingestion/fred.py` |
| `FRED_SERIES_IDS` | tracked series list | `ingestion/fred.py` |
| `FDIC_QBP_SOURCE_URL` | normalized QBP CSV/JSON artifact URL | `ingestion/qbp.py`, Stress Pulse |
| `NIC_CURRENT_PARENT_SOURCE_URL` | current-parent NIC artifact URL | `ingestion/nic.py` |
| `AWS_ACCESS_KEY_ID` | AWS programmatic identity | optional export/deployment work |
| `AWS_SECRET_ACCESS_KEY` | AWS programmatic secret | optional export/deployment work |
| `AWS_DEFAULT_REGION` | default AWS region | optional export/deployment work |
| `SNOWFLAKE_ACCOUNT` | Snowflake account locator | `snowflake`, `dbt` |
| `SNOWFLAKE_USER` | Snowflake username | `snowflake`, `dbt` |
| `SNOWFLAKE_PASSWORD` | Snowflake password | `snowflake`, `dbt` |
| `POSTGRES_SYNC_DSN` | home Postgres connection string | control-plane sync |
| `POSTGRES_SYNC_SCHEMA` | target schema for synced state | control-plane sync |
| `CLOUDFLARE_API_TOKEN` | DNS / deployment scripting | Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account identifier | Cloudflare |
| `CLOUDFLARE_ZONE_ID` | Cloudflare zone identifier | Cloudflare |
| `CLOUDFLARE_TURNSTILE_SITE_KEY` | public Turnstile key | telemetry / protection |
| `CLOUDFLARE_TURNSTILE_SECRET_KEY` | server-side Turnstile verification key | API telemetry |

## Local Usage

1. Keep `.env` in the repo root.
2. Keep `.env.example` committed with variable names only.
3. Load configuration through `finlens.config.get_settings()`.
