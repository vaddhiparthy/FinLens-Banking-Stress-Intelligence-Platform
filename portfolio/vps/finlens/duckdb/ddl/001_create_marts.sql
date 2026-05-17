CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS marts.fct_bank_failures (
  bank_id VARCHAR,
  bank_name VARCHAR,
  state VARCHAR,
  year INTEGER,
  assets_millions DOUBLE,
  acquirer VARCHAR
);

CREATE TABLE IF NOT EXISTS marts.fct_financial_metrics (
  series_id VARCHAR,
  date DATE,
  value DOUBLE,
  metric_name VARCHAR
);

CREATE TABLE IF NOT EXISTS marts.dim_acquirer (
  acquirer VARCHAR,
  decade VARCHAR,
  assets_absorbed_millions DOUBLE
);
