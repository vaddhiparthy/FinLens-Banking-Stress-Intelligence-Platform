{{ config(materialized='incremental', unique_key=['series_id', 'date']) }}

SELECT
  series_id,
  date,
  value,
  metric_name
FROM {{ ref('stg_fred_observations') }}
