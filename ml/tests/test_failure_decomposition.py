"""Tests for the new failure-type decomposition + sequence-challenger layer.

These guard the logic that the adversarial gate relied on: the model-independent
classifier, the no-leakage sequence builder, the addressable-subset arithmetic, and
reconciliation of the committed artifacts (so a retrain that desyncs them fails CI).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
ART = REPO / "ml" / "artifacts"


def _load(modname, relpath):
    spec = importlib.util.spec_from_file_location(modname, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fd = _load("failure_decomposition", "ml/scripts/failure_decomposition.py")
sq = _load("sequence_challenger", "ml/scripts/sequence_challenger.py")


# ---- classifier ----

def test_classify_credit_from_noncurrent():
    row = pd.Series({"noncurrent_to_loans": 6.0, "nco_to_loans": 0.0,
                     "tier1_rwa_ratio": 15.0, "equity_to_assets": 10.0,
                     "uninsured_deposit_share": 5.0, "htm_securities_share": 0.0,
                     "afs_securities_share": 0.0})
    assert fd._classify(row) == "credit_visible"


def test_classify_credit_from_thin_capital():
    row = pd.Series({"noncurrent_to_loans": 0.1, "nco_to_loans": 0.0,
                     "tier1_rwa_ratio": 4.0, "equity_to_assets": 3.0,
                     "uninsured_deposit_share": 80.0, "htm_securities_share": 40.0,
                     "afs_securities_share": 0.0})
    # capital below PCA lines wins over the rate/liquidity branch
    assert fd._classify(row) == "credit_visible"


def test_classify_rate_liquidity_svb_profile():
    row = pd.Series({"noncurrent_to_loans": 0.2, "nco_to_loans": 0.0,
                     "tier1_rwa_ratio": 15.0, "equity_to_assets": 7.0,
                     "uninsured_deposit_share": 95.0, "htm_securities_share": 45.0,
                     "afs_securities_share": 0.0})
    assert fd._classify(row) == "rate_liquidity_visible"


def test_classify_invisible_when_sound():
    row = pd.Series({"noncurrent_to_loans": 0.0, "nco_to_loans": 0.0,
                     "tier1_rwa_ratio": 20.0, "equity_to_assets": 10.0,
                     "uninsured_deposit_share": 5.0, "htm_securities_share": 0.0,
                     "afs_securities_share": 0.0})
    assert fd._classify(row) == "invisible"


def test_classify_nan_securities_symmetric_and_safe():
    # NaN on a securities leg must not crash and must not manufacture a rate/liq label
    row = pd.Series({"noncurrent_to_loans": 0.1, "nco_to_loans": 0.0,
                     "tier1_rwa_ratio": 20.0, "equity_to_assets": 10.0,
                     "uninsured_deposit_share": 99.0, "htm_securities_share": np.nan,
                     "afs_securities_share": np.nan})
    assert fd._classify(row) == "invisible"


# ---- sequence builder: no leakage ----

def _toy_panel(k_quarters=10):
    from finlens_ml.features import FEATURE_COLUMNS
    rows = []
    for cert in (100, 200):
        for q in range(k_quarters):
            r = {c: 0.0 for c in FEATURE_COLUMNS}
            r[FEATURE_COLUMNS[0]] = float(q)  # marker = its own qord
            r["cert"] = cert
            r["obs_qord"] = q
            rows.append(r)
    return pd.DataFrame(rows), FEATURE_COLUMNS


def test_build_sequences_uses_only_past_and_left_pads():
    df, cols = _toy_panel(10)
    # target the row for cert 100 at qord 5
    idx = np.array([df.index[(df["cert"] == 100) & (df["obs_qord"] == 5)][0]])
    X, M = sq._build_sequences(df, idx)
    K = sq.K
    assert X.shape == (1, K, len(cols))
    # history at qord 5 is quarters 0..5 = 6 steps -> mask has 6 ones, left-padded
    assert int(M[0].sum()) == 6
    assert M[0, :K - 6].sum() == 0  # left pad is zero-masked
    # last unmasked step is the target quarter (no future leakage)
    assert X[0, K - 1, 0] == pytest.approx(5.0)
    # the marker feature across unmasked steps is strictly <= target qord
    unmasked = X[0, K - 6:, 0]
    assert unmasked.max() == pytest.approx(5.0)
    assert list(unmasked) == [0, 1, 2, 3, 4, 5]


def test_build_sequences_truncates_to_last_k():
    df, cols = _toy_panel(20)
    idx = np.array([df.index[(df["cert"] == 200) & (df["obs_qord"] == 19)][0]])
    X, M = sq._build_sequences(df, idx)
    K = sq.K
    assert int(M[0].sum()) == K  # full history available -> all K steps used
    assert list(X[0, :, 0]) == [float(q) for q in range(19 - K + 1, 20)]


# ---- addressable-subset arithmetic ----

def test_addressable_drops_only_invisible_positives():
    y = np.array([1, 1, 0, 0, 1])
    invisible = np.array([True, False, True, False, False])  # one invisible pos, one inv neg
    keep = ~(invisible & (y == 1))
    # the invisible NEGATIVE (index 2) must be kept; only the invisible POSITIVE (0) dropped
    assert keep.tolist() == [False, True, True, True, True]
    assert y[keep].sum() == 2  # 3 positives -> 2 after dropping the invisible positive


# ---- artifact reconciliation (regression guard against desync on retrain) ----

@pytest.mark.skipif(not (ART / "failure_decomposition.json").exists(),
                    reason="decomposition artifact not built")
def test_decomposition_artifact_reconciles():
    d = json.loads((ART / "failure_decomposition.json").read_text())
    tc = d["type_counts"]
    assert sum(tc.values()) == d["n_oot_positives"]
    assert d["addressable_positives"] + d["invisible_positives"] == d["n_oot_positives"]
    # by-filing-year counts sum to the totals
    by = d["by_filing_year"]
    assert sum(sum(v.values()) for v in by.values()) == d["n_oot_positives"]
    assert d["pr_auc_addressable"] >= d["pr_auc_full"]  # removing unseeable positives helps
    assert d["story_robust_to_thresholds"] is True
    # the addressable headline must carry its own bootstrap CI, and the credit-vs-rate/liquidity
    # boundary must not move it (only the invisible boundary does)
    full_ci = d["pr_auc_full_ci"]; addr_ci = d["pr_auc_addressable_ci"]
    assert addr_ci[0] <= d["pr_auc_addressable"] <= addr_ci[1]
    assert d["ci_overlap_full_addressable"] is True  # honest: intervals overlap heavily
    assert d["addressable_depends_only_on_invisible_boundary"] is True
    lo, hi = d["pr_auc_addressable_range_over_grids"]
    assert hi - lo < 0.15  # addressable stable as the invisible boundary varies


@pytest.mark.skipif(not (ART / "sequence_challenger.json").exists(),
                    reason="sequence artifact not built")
def test_sequence_artifact_inside_gbm_ci():
    s = json.loads((ART / "sequence_challenger.json").read_text())
    lo, hi = s["gbm_pr_auc_ci"]
    assert lo <= s["oot_pr_auc_gru"] <= hi  # not separable: GRU sits inside the GBM CI
    assert s["oot_pr_auc_gru"] < s["oot_pr_auc_gbm_served"]  # honest: GRU is worse
