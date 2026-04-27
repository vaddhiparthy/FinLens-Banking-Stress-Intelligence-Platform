import pandas as pd

from streamlit_app.lib.view_model import (
    DashboardFilters,
    apply_dashboard_filters,
    compute_kpis,
    failures_table,
)


def test_apply_dashboard_filters_returns_sliced_frames() -> None:
    failures = pd.DataFrame(
        [
            {"state": "CA", "bank_id": "a", "assets_millions": 10, "bank_name": "A", "year": 2023},
            {"state": "NC", "bank_id": "b", "assets_millions": 20, "bank_name": "B", "year": 2009},
        ]
    )
    metrics = pd.DataFrame(
        [
            {"series_id": "UNRATE", "date": "2023-01-01", "value": 1},
            {"series_id": "DGS10", "date": "2023-01-01", "value": 2},
        ]
    )
    acquirers = pd.DataFrame(
        [
            {"acquirer": "X", "decade": "2020s", "assets_absorbed_millions": 10},
            {"acquirer": "Y", "decade": "2000s", "assets_absorbed_millions": 20},
        ]
    )

    filtered_failures, filtered_metrics, filtered_acquirers = apply_dashboard_filters(
        failures,
        metrics,
        acquirers,
        DashboardFilters(states=["CA"], metric="UNRATE", decades=["2020s"]),
    )

    assert filtered_failures["state"].tolist() == ["CA"]
    assert filtered_metrics["series_id"].tolist() == ["UNRATE"]
    assert filtered_acquirers["decade"].tolist() == ["2020s"]


def test_compute_kpis_returns_none_for_empty_slices() -> None:
    failures = pd.DataFrame(columns=["assets_millions", "bank_name", "year"])
    acquirers = pd.DataFrame(columns=["assets_absorbed_millions", "acquirer"])

    assert compute_kpis(failures, acquirers) is None


def test_failures_table_renames_columns() -> None:
    table = failures_table(
        pd.DataFrame(
            [
                {
                    "bank_name": "Example Bank",
                    "state": "CA",
                    "year": 2023,
                    "assets_millions": 100.0,
                    "acquirer": "Buyer",
                }
            ]
        )
    )

    assert "Bank" in table.columns
    assert "Failure Year" in table.columns
