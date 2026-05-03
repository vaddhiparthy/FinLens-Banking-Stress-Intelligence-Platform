# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading, styled_table


def planned_scope() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Planned artifact": "Gold mart",
                "Target": "marts.fct_bank_stress_score",
                "Status": "Coming soon",
                "Purpose": (
                    "One row per active institution with score, decile, "
                    "and component breakdown."
                ),
            },
            {
                "Planned artifact": "Training script",
                "Target": "scripts/train_stress_score.py",
                "Status": "Coming soon",
                "Purpose": (
                    "Train a transparent logistic model from public historical "
                    "failure data."
                ),
            },
            {
                "Planned artifact": "Model coefficients",
                "Target": "dbt reference table",
                "Status": "Coming soon",
                "Purpose": "Keep scoring auditable as data, not an opaque pickled object.",
            },
            {
                "Planned artifact": "Scoring surface",
                "Target": "Business Surface",
                "Status": "Coming soon",
                "Purpose": (
                    "Explain relative observable stress without presenting "
                    "failure predictions."
                ),
            },
        ]
    )


def scoring_boundaries() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Boundary": "Not a prediction",
                "Meaning": (
                    "The score will rank observable public-data stress, "
                    "not forecast bank failure."
                ),
            },
            {
                "Boundary": "No supervisory data",
                "Meaning": (
                    "CAMELS ratings, examination findings, and internal "
                    "liquidity data are not public."
                ),
            },
            {
                "Boundary": "Transparent first",
                "Meaning": (
                    "The first version will favor interpretable coefficients "
                    "and component attribution."
                ),
            },
            {
                "Boundary": "Quarterly cadence",
                "Meaning": (
                    "The scoring refresh will align with available public "
                    "banking-data cadence."
                ),
            },
        ]
    )


st.set_page_config(
    page_title="FinLens | Predictive Analytics",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("predictive", BUSINESS_PAGE)
record_page_view("predictive_analytics", BUSINESS_PAGE)
status_ribbon("Planned analytical surface")
page_intro(
    "Business Surface",
    "Predictive Analytics",
    "Coming soon: a transparent bank stress scoring surface that ranks observable public-data "
    "stress indicators without presenting itself as a bank-failure prediction product.",
)

chart_note(
    "Scope boundary",
    "This surface is intentionally not active yet. It is documented as planned work because the "
    "model, scoring mart, and validation artifacts must exist before any score is shown publicly.",
)

section_heading(
    "Planned Delivery Shape",
    "The target implementation keeps the score inside the data platform: train transparently, "
    "store coefficients as auditable data, compute scores in the mart layer, and serve only Gold.",
)
styled_table(planned_scope())

section_heading(
    "Interpretation Guardrails",
    "These boundaries will remain visible in the surface so the analysis is not mistaken for "
    "regulatory, investment, deposit, or supervisory advice.",
)
styled_table(scoring_boundaries())
