"""Deterministic tests for the discrete-time hazard labeling (no network)."""

from __future__ import annotations

import pandas as pd

from finlens_ml.labels import attach_labels


def _panel(certs_quarters: list[tuple[int, str]]) -> pd.DataFrame:
    return pd.DataFrame(certs_quarters, columns=["cert", "quarter"])


def _failures(rows: list[tuple[int, int]]) -> pd.DataFrame:
    # (cert, fail_qord)
    return pd.DataFrame(rows, columns=["cert", "fail_qord"])


def _qord(quarter: str) -> int:
    y, q = quarter.upper().split("Q")
    return int(y) * 4 + (int(q) - 1)


def test_positive_within_horizon_and_already_failed_dropped() -> None:
    # bank present 2008Q1..2008Q4, fails in 2008Q3 (qord of 2008Q3)
    fq = _qord("2008Q3")
    panel = _panel([(1, "2008Q1"), (1, "2008Q2"), (1, "2008Q3"), (1, "2008Q4")])
    out = attach_labels(panel, _failures([(1, fq)]), horizon_q=4)
    by_q = dict(zip(out["quarter"], out["label_status_4"]))
    assert by_q["2008Q1"] == "positive"  # fails in 2 quarters
    assert by_q["2008Q2"] == "positive"  # fails in 1 quarter
    # at/after failure quarter -> already failed, dropped (label NA)
    assert by_q["2008Q3"] == "already_failed"
    assert out.loc[out["quarter"] == "2008Q3", "label_4"].isna().all()


def test_survivor_observed_through_horizon_is_negative() -> None:
    # bank observed 2008Q1..2010Q1 (9 quarters), never fails
    quarters = [f"2008Q1", "2008Q2", "2008Q3", "2008Q4", "2009Q1", "2009Q2", "2009Q3", "2009Q4", "2010Q1"]
    panel = _panel([(2, q) for q in quarters])
    out = attach_labels(panel, _failures([]), horizon_q=4)
    by_q = dict(zip(out["quarter"], out["label_4"]))
    assert by_q["2008Q1"] == 0  # observed 4 quarters later -> survived
    # last 4 quarters cannot confirm horizon -> censored (NA)
    assert pd.isna(by_q["2009Q2"])
    assert pd.isna(by_q["2010Q1"])


def test_healthy_exit_is_censored_not_negative() -> None:
    # bank merges away after 2008Q3 (disappears), no failure record
    panel = _panel([(3, "2008Q1"), (3, "2008Q2"), (3, "2008Q3")])
    out = attach_labels(panel, _failures([]), horizon_q=4)
    # cannot observe 4 quarters ahead -> all censored, never labeled 0
    assert (out["label_status_4"] == "censored").all()
    assert out["label_4"].isna().all()


def test_failure_beyond_horizon_is_negative() -> None:
    fq = _qord("2010Q1")  # fails far in the future
    panel = _panel([(4, "2008Q1"), (4, "2008Q2"), (4, "2008Q3"), (4, "2008Q4"), (4, "2009Q1")])
    out = attach_labels(panel, _failures([(4, fq)]), horizon_q=4)
    # 2008Q1 + 4 = 2009Q1 < 2010Q1 fail -> survives this horizon -> negative
    assert out.loc[out["quarter"] == "2008Q1", "label_4"].iloc[0] == 0
