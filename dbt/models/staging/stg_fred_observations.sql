SELECT
  raw_data:series_id::VARCHAR AS metric_id_nk,
  raw_data:observations AS observations,
  source_system,
  ingestion_timestamp,
  file_name
FROM {{ source('raw', 'fred_observations_raw') }}
