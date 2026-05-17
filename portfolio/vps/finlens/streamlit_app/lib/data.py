from __future__ import annotations

import pandas as pd

from finlens.config import get_settings
from finlens.datasets import load_demo_bundle, load_demo_stress_pulse
from finlens.warehouse import read_table


def load_failures():
    try:
        frame = read_table("marts.fct_bank_failures")
    except Exception:
        if get_settings().finlens_data_mode == "live":
            return pd.DataFrame(
                columns=[
                    "bank_id",
                    "bank_name",
                    "city",
                    "state",
                    "cert",
                    "acquirer",
                    "closing_date",
                    "year",
                    "assets_millions",
                ]
            )
        frame = load_demo_bundle().failures

    frame = frame.copy()
    frame["year"] = frame["year"].astype(int)
    frame["assets_millions"] = frame["assets_millions"].astype(float)
    return frame


def load_metrics():
    try:
        frame = read_table("marts.fct_financial_metrics")
    except Exception:
        if get_settings().finlens_data_mode == "live":
            return pd.DataFrame(columns=["series_id", "date", "value", "metric_name"])
        frame = load_demo_bundle().metrics

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = frame["value"].astype(float)
    return frame


def load_acquirers():
    try:
        frame = read_table("marts.dim_acquirer")
    except Exception:
        if get_settings().finlens_data_mode == "live":
            return pd.DataFrame(
                columns=["acquirer", "decade", "failure_count", "assets_absorbed_millions"]
            )
        frame = load_demo_bundle().acquirers

    frame = frame.copy()
    frame["assets_absorbed_millions"] = frame["assets_absorbed_millions"].astype(float)
    return frame


def load_stress_pulse():
    try:
        frame = read_table("marts.fct_stress_pulse")
    except Exception:
        if get_settings().finlens_data_mode == "live":
            return pd.DataFrame(
                columns=[
                    "quarter",
                    "net_income",
                    "roa",
                    "nim",
                    "problem_banks",
                    "asset_yield",
                    "funding_cost",
                    "noncurrent_rate",
                    "nco_rate",
                    "afs_losses",
                    "htm_losses",
                ]
            )
        frame = load_demo_stress_pulse()

    frame = frame.copy()
    numeric_columns = [
        "net_income",
        "roa",
        "nim",
        "problem_banks",
        "asset_yield",
        "funding_cost",
        "noncurrent_rate",
        "nco_rate",
        "afs_losses",
        "htm_losses",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame
