import pandas as pd
from streamlit_app.lib import data as data_module

from streamlit_app.lib.charts import (
    acquirer_chart,
    failures_by_year_chart,
    largest_failures_chart,
    latest_macro_snapshot,
    macro_compare_chart,
    macro_trend_chart,
    state_assets_map,
    state_mix_donut,
    top_states_chart,
)
from streamlit_app.lib.data import load_acquirers, load_failures, load_metrics


def test_chart_builders_return_plotly_figures(monkeypatch) -> None:
    # Exercise the real loaders and chart builders with deterministic warehouse rows.
    failures_fixture = pd.DataFrame([
        {"bank_id": 1, "bank_name": "Fixture Bank A", "city": "City A", "state": "VA", "cert": 1001, "acquirer": "Fixture Acquirer A", "closing_date": pd.Timestamp("2022-03-01"), "year": 2022, "assets_millions": 50000.0},
        {"bank_id": 2, "bank_name": "Fixture Bank B", "city": "City B", "state": "CA", "cert": 1002, "acquirer": "Fixture Acquirer A", "closing_date": pd.Timestamp("2023-04-01"), "year": 2023, "assets_millions": 20000.0},
        {"bank_id": 3, "bank_name": "Fixture Bank C", "city": "City C", "state": "NY", "cert": 1003, "acquirer": "Fixture Acquirer B", "closing_date": pd.Timestamp("2024-05-01"), "year": 2024, "assets_millions": 10000.0},
    ])
    metrics_fixture = pd.DataFrame([
        {"series_id": series, "date": pd.Timestamp(date), "value": value, "metric_name": title}
        for series, title, values in [("UNRATE", "Unemployment rate", [3.5, 3.6, 3.7]), ("FEDFUNDS", "Federal funds rate", [4.5, 4.6, 4.7])]
        for date, value in zip(["2024-01-01", "2024-02-01", "2024-03-01"], values)
    ])
    acquirers_fixture = pd.DataFrame([
        {"acquirer": "Fixture Acquirer A", "decade": 2020, "failure_count": 2, "assets_absorbed_millions": 70000.0},
        {"acquirer": "Fixture Acquirer B", "decade": 2020, "failure_count": 1, "assets_absorbed_millions": 10000.0},
    ])
    tables = {"marts.fct_bank_failures": failures_fixture, "marts.fct_financial_metrics": metrics_fixture, "marts.dim_acquirer": acquirers_fixture}
    monkeypatch.setattr(data_module, "_read_cached", lambda table: tables[table].copy())
    failures = load_failures()
    metrics = load_metrics()
    acquirers = load_acquirers()

    figures = [
        failures_by_year_chart(failures),
        state_assets_map(failures),
        macro_trend_chart(metrics[metrics["series_id"] == metrics["series_id"].iloc[0]], "UNRATE"),
        acquirer_chart(acquirers),
        state_mix_donut(failures),
        top_states_chart(failures),
        largest_failures_chart(failures),
        macro_compare_chart(metrics),
        latest_macro_snapshot(metrics),
    ]

    for figure in figures:
        assert figure.to_dict()
        assert figure.data
