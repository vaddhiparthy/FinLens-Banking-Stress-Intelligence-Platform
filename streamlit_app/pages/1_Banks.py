# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib.data import load_failures
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    chart_note,
    empty_state,
    inject_styles,
    metric_card,
    section_heading,
    styled_table,
)


def prepare_failures() -> pd.DataFrame:
    frame = load_failures().copy()
    frame["resolution_type"] = "Resolution detail not standardized in current feed"
    frame["status"] = "Failed"
    if "acquirer" not in frame:
        frame["acquirer"] = pd.NA
    return frame


def apply_readable_axes(figure: go.Figure) -> go.Figure:
    figure.update_xaxes(title_font=dict(color="#1f2933"), tickfont=dict(color="#1f2933"))
    figure.update_yaxes(title_font=dict(color="#1f2933"), tickfont=dict(color="#1f2933"))
    figure.update_layout(font=dict(color="#1f2933"))
    return figure


def failure_timeline(frame: pd.DataFrame) -> go.Figure:
    grouped = frame.groupby("year")["bank_id"].count().reset_index(name="failures")
    figure = px.bar(
        grouped,
        x="year",
        y="failures",
        color_discrete_sequence=["#bf6d47"],
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        yaxis_title="Failures",
        xaxis_title="Failure year",
    )
    return apply_readable_axes(figure)


def acquirer_chart(frame: pd.DataFrame) -> go.Figure:
    clean = frame.dropna(subset=["acquirer"]).copy()
    clean = clean.loc[clean["acquirer"].astype(str).str.strip() != ""]
    grouped = clean.groupby("acquirer").size().nlargest(15).reset_index(name="failures")
    figure = px.bar(
        grouped.sort_values("failures"),
        x="failures",
        y="acquirer",
        orientation="h",
        color_discrete_sequence=["#0f766e"],
    )
    figure.update_layout(
        title="Top acquirers in current filter",
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        xaxis=dict(title="Failures acquired", tickfont=dict(color="#1f2933")),
        yaxis=dict(title="Acquirer", tickfont=dict(color="#1f2933")),
    )
    return apply_readable_axes(figure)


def state_map(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        figure = go.Figure()
        figure.add_annotation(
            text="No failures match the selected filters",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#1f2933"),
        )
        figure.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            font=dict(color="#1f2933"),
        )
        return figure
    value_column = "assets_millions" if frame["assets_millions"].notna().any() else "bank_id"
    aggregation = "sum" if value_column == "assets_millions" else "count"
    grouped = frame.groupby("state")[value_column].agg(aggregation).reset_index()
    figure = px.choropleth(
        grouped,
        locations="state",
        locationmode="USA-states",
        color=value_column,
        scope="usa",
        color_continuous_scale="Tealgrn",
    )
    figure.update_layout(
        title="State-wise failures in current filter",
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        geo_bgcolor="rgba(255,255,255,0)",
        font=dict(color="#1f2933"),
        coloraxis_colorbar=dict(title="Failures", tickfont=dict(color="#1f2933")),
    )
    return apply_readable_axes(figure)


def inventory_table(frame: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "bank_name": "Bank",
        "city": "City",
        "state": "State",
        "closing_date": "Failure Date",
        "year": "Failure Year",
        "cert": "Cert",
        "acquirer": "Acquirer",
    }
    available = [column for column in columns if column in frame.columns]
    return (
        frame[available]
        .rename(columns=columns)
        .sort_values(["Failure Year", "State", "Bank"], ascending=[False, True, True])
    )


def _failure_inventory_page(total_rows: int) -> tuple[int, int]:
    page_size = 12
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page_key = "failure_inventory_page"
    if st.session_state.get(page_key, 1) > total_pages:
        st.session_state[page_key] = total_pages
    if st.session_state.get(page_key, 1) < 1:
        st.session_state[page_key] = 1
    return int(st.session_state.get(page_key, 1)), total_pages


def _render_inventory_pager(current_page: int, total_pages: int) -> None:
    st.markdown('<div class="page-control-anchor"></div>', unsafe_allow_html=True)
    _, left, middle, right, _ = st.columns([4.4, 0.25, 1, 0.25, 4.4], vertical_alignment="center")
    with left:
        if st.button("‹", key="failure_inventory_previous", use_container_width=True):
            st.session_state["failure_inventory_page"] = max(1, current_page - 1)
    with middle:
        st.markdown(
            f'<div class="page-number-display">Page {current_page} of {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with right:
        if st.button("›", key="failure_inventory_next", use_container_width=True):
            st.session_state["failure_inventory_page"] = min(total_pages, current_page + 1)


st.set_page_config(
    page_title="FinLens | Failure Forensics",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("banks", BUSINESS_PAGE)
record_page_view("failure_forensics", BUSINESS_PAGE)
status_ribbon("Failure analytics view")
page_intro(
    "Business Surface",
    "Failure Forensics",
    "A transformed failure dataset should show concentration, resolution patterns, and cost, not "
    "just a flat archive of collapsed institutions.",
)

failures = prepare_failures().sort_values(["year", "assets_millions"], ascending=[False, False])
if failures.empty:
    empty_state("No FDIC failure rows are available from the current source run.")
else:
    total_failures = len(failures)
    latest_year = int(failures["year"].max())
    ttm_count = failures.loc[failures["year"] == latest_year, "bank_id"].count()
    top_state = failures["state"].dropna().value_counts().index[0]
    state_count = int(failures["state"].dropna().value_counts().iloc[0])
    latest_failure = failures.sort_values("closing_date", ascending=False).iloc[0]

    card1, card2, card3, card4 = st.columns(4)
    with card1:
        metric_card("Total failures", f"{total_failures}", "1980-present FDIC feed view")
    with card2:
        metric_card("Top state", top_state, f"{state_count} failures in current feed")
    with card3:
        metric_card(
            "Latest failed bank",
            latest_failure["bank_name"],
            str(latest_failure["closing_date"])[:10],
        )
    with card4:
        metric_card("Latest year count", f"{ttm_count}", f"{latest_year} current slice")

    section_heading(
        "Geography And Acquirers",
        "Use the year and state controls below to filter the inventory. The map stays visual; "
        "the table is the operational drill-down.",
    )
    years = sorted(failures["year"].dropna().astype(int).unique().tolist(), reverse=True)
    states = ["All states", *sorted(failures["state"].dropna().unique().tolist())]
    filter_left, filter_right = st.columns(2)
    with filter_left:
        selected_year = st.selectbox(
            "Failure year",
            ["All years", *years],
            index=0,
            key="failure_forensics_year",
        )
    with filter_right:
        selected_state = st.selectbox("State", states, index=0, key="failure_forensics_state")

    filtered = failures.copy()
    if selected_year != "All years":
        filtered = filtered.loc[filtered["year"].eq(int(selected_year))]
    if selected_state != "All states":
        filtered = filtered.loc[filtered["state"].eq(selected_state)]

    left, right = st.columns(2)
    with left:
        st.plotly_chart(state_map(filtered), width="stretch")
        chart_note(
            "Interpretation",
            "The map now reflects the selected year and state filters. Use it as a geographic "
            "summary, then read the filtered inventory below for the actual banks.",
        )
    with right:
        st.plotly_chart(acquirer_chart(filtered), width="stretch")
        chart_note(
            "Interpretation",
            "The acquirer chart shows which institutions absorbed failed banks in the current "
            "filter. Blank output means the selected records do not carry acquirer names.",
        )

    section_heading(
        "Failure Inventory",
        "This is the one flat list in the business surface. It stays subordinate to the charts.",
    )
    if filtered.empty:
        empty_state("No failed-bank rows match the selected filters.")
    else:
        inventory = inventory_table(filtered)
        current_page, total_pages = _failure_inventory_page(len(inventory))
        start = (current_page - 1) * 12
        styled_table(inventory.iloc[start : start + 12])
        _render_inventory_pager(current_page, total_pages)
