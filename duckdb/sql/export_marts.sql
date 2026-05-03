COPY marts.fct_bank_failures TO 'data/marts/fct_bank_failures.parquet' (FORMAT PARQUET);
COPY marts.fct_financial_metrics TO 'data/marts/fct_financial_metrics.parquet' (FORMAT PARQUET);
COPY marts.dim_acquirer TO 'data/marts/dim_acquirer.parquet' (FORMAT PARQUET);
