USE DATABASE FINLENS_RAW;
USE SCHEMA PUBLIC;

CREATE TABLE IF NOT EXISTS FDIC_FAILED_BANKS_RAW (
  raw_data VARIANT,
  source_system VARCHAR,
  ingestion_timestamp TIMESTAMP_NTZ,
  file_name VARCHAR
);

CREATE TABLE IF NOT EXISTS FRED_OBSERVATIONS_RAW (
  raw_data VARIANT,
  source_system VARCHAR,
  ingestion_timestamp TIMESTAMP_NTZ,
  file_name VARCHAR
);

CREATE TABLE IF NOT EXISTS FDIC_QBP_RAW (
  raw_data VARIANT,
  source_system VARCHAR,
  ingestion_timestamp TIMESTAMP_NTZ,
  file_name VARCHAR
);

CREATE TABLE IF NOT EXISTS NIC_CURRENT_PARENT_RAW (
  raw_data VARIANT,
  source_system VARCHAR,
  ingestion_timestamp TIMESTAMP_NTZ,
  file_name VARCHAR
);
