"""CAMELS-aligned feature engineering for the bank-quarter panel.

Derives interpretable, economically-signed features from the raw FDIC panel:
levels (capital, asset quality, earnings, liquidity), trends (QoQ / YoY deltas),
peer z-scores within asset-size bands, and (optionally) point-in-time macro context.
Monotonic direction of each feature vs. distress risk is recorded in
``MONOTONE_CONSTRAINTS`` so the GBM can enforce regulator-defensible relationships.

No ``finlens.aws`` / ``boto3`` / ``snowflake`` imports ($0 invariant).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# raw FDIC fields used (already numeric in the panel)
_EPS = 1e-9


def _safe_ratio(num: pd.Series, den: pd.Series, scale: float = 100.0) -> pd.Series:
    den = den.where(den.abs() > _EPS)
    return (num / den) * scale


def add_level_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["log_assets"] = np.log(out["ASSET"].where(out["ASSET"] > 0))
    # Capital
    out["equity_to_assets"] = _safe_ratio(out["EQ"], out["ASSET"])
    out["tier1_rwa_ratio"] = pd.to_numeric(out.get("RBC1RWAJ"), errors="coerce")
    out["tier1_leverage"] = _safe_ratio(out.get("RBCT1J"), out["ASSET"])
    # Asset quality
    out["noncurrent_to_loans"] = _safe_ratio(out.get("P9LNLS"), out.get("LNLSGR"))
    out["nco_to_loans"] = pd.to_numeric(out.get("NTLNLSR"), errors="coerce")
    out["allowance_to_loans"] = _safe_ratio(out.get("LNATRES"), out.get("LNLSGR"))
    # Earnings
    out["roa"] = pd.to_numeric(out.get("ROA"), errors="coerce")
    out["roe"] = pd.to_numeric(out.get("ROE"), errors="coerce")
    out["nim"] = pd.to_numeric(out.get("NIMY"), errors="coerce")
    out["efficiency_ratio"] = pd.to_numeric(out.get("EEFFR"), errors="coerce")
    # Liquidity / funding
    out["loans_to_deposits"] = _safe_ratio(out.get("LNLSNET"), out.get("DEP"))
    out["brokered_to_deposits"] = _safe_ratio(out.get("BRO"), out.get("DEP"))
    out["securities_to_assets"] = _safe_ratio(out.get("SC"), out["ASSET"])
    out["cash_to_assets"] = _safe_ratio(out.get("CHBAL"), out["ASSET"])
    return out


_TREND_BASE = ["equity_to_assets", "noncurrent_to_loans", "roa", "nim", "loans_to_deposits"]


def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["cert", "repdte"]).copy()
    grp = out.groupby("cert", sort=False)
    out["asset_growth_yoy"] = grp["ASSET"].pct_change(4) * 100
    out["asset_growth_qoq"] = grp["ASSET"].pct_change(1) * 100
    for col in _TREND_BASE:
        out[f"{col}_qoq_delta"] = grp[col].diff(1)
        out[f"{col}_yoy_delta"] = grp[col].diff(4)
    return out


_PEER_BASE = ["equity_to_assets", "noncurrent_to_loans", "roa", "nco_to_loans"]


def add_peer_zscores(df: pd.DataFrame, n_bands: int = 10) -> pd.DataFrame:
    """Z-score key ratios within asset-size band, per quarter (peer-relative stress)."""
    out = df.copy()
    # size band by log-asset quantile within each quarter
    def _band(s: pd.Series) -> pd.Series:
        try:
            return pd.qcut(s.rank(method="first"), q=min(n_bands, max(1, s.notna().sum())),
                           labels=False, duplicates="drop")
        except (ValueError, IndexError):
            return pd.Series(0, index=s.index)

    out["size_band"] = out.groupby("quarter")["log_assets"].transform(_band).fillna(0).astype(int)
    for col in _PEER_BASE:
        g = out.groupby(["quarter", "size_band"])[col]
        mean = g.transform("mean")
        std = g.transform("std").replace(0, np.nan)
        out[f"{col}_peer_z"] = ((out[col] - mean) / std).fillna(0.0)
    return out


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    if panel.empty:
        return panel
    out = add_level_features(panel)
    out = add_trend_features(out)
    out = add_peer_zscores(out)
    return out


# the model feature set + monotone direction vs distress risk
# +1 => higher value should not DECREASE predicted distress; -1 => higher value
# should not INCREASE predicted distress. 0 => unconstrained.
MONOTONE_CONSTRAINTS: dict[str, int] = {
    "log_assets": 0,
    "equity_to_assets": -1,
    "tier1_rwa_ratio": -1,
    "tier1_leverage": -1,
    "noncurrent_to_loans": +1,
    "nco_to_loans": +1,
    "allowance_to_loans": 0,
    "roa": -1,
    "roe": -1,
    "nim": -1,
    "efficiency_ratio": +1,
    "loans_to_deposits": +1,
    "brokered_to_deposits": +1,
    "securities_to_assets": 0,
    "cash_to_assets": -1,
    "asset_growth_yoy": 0,
    "asset_growth_qoq": 0,
    "equity_to_assets_qoq_delta": -1,
    "equity_to_assets_yoy_delta": -1,
    "noncurrent_to_loans_qoq_delta": +1,
    "noncurrent_to_loans_yoy_delta": +1,
    "roa_qoq_delta": -1,
    "roa_yoy_delta": -1,
    "nim_qoq_delta": 0,
    "nim_yoy_delta": 0,
    "loans_to_deposits_qoq_delta": 0,
    "loans_to_deposits_yoy_delta": 0,
    "equity_to_assets_peer_z": -1,
    "noncurrent_to_loans_peer_z": +1,
    "roa_peer_z": -1,
    "nco_to_loans_peer_z": +1,
}

FEATURE_COLUMNS: list[str] = list(MONOTONE_CONSTRAINTS.keys())
