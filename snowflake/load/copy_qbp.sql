COPY INTO FINLENS_RAW.PUBLIC.FDIC_QBP_RAW (raw_data, source_system, ingestion_timestamp, file_name)
FROM (
  SELECT
    PARSE_JSON($1),
    'qbp',
    CURRENT_TIMESTAMP(),
    METADATA$FILENAME
  FROM @finlens_raw_stage/source=qbp/
)
FILE_FORMAT = (TYPE = JSON);
