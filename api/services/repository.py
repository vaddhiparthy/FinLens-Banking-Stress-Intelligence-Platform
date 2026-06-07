from __future__ import annotations

from finlens.warehouse import read_table

# Reads the real Gold warehouse only. If a table is missing it returns an empty result —
# never demo / synthetic data.


def list_failures() -> list[dict]:
    try:
        return read_table("marts.fct_bank_failures").to_dict(orient="records")
    except Exception:  # noqa: BLE001
        return []


def get_bank(bank_id: str) -> dict | None:
    for row in list_failures():
        if row["bank_id"] == bank_id:
            return row
    return None


def get_metrics(series_id: str) -> list[dict]:
    try:
        rows = read_table("marts.fct_financial_metrics").to_dict(orient="records")
    except Exception:  # noqa: BLE001
        return []
    return [row for row in rows if row["series_id"] == series_id]
