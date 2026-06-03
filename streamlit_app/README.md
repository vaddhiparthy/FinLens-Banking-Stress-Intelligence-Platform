# Streamlit App

The active Streamlit product is organized into three surfaces:

- business surface:
  - `Stress Pulse`
  - `Failure Forensics`
  - `Macro Transmission`
  - `Predictive Analytics` (live, model-backed: insert a bank, hold out a real failure, what-if)
  - `Wiki`
- data engineering surface (`pages/4_Under_The_Hood.py`):
  - `Live Pipeline`
  - `Source Contracts`
  - `Engineering Stack`
  - `Data Quality`
  - `Administration`
  - `Architecture Decisions`
  - `Wiki`
- AI engineering surface (`pages/7_AI_Engineering.py`), mirroring the data engineering flow:
  - `AI Pipeline`
  - `Feature Contracts`
  - `AI Stack`
  - `Model Quality` (real out-of-time metrics, calibration, drift)
  - `Model Decisions`
  - `Administration`
  - `AI Wiki`

Notes:
- sidebar / hamburger navigation remains in code but disabled
- the prior fabricated `Stress Lab` demo has been removed; the real model-backed
  Predictive Analytics tab and the AI surface replace it

Shared presentation logic lives in `streamlit_app/lib/`.

The Architecture Decisions and Wiki sections are the in-app data architecture handbook. Their main
emphasis is AWS S3, Airflow, dbt, Terraform, Snowflake, DuckDB, source contracts, lineage,
warehouse layering, and data quality strategy. Web and monitoring details are kept secondary.
