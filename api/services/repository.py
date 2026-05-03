from __future__ import annotations

from finlens.datasets import load_demo_bundle
from finlens.warehouse import read_table


def list_failures() -> list[dict]:
    try:
        return read_table("marts.fct_bank_failures").to_dict(orient="records")
    except Exception:
        return load_demo_bundle().failures.to_dict(orient="records")


def get_bank(bank_id: str) -> dict | None:
    for row in list_failures():
        if row["bank_id"] == bank_id:
            return row
    return None


def get_metrics(series_id: str) -> list[dict]:
    try:
        rows = read_table("marts.fct_financial_metrics").to_dict(orient="records")
    except Exception:
        rows = load_demo_bundle().metrics.to_dict(orient="records")
    return [row for row in rows if row["series_id"] == series_id]
