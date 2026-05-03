COPY INTO FINLENS_RAW.PUBLIC.FDIC_FAILED_BANKS_RAW (raw_data, source_system, ingestion_timestamp, file_name)
FROM (
  SELECT
    PARSE_JSON($1),
    'fdic',
    CURRENT_TIMESTAMP(),
    METADATA$FILENAME
  FROM @finlens_raw_stage/source=fdic/
)
FILE_FORMAT = (TYPE = JSON);
