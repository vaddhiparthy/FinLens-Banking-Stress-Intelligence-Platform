"""Backend for the interactive AI scenario surface (real model, real data).

Powers three flows in the Streamlit Predictive Analytics tab:
  * insert a real bank by CERT -> its actual features + live distress score + reasons
  * hold out a real FAILED bank -> predicted score vs. the actual failure outcome
  * hypothetical what-if -> score a slider-built bank live

Everything reads the real DuckDB panel and the trained model. $0: no billable imports.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from finlens_ml.config import get_ml_settings
from finlens_ml.features import FEATURE_COLUMNS, MONOTONE_CONSTRAINTS

SLIDER_LABELS: dict[str, str] = {
    "tier1_rwa_ratio": "Tier 1 risk-based capital ratio (%)",
    "equity_to_assets": "Equity / assets (%)",
    "roa": "Return on assets (%)",
    "noncurrent_to_loans": "Noncurrent loans / total loans (%)",
    "nco_to_loans": "Net charge-offs / loans (%)",
    "loans_to_deposits": "Loans / deposits (%)",
    "brokered_to_deposits": "Brokered / total deposits (%)",
    "nim": "Net interest margin (%)",
    "efficiency_ratio": "Efficiency ratio (%)",
}

_ABBR = {
    "rwa": "RWA", "roa": "ROA", "roe": "ROE", "nim": "NIM", "nco": "NCO",
    "htm": "HTM", "afs": "AFS", "yoy": "YoY", "ppnr": "PPNR", "tier1": "Tier 1",
    "dep": "deposits", "ins": "insured",
}


_EXTRA_LABELS: dict[str, str] = {
    "roe": "Return on equity (%)",
    "nim_yoy_delta": "Net interest margin (YoY change)",
    "loans_to_deposits_yoy_delta": "Loans / deposits (YoY change)",
    "equity_to_assets_yoy_delta": "Equity / assets (YoY change)",
    "allowance_to_loans": "Loan-loss allowance / loans (%)",
    "cash_to_assets": "Cash / assets (%)",
    "noncurrent_to_loans_yoy_delta": "Noncurrent loans / loans (YoY change)",
    "log_assets": "Bank size (log assets)",
    "equity_to_assets_peer_z": "Equity / assets vs peers (z-score)",
}


def humanize_feature(name: str) -> str:
    """snake_case feature -> readable label, with banking acronyms preserved."""
    if name in SLIDER_LABELS:
        return SLIDER_LABELS[name]
    if name in _EXTRA_LABELS:
        return _EXTRA_LABELS[name]
    words = []
    for part in name.split("_"):
        if part in _ABBR:
            words.append(_ABBR[part])
        elif part == "to":
            words.append("/")
        elif part == "delta":
            words.append("change")
        else:
            words.append(part.capitalize())
    return " ".join(words)


# slider-friendly subset (the most interpretable CAMELS levers) + sane bounds
SLIDER_FEATURES: dict[str, tuple[float, float, float]] = {
    # feature: (min, max, default)
    "tier1_rwa_ratio": (0.0, 30.0, 12.0),
    "equity_to_assets": (0.0, 25.0, 10.0),
    "roa": (-8.0, 4.0, 1.0),
    "noncurrent_to_loans": (0.0, 25.0, 1.0),
    "nco_to_loans": (-1.0, 12.0, 0.2),
    "loans_to_deposits": (20.0, 160.0, 75.0),
    "brokered_to_deposits": (0.0, 80.0, 5.0),
    "nim": (0.0, 8.0, 3.2),
    "efficiency_ratio": (20.0, 120.0, 62.0),
}


@lru_cache(maxsize=1)
def _dataset() -> pd.DataFrame:
    import duckdb

    settings = get_ml_settings()
    with duckdb.connect(str(settings.duckdb_path), read_only=True) as conn:
        return conn.execute(
            "select * from ml.training_dataset"
        ).df()


@lru_cache(maxsize=1)
def bank_directory() -> pd.DataFrame:
    """One row per bank (latest quarter) for a searchable name picker, so users
    never have to know an FDIC CERT. Sorted by name; failed banks flagged."""
    df = _dataset().copy()
    latest = df.sort_values("obs_qord").drop_duplicates("cert", keep="last")
    cols = [c for c in ["cert", "bank_name", "state", "quarter"] if c in latest.columns]
    out = latest[cols].dropna(subset=["bank_name"]).copy()
    if "label_4" in latest.columns:
        ever_failed = df.groupby("cert")["label_4"].max()
        out["ever_failed"] = out["cert"].map(ever_failed).fillna(0).astype(int)
    else:
        out["ever_failed"] = 0
    out["cert"] = out["cert"].astype(int)
    out["label"] = (
        out["bank_name"].astype(str)
        + " (" + out["state"].fillna("?").astype(str) + ")"
    )
    return out.sort_values("bank_name").reset_index(drop=True)


def latest_row_for_cert(cert: int) -> dict | None:
    """Most recent bank-quarter feature row for a CERT (for 'insert test bank')."""
    df = _dataset()
    sub = df[df["cert"] == cert]
    if sub.empty:
        return None
    row = sub.sort_values("obs_qord").iloc[-1]
    feats = {c: (None if pd.isna(row[c]) else float(row[c])) for c in FEATURE_COLUMNS}
    return {
        "cert": int(cert),
        "bank_name": row.get("bank_name"),
        "quarter": row.get("quarter"),
        "state": row.get("state"),
        "features": feats,
        "actual_label_4": (None if pd.isna(row.get("label_4")) else int(row["label_4"])),
    }


def held_out_failed_banks(horizon_q: int = 4, limit: int = 25) -> pd.DataFrame:
    """Real banks that actually FAILED within the horizon (label==1), for the
    hold-out demo: pick one, score its pre-failure quarter, compare to the outcome."""
    df = _dataset()
    pos = df[df[f"label_{horizon_q}"] == 1].copy()
    if pos.empty:
        return pos
    # one row per cert: the earliest quarter where it was already flagged positive
    pos = pos.sort_values("obs_qord").drop_duplicates("cert", keep="first")
    cols = [c for c in ["cert", "bank_name", "quarter", "state"] if c in pos.columns]
    return pos[cols].head(limit).reset_index(drop=True)


def score_features(features: dict, horizon_q: int = 4) -> dict:
    """Score a feature dict (real or hypothetical) -> probability + decision + reasons."""
    from finlens_ml.explain import local_reasons
    from finlens_ml.predict import decision, score_record

    prob = score_record(features, horizon_q)
    dec = decision(prob)
    reasons = [
        {"feature": r.feature, "value": (None if r.value != r.value else r.value),
         "shap": r.shap, "direction": r.direction}
        for r in local_reasons(features, top_k=6)
    ]
    return {**dec, "reasons": reasons}


@lru_cache(maxsize=1)
def baseline_features() -> dict:
    """Median of every feature across the panel — a realistic, complete 'typical bank'
    vector. Used to fill the features a what-if user does not set, so the score and SHAP
    reasons reflect a coherent whole bank rather than a mostly-missing record."""
    df = _dataset()
    out: dict[str, float] = {}
    for c in FEATURE_COLUMNS:
        if c in df.columns:
            med = pd.to_numeric(df[c], errors="coerce").median()
            out[c] = None if pd.isna(med) else float(med)
        else:
            out[c] = None
    return out


def score_hypothetical(slider_values: dict, horizon_q: int = 4) -> dict:
    """Score a what-if bank: the user's sliders applied on top of a median baseline so
    every feature is populated and the reason codes are economically coherent."""
    full = {**baseline_features(), **slider_values}
    return score_features(full, horizon_q)


def default_hypothetical() -> dict:
    return {f: d for f, (_, _, d) in SLIDER_FEATURES.items()}


def feature_monotone(feature: str) -> int:
    return MONOTONE_CONSTRAINTS.get(feature, 0)
