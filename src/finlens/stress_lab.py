from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "total_assets_billion",
    "tier1_capital_ratio",
    "return_on_assets",
    "deposit_growth_pct",
    "uninsured_deposit_share",
    "securities_to_assets_pct",
    "cre_loan_share_pct",
    "nonperforming_assets_pct",
    "efficiency_ratio",
    "fed_funds_rate",
]


@dataclass(frozen=True)
class ModelResult:
    model_name: str
    cv_roc_auc: float
    test_roc_auc: float
    accuracy: float
    precision: float
    recall: float


@dataclass(frozen=True)
class StressLabResult:
    dataset: pd.DataFrame
    feature_columns: list[str]
    model_results: list[ModelResult]
    best_model_name: str
    heldout_predictions: pd.DataFrame
    feature_importance: pd.DataFrame
    confusion: list[list[int]]


def load_demo_stress_dataset() -> pd.DataFrame:
    records = [
        {
            "bank_name": "Washington Mutual Bank",
            "state": "WA",
            "snapshot_year": 2008,
            "failure_date": "2008-09-25",
            "failed": 1,
            "total_assets_billion": 307.0,
            "tier1_capital_ratio": 6.3,
            "return_on_assets": -1.6,
            "deposit_growth_pct": -8.1,
            "uninsured_deposit_share": 49.0,
            "securities_to_assets_pct": 21.0,
            "cre_loan_share_pct": 19.0,
            "nonperforming_assets_pct": 5.8,
            "efficiency_ratio": 79.0,
            "fed_funds_rate": 2.0,
        },
        {
            "bank_name": "IndyMac Bank",
            "state": "CA",
            "snapshot_year": 2008,
            "failure_date": "2008-07-11",
            "failed": 1,
            "total_assets_billion": 32.0,
            "tier1_capital_ratio": 6.8,
            "return_on_assets": -2.1,
            "deposit_growth_pct": -6.2,
            "uninsured_deposit_share": 44.0,
            "securities_to_assets_pct": 18.0,
            "cre_loan_share_pct": 26.0,
            "nonperforming_assets_pct": 6.3,
            "efficiency_ratio": 81.0,
            "fed_funds_rate": 2.0,
        },
        {
            "bank_name": "Bank of Granite",
            "state": "NC",
            "snapshot_year": 2009,
            "failure_date": "2009-10-09",
            "failed": 1,
            "total_assets_billion": 2.2,
            "tier1_capital_ratio": 6.5,
            "return_on_assets": -1.1,
            "deposit_growth_pct": -4.5,
            "uninsured_deposit_share": 28.0,
            "securities_to_assets_pct": 12.0,
            "cre_loan_share_pct": 34.0,
            "nonperforming_assets_pct": 4.8,
            "efficiency_ratio": 77.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "Colonial Bank",
            "state": "AL",
            "snapshot_year": 2009,
            "failure_date": "2009-08-14",
            "failed": 1,
            "total_assets_billion": 25.0,
            "tier1_capital_ratio": 5.6,
            "return_on_assets": -1.9,
            "deposit_growth_pct": -5.1,
            "uninsured_deposit_share": 37.0,
            "securities_to_assets_pct": 14.0,
            "cre_loan_share_pct": 31.0,
            "nonperforming_assets_pct": 5.2,
            "efficiency_ratio": 82.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "Guaranty Bank",
            "state": "TX",
            "snapshot_year": 2009,
            "failure_date": "2009-08-21",
            "failed": 1,
            "total_assets_billion": 13.0,
            "tier1_capital_ratio": 6.1,
            "return_on_assets": -1.4,
            "deposit_growth_pct": -3.8,
            "uninsured_deposit_share": 35.0,
            "securities_to_assets_pct": 15.0,
            "cre_loan_share_pct": 29.0,
            "nonperforming_assets_pct": 4.7,
            "efficiency_ratio": 78.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "Silicon Valley Bank",
            "state": "CA",
            "snapshot_year": 2023,
            "failure_date": "2023-03-10",
            "failed": 1,
            "total_assets_billion": 209.0,
            "tier1_capital_ratio": 7.8,
            "return_on_assets": 0.3,
            "deposit_growth_pct": -12.6,
            "uninsured_deposit_share": 86.0,
            "securities_to_assets_pct": 56.0,
            "cre_loan_share_pct": 9.0,
            "nonperforming_assets_pct": 0.6,
            "efficiency_ratio": 66.0,
            "fed_funds_rate": 4.75,
        },
        {
            "bank_name": "Signature Bank",
            "state": "NY",
            "snapshot_year": 2023,
            "failure_date": "2023-03-12",
            "failed": 1,
            "total_assets_billion": 118.0,
            "tier1_capital_ratio": 7.2,
            "return_on_assets": 0.2,
            "deposit_growth_pct": -10.9,
            "uninsured_deposit_share": 79.0,
            "securities_to_assets_pct": 28.0,
            "cre_loan_share_pct": 16.0,
            "nonperforming_assets_pct": 0.9,
            "efficiency_ratio": 71.0,
            "fed_funds_rate": 4.75,
        },
        {
            "bank_name": "First Republic Bank",
            "state": "CA",
            "snapshot_year": 2023,
            "failure_date": "2023-05-01",
            "failed": 1,
            "total_assets_billion": 229.0,
            "tier1_capital_ratio": 8.1,
            "return_on_assets": 0.1,
            "deposit_growth_pct": -14.4,
            "uninsured_deposit_share": 67.0,
            "securities_to_assets_pct": 25.0,
            "cre_loan_share_pct": 12.0,
            "nonperforming_assets_pct": 0.5,
            "efficiency_ratio": 74.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "PNC Bank",
            "state": "PA",
            "snapshot_year": 2009,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 280.0,
            "tier1_capital_ratio": 10.8,
            "return_on_assets": 0.9,
            "deposit_growth_pct": 3.5,
            "uninsured_deposit_share": 24.0,
            "securities_to_assets_pct": 16.0,
            "cre_loan_share_pct": 18.0,
            "nonperforming_assets_pct": 1.3,
            "efficiency_ratio": 58.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "U.S. Bank",
            "state": "MN",
            "snapshot_year": 2009,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 280.0,
            "tier1_capital_ratio": 11.4,
            "return_on_assets": 1.1,
            "deposit_growth_pct": 2.9,
            "uninsured_deposit_share": 21.0,
            "securities_to_assets_pct": 14.0,
            "cre_loan_share_pct": 17.0,
            "nonperforming_assets_pct": 1.1,
            "efficiency_ratio": 56.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "M&T Bank",
            "state": "NY",
            "snapshot_year": 2009,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 68.0,
            "tier1_capital_ratio": 10.9,
            "return_on_assets": 0.8,
            "deposit_growth_pct": 2.1,
            "uninsured_deposit_share": 18.0,
            "securities_to_assets_pct": 12.0,
            "cre_loan_share_pct": 22.0,
            "nonperforming_assets_pct": 1.4,
            "efficiency_ratio": 57.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "Bank of America",
            "state": "NC",
            "snapshot_year": 2009,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 2230.0,
            "tier1_capital_ratio": 10.2,
            "return_on_assets": 0.5,
            "deposit_growth_pct": 4.4,
            "uninsured_deposit_share": 26.0,
            "securities_to_assets_pct": 17.0,
            "cre_loan_share_pct": 15.0,
            "nonperforming_assets_pct": 1.9,
            "efficiency_ratio": 62.0,
            "fed_funds_rate": 0.2,
        },
        {
            "bank_name": "JPMorgan Chase",
            "state": "NY",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 3660.0,
            "tier1_capital_ratio": 13.9,
            "return_on_assets": 1.2,
            "deposit_growth_pct": 5.1,
            "uninsured_deposit_share": 34.0,
            "securities_to_assets_pct": 19.0,
            "cre_loan_share_pct": 11.0,
            "nonperforming_assets_pct": 0.6,
            "efficiency_ratio": 53.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "Citizens Bank",
            "state": "RI",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 226.0,
            "tier1_capital_ratio": 10.6,
            "return_on_assets": 0.9,
            "deposit_growth_pct": 2.8,
            "uninsured_deposit_share": 31.0,
            "securities_to_assets_pct": 15.0,
            "cre_loan_share_pct": 18.0,
            "nonperforming_assets_pct": 0.8,
            "efficiency_ratio": 59.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "Comerica Bank",
            "state": "TX",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 81.0,
            "tier1_capital_ratio": 11.1,
            "return_on_assets": 1.0,
            "deposit_growth_pct": -0.7,
            "uninsured_deposit_share": 48.0,
            "securities_to_assets_pct": 23.0,
            "cre_loan_share_pct": 17.0,
            "nonperforming_assets_pct": 0.6,
            "efficiency_ratio": 58.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "Fifth Third Bank",
            "state": "OH",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 214.0,
            "tier1_capital_ratio": 10.9,
            "return_on_assets": 1.1,
            "deposit_growth_pct": 1.9,
            "uninsured_deposit_share": 29.0,
            "securities_to_assets_pct": 18.0,
            "cre_loan_share_pct": 19.0,
            "nonperforming_assets_pct": 0.7,
            "efficiency_ratio": 57.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "Truist Bank",
            "state": "NC",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 535.0,
            "tier1_capital_ratio": 10.5,
            "return_on_assets": 0.9,
            "deposit_growth_pct": 1.4,
            "uninsured_deposit_share": 33.0,
            "securities_to_assets_pct": 20.0,
            "cre_loan_share_pct": 20.0,
            "nonperforming_assets_pct": 0.8,
            "efficiency_ratio": 59.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "Regions Bank",
            "state": "AL",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 157.0,
            "tier1_capital_ratio": 11.3,
            "return_on_assets": 1.1,
            "deposit_growth_pct": 2.3,
            "uninsured_deposit_share": 22.0,
            "securities_to_assets_pct": 14.0,
            "cre_loan_share_pct": 21.0,
            "nonperforming_assets_pct": 0.9,
            "efficiency_ratio": 56.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "Huntington Bank",
            "state": "OH",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 189.0,
            "tier1_capital_ratio": 11.7,
            "return_on_assets": 1.0,
            "deposit_growth_pct": 2.6,
            "uninsured_deposit_share": 19.0,
            "securities_to_assets_pct": 13.0,
            "cre_loan_share_pct": 23.0,
            "nonperforming_assets_pct": 0.8,
            "efficiency_ratio": 55.0,
            "fed_funds_rate": 5.0,
        },
        {
            "bank_name": "New York Community Bank",
            "state": "NY",
            "snapshot_year": 2023,
            "failure_date": "",
            "failed": 0,
            "total_assets_billion": 116.0,
            "tier1_capital_ratio": 9.2,
            "return_on_assets": 0.4,
            "deposit_growth_pct": -1.8,
            "uninsured_deposit_share": 36.0,
            "securities_to_assets_pct": 20.0,
            "cre_loan_share_pct": 39.0,
            "nonperforming_assets_pct": 1.7,
            "efficiency_ratio": 68.0,
            "fed_funds_rate": 5.0,
        },
    ]
    return pd.DataFrame.from_records(records)


def _build_models() -> dict[str, Pipeline]:
    return {
        "Logistic Regression": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Random Forest": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=5,
                        min_samples_leaf=1,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Gradient Boosting": Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingClassifier(random_state=42)),
            ]
        ),
    }


def _extract_importance(model: Pipeline, feature_columns: list[str]) -> pd.DataFrame:
    estimator = model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        importance = estimator.feature_importances_
    else:
        coefficients = getattr(estimator, "coef_", [[0.0] * len(feature_columns)])[0]
        importance = [abs(value) for value in coefficients]
    frame = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": importance,
        }
    )
    return frame.sort_values("importance", ascending=False).reset_index(drop=True)


def run_demo_stress_lab() -> StressLabResult:
    dataset = load_demo_stress_dataset()
    features = dataset[FEATURE_COLUMNS]
    target = dataset["failed"]

    x_train, x_test, y_train, y_test, meta_train, meta_test = train_test_split(
        features,
        target,
        dataset[["bank_name", "state", "snapshot_year", "failure_date"]],
        test_size=0.3,
        random_state=42,
        stratify=target,
    )

    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=42)
    model_results: list[ModelResult] = []
    fitted_models: dict[str, Pipeline] = {}

    for name, pipeline in _build_models().items():
        cv_scores = cross_val_score(pipeline, x_train, y_train, cv=cv, scoring="roc_auc")
        pipeline.fit(x_train, y_train)
        probabilities = pipeline.predict_proba(x_test)[:, 1]
        predictions = pipeline.predict(x_test)
        model_results.append(
            ModelResult(
                model_name=name,
                cv_roc_auc=float(cv_scores.mean()),
                test_roc_auc=float(roc_auc_score(y_test, probabilities)),
                accuracy=float(accuracy_score(y_test, predictions)),
                precision=float(precision_score(y_test, predictions)),
                recall=float(recall_score(y_test, predictions)),
            )
        )
        fitted_models[name] = pipeline

    best_model = max(model_results, key=lambda item: item.cv_roc_auc)
    best_pipeline = fitted_models[best_model.model_name]
    best_probabilities = best_pipeline.predict_proba(x_test)[:, 1]
    best_predictions = best_pipeline.predict(x_test)

    heldout_predictions = meta_test.reset_index(drop=True).copy()
    heldout_predictions[FEATURE_COLUMNS] = x_test.reset_index(drop=True)
    heldout_predictions["stress_score"] = best_probabilities
    heldout_predictions["predicted_failed"] = best_predictions
    heldout_predictions["actual_failed"] = y_test.reset_index(drop=True)
    heldout_predictions = heldout_predictions.sort_values("stress_score", ascending=False)

    importance = _extract_importance(best_pipeline, FEATURE_COLUMNS)
    confusion = confusion_matrix(y_test, best_predictions).tolist()

    return StressLabResult(
        dataset=dataset,
        feature_columns=FEATURE_COLUMNS,
        model_results=sorted(model_results, key=lambda item: item.cv_roc_auc, reverse=True),
        best_model_name=best_model.model_name,
        heldout_predictions=heldout_predictions.reset_index(drop=True),
        feature_importance=importance,
        confusion=confusion,
    )


def score_manual_scenario(feature_values: dict[str, float]) -> float:
    result = run_demo_stress_lab()
    winner = next(
        item for item in result.model_results if item.model_name == result.best_model_name
    )
    _ = winner
    pipeline = _build_models()[result.best_model_name]
    pipeline.fit(result.dataset[FEATURE_COLUMNS], result.dataset["failed"])
    frame = pd.DataFrame([{feature: feature_values[feature] for feature in FEATURE_COLUMNS}])
    return float(pipeline.predict_proba(frame)[0, 1])
