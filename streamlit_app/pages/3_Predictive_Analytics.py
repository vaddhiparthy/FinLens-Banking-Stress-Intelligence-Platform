# ruff: noqa: E402
"""Predictive Analytics — REAL interactive bank-distress scoring.

Backed by the trained model (ml/finlens_ml). Three in-page tabs (st.tabs = no full
reload): insert a real bank by CERT, hold out a real failed bank (predicted vs
actual), and a hypothetical what-if with CAMELS sliders. Every number is computed
live from the real calibrated model + SHAP — nothing is fabricated.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles, section_heading

st.set_page_config(
    page_title="FinLens | Predictive Analytics", layout="wide", initial_sidebar_state="collapsed"
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("predictive", BUSINESS_PAGE)
record_page_view("predictive_analytics", BUSINESS_PAGE)


@st.cache_resource(show_spinner=False)
def _backend():
    import finlens_ml.scenario as scenario

    return scenario


def _model_available() -> bool:
    return (PROJECT_ROOT / "ml" / "artifacts" / "calibrated_h4.skops").exists() or (
        PROJECT_ROOT / "ml" / "artifacts" / "booster_h4.txt"
    ).exists()


def _render_score(result: dict, actual: int | None = None) -> None:
    prob = result["probability"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Distress probability (4q)", f"{prob * 100:.2f}%")
    c2.metric("Decision", "FLAGGED for review" if result["flagged"] else "not flagged")
    if actual is not None:
        c3.metric("Actual outcome", "FAILED" if actual == 1 else "survived")
    st.caption(f"Flag threshold: {result['threshold'] * 100:.0f}% (calibrated probability)")
    reasons = pd.DataFrame(result["reasons"])
    if not reasons.empty:
        reasons["impact"] = reasons["shap"].abs().round(3)
        section_heading("Why — top SHAP reason codes", "Validator-facing drivers of this score.")
        st.dataframe(
            reasons[["feature", "value", "direction", "impact"]],
            hide_index=True,
            use_container_width=True,
        )


status_ribbon("Live model-backed predictive surface")
page_intro(
    "Business Surface",
    "Predictive Analytics",
    "Interactive bank financial-distress early-warning, scored live by the calibrated "
    "gradient-boosted hazard model. Ranks observable public-data stress; it is not "
    "investment, deposit, or supervisory advice.",
)

if not _model_available():
    chart_note(
        "Model artifact not present",
        "Train the model (python ml/finlens_ml/train.py) to activate this surface. "
        "The page is wired to the real model and will show no fabricated output.",
    )
    st.stop()

scenario = _backend()
tab_insert, tab_holdout, tab_what_if = st.tabs(
    ["Insert a bank (by CERT)", "Hold-out test (real failures)", "Hypothetical what-if"]
)

with tab_insert:
    st.write(
        "Enter an FDIC certificate number to score that institution's most recent "
        "quarter from real Call Report data."
    )
    cert = st.number_input("FDIC CERT", min_value=1, max_value=99999, value=29730, step=1)
    if st.button("Score this bank", key="score_cert"):
        row = scenario.latest_row_for_cert(int(cert))
        if row is None:
            st.warning(f"CERT {int(cert)} not found in the panel (2008Q1-2026Q1).")
        else:
            st.success(f"{row['bank_name']} ({row['state']}) — most recent quarter {row['quarter']}")
            _render_score(scenario.score_features(row["features"]), row["actual_label_4"])

with tab_holdout:
    st.write(
        "Pick a bank that **actually failed**. The model scores its pre-failure quarter "
        "so you can compare the predicted distress probability against the real outcome."
    )
    failed = scenario.held_out_failed_banks(limit=25)
    if failed.empty:
        st.info("No labeled failures in the panel.")
    else:
        failed["label"] = failed["bank_name"] + " (" + failed["state"].fillna("?") + ", " + failed["quarter"] + ")"
        choice = st.selectbox("Held-out failed bank", failed["label"].tolist(), key="holdout_pick")
        pick = failed[failed["label"] == choice].iloc[0]
        row = scenario.latest_row_for_cert(int(pick["cert"]))
        if row is not None:
            _render_score(scenario.score_features(row["features"]), row["actual_label_4"])

with tab_what_if:
    st.write("Move the CAMELS levers to build a hypothetical bank and watch the live score.")
    vals = {}
    cols = st.columns(3)
    for i, (feat, (lo, hi, default)) in enumerate(scenario.SLIDER_FEATURES.items()):
        with cols[i % 3]:
            vals[feat] = st.slider(feat, float(lo), float(hi), float(default), key=f"wi_{feat}")
    _render_score(scenario.score_features(vals))
    st.caption(
        "Monotone constraints are enforced in the model: more capital never increases "
        "predicted risk; higher noncurrent loans never decreases it."
    )
