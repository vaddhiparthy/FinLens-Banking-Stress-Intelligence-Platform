# Data Model

The current FinLens data model is intentionally small and durable.

## Bronze

Raw source snapshots are stored unchanged, tagged with ingest metadata.

Approved Bronze domains:
- `fdic_bankfind`
- `fdic_qbp`
- `fred`
- `nic_current_parent`

## Silver

Silver normalizes provider payloads into canonical internal contracts.

Core Silver entities:
- `institution_current`
- `quarter`
- `failure_event`
- `macro_observation`
- `industry_aggregate`
- `pipeline_run`

## Gold

Gold is the only layer the UI reads from.

Current Gold contracts:
- `gold_stress_pulse_metrics`
- `gold_stress_pulse_timeseries`
- `gold_failure_forensics_summary`
- `gold_failure_forensics_events`
- `gold_macro_transmission_series`
- `gold_macro_transmission_lag_view`
- `gold_control_room_status`
- `gold_control_room_reconciliation`

## Rules

- no dashboard reads raw provider fields directly
- no threshold logic lives in UI code
- every displayed metric must have a source and as-of date

## Warehouse Target

The local runtime uses DuckDB for fast development and smoke testing. The resume-stack target is
Snowflake, with dbt owning the transformation contract between raw/staging/intermediate/mart
schemas. Streamlit should continue to read stable Gold outputs regardless of whether the backing
engine is local DuckDB or Snowflake.
