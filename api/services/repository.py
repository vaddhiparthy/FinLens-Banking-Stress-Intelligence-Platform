from __future__ import annotations

import math
from datetime import date, datetime
from numbers import Real

import pandas as pd

from finlens.datasets import load_demo_bundle
from finlens.warehouse import read_table


def _json_safe_value(value: object) -> object:
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, Real) and not math.isfinite(float(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_safe_value(item())
        except (TypeError, ValueError):
            pass
    return value


def _json_safe_records(frame: pd.DataFrame) -> list[dict]:
    return [
        {key: _json_safe_value(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def list_failures() -> list[dict]:
    try:
        frame = read_table("marts.fct_bank_failures")
    except Exception:
        frame = load_demo_bundle().failures
    return _json_safe_records(frame)


def get_bank(bank_id: str) -> dict | None:
    for row in list_failures():
        if row["bank_id"] == bank_id:
            return row
    return None


def get_metrics(series_id: str) -> list[dict]:
    try:
        frame = read_table("marts.fct_financial_metrics")
    except Exception:
        frame = load_demo_bundle().metrics
    return [row for row in _json_safe_records(frame) if row["series_id"] == series_id]
