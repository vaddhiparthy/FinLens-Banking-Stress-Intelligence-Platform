"""Deterministic tests for rare-event evaluation metrics."""

from __future__ import annotations

import numpy as np

from finlens_ml.evaluate import evaluate, evaluate_by_cohort, recall_precision_at_k


def test_recall_at_k_perfect_ranking() -> None:
    # 2 positives ranked at the very top -> recall@2 == 1.0, precision@2 == 1.0
    y = np.array([1, 1, 0, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.4, 0.3, 0.2, 0.1])
    recall, precision = recall_precision_at_k(y, s, k=2)
    assert recall == 1.0 and precision == 1.0


def test_recall_at_k_partial() -> None:
    # 1 of 2 positives in top-2
    y = np.array([1, 0, 1, 0])
    s = np.array([0.9, 0.8, 0.1, 0.05])
    recall, precision = recall_precision_at_k(y, s, k=2)
    assert recall == 0.5
    assert precision == 0.5


def test_evaluate_handles_single_class() -> None:
    # no positives -> pr_auc/roc_auc NaN, no crash
    y = np.zeros(10, dtype=int)
    s = np.random.default_rng(0).random(10)
    m = evaluate(y, s, k=3)
    assert np.isnan(m.pr_auc) and np.isnan(m.roc_auc)
    assert m.n_positive == 0


def test_evaluate_perfect_separation() -> None:
    y = np.array([0, 0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.3, 0.95, 0.99])
    m = evaluate(y, s, k=2)
    assert m.pr_auc > 0.99 and m.roc_auc == 1.0
    assert m.base_rate == 0.4


def test_evaluate_by_cohort_splits() -> None:
    y = np.array([1, 0, 1, 0])
    s = np.array([0.9, 0.1, 0.2, 0.8])
    cohort = np.array(["a", "a", "b", "b"])
    out = evaluate_by_cohort(y, s, cohort, k=1)
    assert set(out.keys()) == {"a", "b"}
    assert out["a"]["n"] == 2
