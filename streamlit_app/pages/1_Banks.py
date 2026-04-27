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
from streamlit_app.lib.ui_components import empty_state, inject_styles, metric_card, section_heading


def prepare_failures() -> pd.DataFrame:
    frame = load_failures().copy()
    frame["resolution_type"] = "Pending source mapping"
    frame["dif_cost_pct"] = pd.NA
    frame["status"] = "Failed"
    return frame


def failure_timeline(frame: pd.DataFrame) -> go.Figure:
    grouped = (
        frame.groupby(["year", "resolution_type"])["bank_id"].count().reset_index(name="failures")
    )
    figure = px.bar(
        grouped,
        x="year",
        y="failures",
        color="resolution_type",
        barmode="stack",
    )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        legend_title_text="Resolution type",
    )
    return figure


def dif_cost_chart(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    if frame["dif_cost_pct"].notna().any():
        grouped = frame.groupby("year")["dif_cost_pct"].mean().reset_index()
        figure.add_scatter(
            x=grouped["year"],
            y=grouped["dif_cost_pct"],
            mode="lines+markers",
            name="DIF cost as % of assets",
        )
    else:
        figure.add_annotation(
            text="DIF cost field pending source mapping",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
    figure.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        yaxis_title="% of assets",
    )
    return figure


def state_map(frame: pd.DataFrame) -> go.Figure:
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
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        geo_bgcolor="rgba(255,255,255,0)",
    )
    return figure


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
    selected_bank = st.selectbox("Selected failed bank", failures["bank_name"].tolist())
    selected = failures.loc[failures["bank_name"] == selected_bank].iloc[0]
    total_failures = len(failures)
    has_assets = failures["assets_millions"].notna().any()
    total_assets = failures["assets_millions"].sum(skipna=True)
    has_dif_cost = failures["dif_cost_pct"].notna().any()
    total_cost = failures["dif_cost_pct"].sum(skipna=True)
    ttm_count = failures.loc[failures["year"] == failures["year"].max(), "bank_id"].count()

    card1, card2, card3, card4 = st.columns(4)
    with card1:
        metric_card("Total failures", f"{total_failures}", "1980-present FDIC feed view")
    with card2:
        metric_card(
            "Assets failed" if has_assets else "Assets available",
            f"${total_assets:,.0f}M" if has_assets else "Not in current feed",
            "Live total" if has_assets else "FDIC CSV feed lacks asset amounts",
        )
    with card3:
        metric_card(
            "DIF cost",
            f"${total_cost:,.0f}M" if has_dif_cost else "Pending source mapping",
            "Live field" if has_dif_cost else "No synthetic cost estimate shown",
        )
    with card4:
        metric_card("Failures TTM", f"{ttm_count}", "Latest available year in current slice")

    section_heading(
        "Failure Timeline",
        "Resolution type is the cleanest first cut for making the failure archive analytically "
        "useful.",
    )
    st.plotly_chart(failure_timeline(failures), width="stretch")

    section_heading(
        "Cost And Geography",
        "This layer answers two practical questions: how expensive failures were and where the "
        "assets concentrated.",
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(dif_cost_chart(failures), width="stretch")
    with right:
        st.plotly_chart(state_map(failures), width="stretch")

    section_heading(
        "Selected Failed Bank",
        "The detail card stays simple in the resilient scope: institution identity, failure "
        "timing, asset scale, and resolution context.",
    )
    detail1, detail2, detail3 = st.columns(3)
    with detail1:
        metric_card("Institution", selected["bank_name"], selected["state"])
    with detail2:
        metric_card("Failure year", f"{int(selected['year'])}", selected["resolution_type"])
    with detail3:
        if pd.notna(selected["assets_millions"]):
            metric_card("Assets", f"${selected['assets_millions']:,.0f}M", selected["status"])
        else:
            cert_value = selected.get("cert", "Unavailable")
            metric_card("Cert", str(cert_value), selected["status"])

    section_heading(
        "Failure Inventory",
        "This is the one flat list in the business surface. It stays subordinate to the charts.",
    )
    inventory_columns = ["Bank", "State", "Failure Year", "Resolution Type"]
    renamed = failures.rename(
        columns={
            "bank_name": "Bank",
            "state": "State",
            "year": "Failure Year",
            "assets_millions": "Assets (M)",
            "resolution_type": "Resolution Type",
            "dif_cost_pct": "Estimated DIF Cost (M)",
            "cert": "Cert",
        }
    )
    if has_assets:
        inventory_columns.extend(["Assets (M)", "Estimated DIF Cost (M)"])
    else:
        inventory_columns.append("Cert")
    st.dataframe(renamed[inventory_columns], width="stretch", hide_index=True)
