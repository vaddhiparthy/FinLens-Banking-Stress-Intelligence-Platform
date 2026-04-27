from finlens.stress_lab import FEATURE_COLUMNS, run_demo_stress_lab, score_manual_scenario


def test_stress_lab_returns_ranked_models():
    result = run_demo_stress_lab()

    assert len(result.model_results) >= 3
    assert result.model_results[0].cv_roc_auc >= result.model_results[-1].cv_roc_auc
    assert not result.heldout_predictions.empty
    assert not result.feature_importance.empty


def test_manual_scenario_score_is_probability():
    result = run_demo_stress_lab()
    sample = result.dataset.iloc[0]
    features = {column: float(sample[column]) for column in FEATURE_COLUMNS}

    score = score_manual_scenario(features)

    assert 0.0 <= score <= 1.0
