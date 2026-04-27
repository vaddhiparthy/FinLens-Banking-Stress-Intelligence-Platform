COPY INTO FINLENS_RAW.PUBLIC.NIC_CURRENT_PARENT_RAW (raw_data, source_system, ingestion_timestamp, file_name)
FROM (
  SELECT
    PARSE_JSON($1),
    'nic',
    CURRENT_TIMESTAMP(),
    METADATA$FILENAME
  FROM @finlens_raw_stage/source=nic/
)
FILE_FORMAT = (TYPE = JSON);
