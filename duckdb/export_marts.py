from pathlib import Path

import duckdb
from finlens.warehouse import initialise_local_duckdb, local_duckdb_path


def main() -> None:
    initialise_local_duckdb()
    output_dir = Path("data/marts")
    output_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(local_duckdb_path())) as conn:
        conn.execute(
            "copy marts.fct_bank_failures to "
            "'data/marts/fct_bank_failures.parquet' (format parquet)"
        )
        conn.execute(
            "copy marts.fct_financial_metrics to "
            "'data/marts/fct_financial_metrics.parquet' (format parquet)"
        )
        conn.execute(
            "copy marts.dim_acquirer to 'data/marts/dim_acquirer.parquet' (format parquet)"
        )


if __name__ == "__main__":
    main()
