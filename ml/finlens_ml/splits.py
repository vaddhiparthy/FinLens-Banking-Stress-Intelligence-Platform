"""Rolling-origin out-of-time splits with reporting-lag embargo.

The ONLY valid validation for a bank-distress hazard model: train on the past,
test on the future, with an embargo so a training row's label horizon cannot peek
into the test period. Random k-fold is forbidden (temporal leakage).

For a training observation at quarter q with horizon H, its label looks at quarters
(q, q+H]. To keep the test period (starting at quarter t) strictly out-of-sample, a
training row must satisfy q + H < t  (i.e. q <= t - H - 1). That gap is the embargo;
it equals the label horizon and subsumes the call-report reporting lag.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OOTFold:
    test_quarter_ord: int
    train_idx: np.ndarray
    test_idx: np.ndarray


def rolling_origin_folds(
    obs_qord: pd.Series,
    *,
    horizon_q: int,
    min_train_quarters: int = 8,
    step: int = 1,
    n_test_quarters: int = 1,
) -> list[OOTFold]:
    """Generate expanding-window out-of-time folds keyed by quarter ordinal.

    ``obs_qord`` is the per-row observation-quarter ordinal (year*4 + quarter-1).
    Each fold: train where q <= t - horizon - 1 (embargo), test where t <= q < t+n.
    """
    q = pd.Series(obs_qord).reset_index(drop=True)
    quarters = np.sort(q.dropna().unique())
    if len(quarters) == 0:
        return []
    folds: list[OOTFold] = []
    first_q = quarters[0]
    # earliest test quarter that leaves room for min_train_quarters of embargoed train
    earliest_test = first_q + min_train_quarters + horizon_q
    test_candidates = [t for t in quarters if t >= earliest_test]
    for t in test_candidates[::step]:
        train_cutoff = t - horizon_q - 1
        train_idx = q.index[(q <= train_cutoff)].to_numpy()
        test_idx = q.index[(q >= t) & (q < t + n_test_quarters)].to_numpy()
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        folds.append(OOTFold(test_quarter_ord=int(t), train_idx=train_idx, test_idx=test_idx))
    return folds


def final_holdout_split(
    obs_qord: pd.Series, *, horizon_q: int, holdout_quarters: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """A single train/test cut: last ``holdout_quarters`` are the out-of-time test set,
    with the horizon embargo applied to the train side."""
    q = pd.Series(obs_qord).reset_index(drop=True)
    quarters = np.sort(q.dropna().unique())
    if len(quarters) <= holdout_quarters:
        raise ValueError("not enough quarters for the requested holdout")
    test_start = quarters[-holdout_quarters]
    train_cutoff = test_start - horizon_q - 1
    train_idx = q.index[q <= train_cutoff].to_numpy()
    test_idx = q.index[q >= test_start].to_numpy()
    return train_idx, test_idx


def assert_no_temporal_overlap(
    obs_qord: pd.Series, train_idx: np.ndarray, test_idx: np.ndarray, horizon_q: int
) -> None:
    """Guard: every train row's label horizon ends strictly before any test quarter."""
    q = pd.Series(obs_qord).reset_index(drop=True)
    if len(train_idx) == 0 or len(test_idx) == 0:
        return
    max_train_horizon_end = q.iloc[train_idx].max() + horizon_q
    min_test = q.iloc[test_idx].min()
    assert max_train_horizon_end < min_test, (
        f"temporal leakage: train horizon reaches {max_train_horizon_end} "
        f">= test start {min_test}"
    )
