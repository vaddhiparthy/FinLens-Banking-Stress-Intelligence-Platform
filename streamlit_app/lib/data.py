from __future__ import annotations

import pandas as pd
import streamlit as st

from finlens.warehouse import read_table

# Single Gold-reading data-access module. Every loader reads the real warehouse; if a table is
# missing it returns an empty frame with the correct columns (an honest "no data" state).
# There is NO demo / mock / synthetic fallback anywhere — the UI shows real data or nothing.
#
# The DuckDB read is the expensive part, and Streamlit reruns the whole script on every
# interaction. We cache the raw table read (per table, 1h TTL, shared across sessions) so a
# page click does not re-query the warehouse; each loader returns a fresh .copy() so a page
# can never mutate the cached frame.


@st.cache_data(ttl=3600, show_spinner=False)
def _read_cached(table: str) -> pd.DataFrame:
    return read_table(table)


def load_failures():
    cols = ["bank_id", "bank_name", "city", "state", "cert", "acquirer",
            "closing_date", "year", "assets_millions"]
    try:
        frame = _read_cached("marts.fct_bank_failures").copy()
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=cols)
    frame["year"] = frame["year"].astype(int)
    frame["assets_millions"] = frame["assets_millions"].astype(float)
    return frame


def load_metrics():
    try:
        frame = _read_cached("marts.fct_financial_metrics").copy()
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["series_id", "date", "value", "metric_name"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = frame["value"].astype(float)
    return frame


def load_acquirers():
    try:
        frame = _read_cached("marts.dim_acquirer").copy()
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["acquirer", "decade", "failure_count",
                                     "assets_absorbed_millions"])
    frame["assets_absorbed_millions"] = frame["assets_absorbed_millions"].astype(float)
    return frame


def load_stress_pulse():
    cols = ["quarter", "net_income", "roa", "nim", "problem_banks", "asset_yield",
            "funding_cost", "noncurrent_rate", "nco_rate", "afs_losses", "htm_losses"]
    try:
        frame = _read_cached("marts.fct_stress_pulse").copy()
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=cols)
    for column in cols[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame
