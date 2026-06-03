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
inject_styles(app_css(get_theme_mode(), sidebar_open=True))
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

        def _fmt_value(v: object) -> str:
            if v is None or (isinstance(v, float) and v != v):
                return "n/a (not reported)"
            if isinstance(v, (int, float)):
                return f"{v:,.3f}"
            return str(v)

        reasons["Driver"] = reasons["feature"].astype(str).map(scenario.humanize_feature)
        reasons["Reported value"] = reasons["value"].map(_fmt_value)
        reasons = reasons.rename(columns={"direction": "Effect on risk", "impact": "Weight"})
        section_heading(
            "Why this score",
            "The factors that moved this bank's score most, from the model's SHAP "
            "attribution. Higher weight = larger influence.",
        )
        st.dataframe(
            reasons[["Driver", "Reported value", "Effect on risk", "Weight"]],
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
    ["Score any bank (by name)", "Hold-out test (real failures)", "Hypothetical what-if"]
)

with tab_insert:
    st.write(
        "Search for any U.S. bank by name and score its most recent quarter in the panel "
        "from real FDIC Call Report data. (No need to know any code — just start typing.)"
    )
    directory = scenario.bank_directory()
    labels = directory["label"].tolist()
    default_idx = next(
        (i for i, lbl in enumerate(labels) if lbl.startswith("INDYMAC")), 0
    )
    choice = st.selectbox(
        "Bank",
        labels,
        index=default_idx,
        key="insert_bank_pick",
        help="Type to search across every bank in the panel.",
        placeholder="Start typing a bank name…",
    )
    if choice:
        pick = directory[directory["label"] == choice].iloc[0]
        row = scenario.latest_row_for_cert(int(pick["cert"]))
        if row is None:
            st.warning("That bank has no scoreable quarter in the panel.")
        else:
            note = "most recent quarter in panel"
            st.success(
                f"{row['bank_name']} ({row['state']}) — {note}: {row['quarter']} "
                f"· FDIC CERT {row['cert']}"
            )
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
    st.write(
        "Move the CAMELS levers to build a hypothetical bank and watch the live score. "
        "Levers you don't touch are set to the typical (median) bank, so the score "
        "reflects a complete, realistic institution."
    )
    vals = {}
    cols = st.columns(3)
    for i, (feat, (lo, hi, default)) in enumerate(scenario.SLIDER_FEATURES.items()):
        with cols[i % 3]:
            vals[feat] = st.slider(
                scenario.SLIDER_LABELS.get(feat, feat),
                float(lo), float(hi), float(default), key=f"wi_{feat}",
            )
    _render_score(scenario.score_hypothetical(vals))
    st.caption(
        "Monotone constraints are enforced in the model: more capital never increases "
        "predicted risk; higher noncurrent loans never decreases it."
    )
