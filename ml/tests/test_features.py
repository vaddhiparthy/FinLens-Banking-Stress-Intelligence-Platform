"""Tests for CAMELS feature engineering (deterministic, no network)."""

from __future__ import annotations

import pandas as pd

from finlens_ml.features import (
    FEATURE_COLUMNS,
    MONOTONE_CONSTRAINTS,
    add_level_features,
    add_trend_features,
    build_features,
)


def _panel() -> pd.DataFrame:
    rows = []
    for i in range(8):  # 8 quarters for one bank
        rows.append(
            {
                "cert": 1,
                "quarter": f"20{8 + i // 4:02d}Q{i % 4 + 1}",
                "repdte": pd.Timestamp("2008-03-31") + pd.DateOffset(months=3 * i),
                "ASSET": 1000.0 + 100 * i,
                "EQ": 100.0,
                "LNLSGR": 600.0,
                "LNLSNET": 580.0,
                "DEP": 800.0,
                "P9LNLS": 12.0 + i,
                "LNATRES": 10.0,
                "SC": 200.0,
                "CHBAL": 50.0,
                "BRO": 40.0,
                "ROA": 1.0 - 0.1 * i,
                "ROE": 9.0,
                "NIMY": 3.2,
                "EEFFR": 60.0,
                "NTLNLSR": 0.5,
                "RBC1RWAJ": 12.0,
                "RBCT1J": 95.0,
            }
        )
    return pd.DataFrame(rows)


def test_level_ratios_are_correct() -> None:
    out = add_level_features(_panel())
    # equity_to_assets at i=0: 100/1000*100 = 10.0
    assert abs(out.iloc[0]["equity_to_assets"] - 10.0) < 1e-6
    # noncurrent_to_loans at i=0: 12/600*100 = 2.0
    assert abs(out.iloc[0]["noncurrent_to_loans"] - 2.0) < 1e-6
    assert abs(out.iloc[0]["loans_to_deposits"] - (580 / 800 * 100)) < 1e-6


def test_safe_ratio_handles_zero_denominator() -> None:
    df = _panel()
    df.loc[0, "ASSET"] = 0.0
    out = add_level_features(df)
    assert pd.isna(out.iloc[0]["equity_to_assets"])  # no div-by-zero blowup


def test_trend_deltas_are_quarter_over_quarter() -> None:
    out = add_trend_features(add_level_features(_panel()))
    # asset grows by 100 each quarter from 1000; qoq pct at i=1 = 100/1000*100 = 10
    assert abs(out.sort_values("repdte").iloc[1]["asset_growth_qoq"] - 10.0) < 1e-6
    # yoy delta defined from i=4 onward
    assert pd.isna(out.sort_values("repdte").iloc[0]["roa_yoy_delta"])
    assert not pd.isna(out.sort_values("repdte").iloc[4]["roa_yoy_delta"])


def test_build_features_produces_all_model_columns() -> None:
    out = build_features(_panel())
    missing = [c for c in FEATURE_COLUMNS if c not in out.columns]
    assert not missing, f"missing model features: {missing}"


def test_monotone_constraints_cover_feature_set() -> None:
    assert set(MONOTONE_CONSTRAINTS.keys()) == set(FEATURE_COLUMNS)
    assert all(v in (-1, 0, 1) for v in MONOTONE_CONSTRAINTS.values())
