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


def test_chart_builders_return_plotly_figures() -> None:
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
