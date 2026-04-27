from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DashboardFilters:
    states: list[str]
    metric: str
    decades: list[str]


@dataclass(frozen=True)
class DashboardKpis:
    total_failures: int
    total_assets_millions: float
    largest_failure_name: str
    largest_failure_year: int
    largest_failure_assets_millions: float
    top_acquirer_name: str
    top_acquirer_assets_millions: float


def default_states(failures: pd.DataFrame) -> list[str]:
    return sorted(failures["state"].dropna().unique().tolist())


def default_decades(acquirers: pd.DataFrame) -> list[str]:
    return sorted(acquirers["decade"].dropna().unique().tolist())


def default_metric(metrics: pd.DataFrame) -> str:
    unique = sorted(metrics["series_id"].dropna().unique().tolist())
    return unique[0] if unique else ""


def apply_dashboard_filters(
    failures: pd.DataFrame,
    metrics: pd.DataFrame,
    acquirers: pd.DataFrame,
    filters: DashboardFilters,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    filtered_failures = failures[failures["state"].isin(filters.states)].copy()
    filtered_metrics = metrics[metrics["series_id"] == filters.metric].copy()
    filtered_acquirers = acquirers[acquirers["decade"].isin(filters.decades)].copy()
    return filtered_failures, filtered_metrics, filtered_acquirers


def compute_kpis(
    filtered_failures: pd.DataFrame,
    filtered_acquirers: pd.DataFrame,
) -> DashboardKpis | None:
    if filtered_failures.empty or filtered_acquirers.empty:
        return None

    largest_failure = filtered_failures.sort_values("assets_millions", ascending=False).iloc[0]
    top_acquirer = filtered_acquirers.sort_values("assets_absorbed_millions", ascending=False).iloc[
        0
    ]

    return DashboardKpis(
        total_failures=len(filtered_failures),
        total_assets_millions=float(filtered_failures["assets_millions"].sum()),
        largest_failure_name=str(largest_failure["bank_name"]),
        largest_failure_year=int(largest_failure["year"]),
        largest_failure_assets_millions=float(largest_failure["assets_millions"]),
        top_acquirer_name=str(top_acquirer["acquirer"]),
        top_acquirer_assets_millions=float(top_acquirer["assets_absorbed_millions"]),
    )


def failures_table(filtered_failures: pd.DataFrame) -> pd.DataFrame:
    return filtered_failures.rename(
        columns={
            "bank_name": "Bank",
            "state": "State",
            "year": "Failure Year",
            "assets_millions": "Assets (M)",
            "acquirer": "Acquirer",
        }
    )
