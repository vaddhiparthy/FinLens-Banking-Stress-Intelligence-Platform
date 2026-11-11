"""Leakage-free discrete-time hazard labeling with proper censoring.

For each bank-quarter (CERT, quarter) we ask: does this institution FAIL within the
next H quarters? The label is strictly forward-looking and uses survival presence in
the panel as ground truth, which correctly censors healthy mergers/acquisitions
(they disappear from the panel without a failure record) and end-of-data (the last H
quarters cannot be confirmed and are dropped, never labeled negative).

Label rule for observation quarter q (ordinal), failure quarter f, last observed
quarter L for the bank, horizon H:
  - f exists and f <= q                      -> drop (bank already failed)
  - f exists and q < f <= q+H                -> 1 (fails within horizon)
  - f exists and f > q+H                      -> 0 (survives the horizon)
  - no failure and L >= q+H                   -> 0 (observed alive through horizon)
  - no failure and L <  q+H                   -> drop (right-censored: merger / data end)

Failures come from the FDIC failures API (CERT, FAILDATE, RESTYPE). RESTYPE=="FAILURE"
is a true closure; open-bank ASSISTANCE is excluded from the failure label by default.
No ``finlens.aws``/``boto3``/``snowflake`` imports ($0 invariant).
"""

from __future__ import annotations

import pandas as pd

from finlens.http import build_session, get_json

FDIC_FAILURES_URL = "https://api.fdic.gov/banks/failures"
_FAILURE_FIELDS = ["CERT", "FAILDATE", "RESTYPE", "NAME"]


def _quarter_ordinal_from_quarter(quarter: str) -> int:
    year, q = quarter.upper().split("Q")
    return int(year) * 4 + (int(q) - 1)


def _quarter_ordinal_from_date(ts: pd.Timestamp) -> int:
    return ts.year * 4 + (ts.quarter - 1)


def fetch_failures(records: list[dict] | None = None) -> pd.DataFrame:
    """Per-CERT first failure quarter (true closures only)."""
    if records is None:
        session = build_session(user_agent="finlens-ml/0.1 (research)")
        records = []
        offset, total = 0, None
        while total is None or len(records) < total:
            payload = get_json(
                session,
                FDIC_FAILURES_URL,
                params={
                    "fields": ",".join(_FAILURE_FIELDS),
                    "limit": 10000,
                    "offset": offset,
                    "format": "json",
                },
            )
            total = int(payload.get("meta", {}).get("total", 0))
            page = [r.get("data", r) for r in payload.get("data", [])]
            if not page:
                break
            records.extend(page)
            offset += len(page)
    if not records:
        return pd.DataFrame(columns=["cert", "fail_qord", "faildate", "restype"])
    frame = pd.DataFrame(records)
    frame["cert"] = pd.to_numeric(frame.get("CERT"), errors="coerce").astype("Int64")
    # FDIC FAILDATE is M/D/YYYY text; pin the format so an ambiguous date cannot
    # silently coerce to NaT and drop a true failure.
    frame["faildate"] = pd.to_datetime(
        frame.get("FAILDATE"), format="%m/%d/%Y", errors="coerce"
    )
    frame["restype"] = frame.get("RESTYPE")
    frame = frame[frame["restype"].astype(str).str.upper().eq("FAILURE")]
    frame = frame.dropna(subset=["cert", "faildate"])
    frame["fail_qord"] = frame["faildate"].map(_quarter_ordinal_from_date)
    # earliest failure per cert
    frame = frame.sort_values("fail_qord").drop_duplicates("cert", keep="first")
    return frame[["cert", "fail_qord", "faildate", "restype"]].reset_index(drop=True)


def attach_labels(
    panel: pd.DataFrame, failures: pd.DataFrame, horizon_q: int
) -> pd.DataFrame:
    """Attach a forward-looking failure label for the given horizon (in quarters).

    Adds columns: ``obs_qord``, ``label_<H>`` (0/1, NaN if not labelable),
    ``label_status_<H>`` (positive/negative/censored/already_failed).
    """
    if panel.empty:
        return panel
    out = panel.copy()
    out["obs_qord"] = out["quarter"].map(_quarter_ordinal_from_quarter)
    last_qord = out.groupby("cert")["obs_qord"].transform("max")

    fail_map = dict(zip(failures["cert"], failures["fail_qord"])) if not failures.empty else {}
    out["fail_qord"] = out["cert"].map(fail_map).astype("Float64")

    h = horizon_q
    label = pd.Series(pd.NA, index=out.index, dtype="Int64")
    status = pd.Series("censored", index=out.index, dtype="object")

    has_fail = out["fail_qord"].notna()
    f = out["fail_qord"]
    q = out["obs_qord"]

    already = has_fail & (f <= q)
    positive = has_fail & (f > q) & (f <= q + h)
    survived_fail = has_fail & (f > q + h)
    survived_nofail = (~has_fail) & (last_qord >= q + h)

    label[positive] = 1
    label[survived_fail | survived_nofail] = 0
    status[already] = "already_failed"
    status[positive] = "positive"
    status[survived_fail | survived_nofail] = "negative"

    out[f"label_{h}"] = label
    out[f"label_status_{h}"] = status
    out[f"labelable_{h}"] = label.notna()
    return out
