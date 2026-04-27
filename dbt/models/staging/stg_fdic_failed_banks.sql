SELECT
  raw_data:records AS records,
  raw_data:record_count::INTEGER AS record_count,
  source_system,
  ingestion_timestamp,
  file_name
FROM {{ source('raw', 'fdic_failed_banks_raw') }}
