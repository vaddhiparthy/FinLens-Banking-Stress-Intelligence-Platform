# Streamlit App

The active Streamlit product is split into two surfaces:

- business surface:
  - `Stress Pulse`
  - `Failure Forensics`
  - `Macro Transmission`
  - `Predictive Analytics`
  - `Wiki`
- technical surface:
  - `Live Pipeline`
  - `Source Contracts`
  - `Engineering Stack`
  - `Data Quality`
  - `Administration`
  - `Architecture Decisions`
  - `Wiki`

Dormant:
- `Stress Lab` remains in `streamlit_app/pages/3_Stress_Lab.py` behind a feature flag
- sidebar / hamburger navigation remains in code but disabled

Shared presentation logic lives in `streamlit_app/lib/`.

The Architecture Decisions and Wiki sections are the in-app data architecture handbook. Their main
emphasis is AWS S3, Airflow, dbt, Terraform, Snowflake, DuckDB, source contracts, lineage,
warehouse layering, and data quality strategy. Web and monitoring details are kept secondary.
