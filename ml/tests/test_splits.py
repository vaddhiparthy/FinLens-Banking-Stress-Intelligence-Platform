"""Tests for rolling-origin out-of-time splits + embargo (no leakage)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from finlens_ml.splits import (
    assert_no_temporal_overlap,
    final_holdout_split,
    rolling_origin_folds,
)


def _obs(quarter_ords: list[int]) -> pd.Series:
    return pd.Series(quarter_ords)


def test_embargo_prevents_horizon_leakage() -> None:
    # 20 consecutive quarters
    base = 8032
    obs = _obs(list(range(base, base + 20)) * 3)  # 3 banks, same quarters
    folds = rolling_origin_folds(obs, horizon_q=4, min_train_quarters=8, step=1)
    assert folds, "expected at least one fold"
    for fold in folds:
        max_train = obs.iloc[fold.train_idx].max()
        min_test = obs.iloc[fold.test_idx].min()
        # train horizon (max_train + 4) must end strictly before the test quarter
        assert max_train + 4 < min_test
        assert_no_temporal_overlap(obs, fold.train_idx, fold.test_idx, horizon_q=4)


def test_expanding_window_grows() -> None:
    base = 8000
    obs = _obs(list(range(base, base + 24)))
    folds = rolling_origin_folds(obs, horizon_q=4, min_train_quarters=8, step=1)
    train_sizes = [len(f.train_idx) for f in folds]
    assert train_sizes == sorted(train_sizes), "train set should expand over folds"


def test_final_holdout_split_is_out_of_time() -> None:
    base = 8000
    obs = _obs(list(range(base, base + 20)))
    train_idx, test_idx = final_holdout_split(obs, horizon_q=4, holdout_quarters=8)
    assert obs.iloc[train_idx].max() + 4 < obs.iloc[test_idx].min()
    assert obs.iloc[test_idx].min() == base + 12  # last 8 quarters


def test_no_overlap_guard_raises_on_leak() -> None:
    obs = _obs([10, 11, 12, 13, 14])
    train_idx = np.array([0, 1, 2])  # quarters 10,11,12
    test_idx = np.array([3, 4])  # quarters 13,14 -> train horizon 12+4=16 >= 13 leak
    with pytest.raises(AssertionError):
        assert_no_temporal_overlap(obs, train_idx, test_idx, horizon_q=4)
