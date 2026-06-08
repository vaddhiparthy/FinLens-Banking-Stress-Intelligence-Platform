# ruff: noqa: E402,E501
"""Technical Dashboard: the AI model and the data pipeline at a glance, no write-ups.

Curated from the AI Engineering and Data Engineering surfaces, grouped headline -> detail. Reads the
real artifacts and live pipeline state; honest-empty where an artifact is missing.
"""

import json
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from finlens.pipeline_status import pipeline_status_rows
from streamlit_app.lib import ml_charts as mc
from streamlit_app.lib.de_pipeline import (
    TZ_CHOICES,
    dag_chart,
    pipeline_status_frame,
    pipeline_status_table,
)
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import (
    inject_styles,
    metric_card,
    section_heading,
    status_tone,
    styled_table,
)
from streamlit_app.lib.wiki_architecture import render_architecture

st.set_page_config(page_title="FinLens | Technical Dashboard", layout="wide",
                   initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
home_navigation()
record_page_view("technical_dashboard", "technical")
MODE = get_theme_mode()
ART = PROJECT_ROOT / "ml" / "artifacts"


def _oot() -> dict:
    p = ART / "metrics_h4.json"
    if not p.exists():
        return {}
    m = json.loads(p.read_text())
    t = (m.get("oot_test", {}) or {}).get("calibrated_lgbm", {})
    return {"pr_auc": t.get("pr_auc"), "roc_auc": t.get("roc_auc"),
            "recall_at_k": t.get("recall_at_k"), "k": t.get("k"),
            "ece": (m.get("oot_calibration", {}) or {}).get("ece"),
            "positives": m.get("test_positives")}


def _gx() -> dict:
    for rel in ("great_expectations/validation_result.json",
                "great_expectations/uncommitted/validation_result.json"):
        p = PROJECT_ROOT / rel
        if p.exists():
            try:
                d = json.loads(p.read_text())
                stats = d.get("statistics", {})
                return {"success": d.get("success"),
                        "evaluated": stats.get("evaluated_expectations"),
                        "successful": stats.get("successful_expectations")}
            except Exception:  # noqa: BLE001
                return {}
    return {}


st.markdown(
    """
    <style>
    div[class*="st-key-td_tab_dash"] button, div[class*="st-key-td_tab_arch"] button {
        background: transparent !important; border: none !important; box-shadow: none !important;
        padding: 0 !important; min-height: 0 !important; justify-content: flex-start !important; }
    div[class*="st-key-td_tab_dash"] button:disabled,
    div[class*="st-key-td_tab_arch"] button:disabled { opacity: 1 !important; }
    div[class*="st-key-td_tab_dash"] button:disabled p,
    div[class*="st-key-td_tab_arch"] button:disabled p {
        font-size: 1.75rem !important; font-weight: 800 !important; letter-spacing: -.02em !important;
        color: #a8501f !important; -webkit-text-fill-color: #a8501f !important; opacity: 1 !important; }
    div[class*="st-key-td_tab_dash"] button:not(:disabled) p,
    div[class*="st-key-td_tab_arch"] button:not(:disabled) p {
        font-size: 1.2rem !important; font-weight: 700 !important; color: #9a8a78 !important;
        -webkit-text-fill-color: #9a8a78 !important; }
    div[class*="st-key-td_tab_dash"] button:not(:disabled):hover p,
    div[class*="st-key-td_tab_arch"] button:not(:disabled):hover p {
        color: #a8501f !important; -webkit-text-fill-color: #a8501f !important; }
    .td-tab-pipe { font-size: 1.7rem; font-weight: 300; color: #cbbfae; text-align: center;
        line-height: 2.1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.session_state.setdefault("td_view", "dashboard")
_tc1, _tcp, _tc2, _tcsp = st.columns([2.4, 0.12, 1.2, 6.3], vertical_alignment="center")
with _tc1:
    st.button("Technical Dashboard", key="td_tab_dash", use_container_width=True,
              disabled=st.session_state["td_view"] == "dashboard",
              on_click=lambda: st.session_state.update(td_view="dashboard"))
with _tcp:
    st.markdown('<div class="td-tab-pipe">|</div>', unsafe_allow_html=True)
with _tc2:
    st.button("Architecture", key="td_tab_arch", use_container_width=True,
              disabled=st.session_state["td_view"] == "arch",
              on_click=lambda: st.session_state.update(td_view="arch"))

if st.session_state["td_view"] == "arch":
    st.markdown('<div class="dash-sub">The whole platform end to end: public sources, ingestion and '
                'Bronze, dbt Silver/Intermediate/Gold on DuckDB, the ML hazard model, the serving '
                'surfaces, and orchestration. Scroll to zoom, drag to pan.</div>',
                unsafe_allow_html=True)
    render_architecture()
    if st.button("Read more about the architecture ›", key="td_arch_readmore"):
        st.session_state["wiki_article"] = "system-architecture"
        st.switch_page("pages/6_Wiki.py")
    page_footer()
    st.stop()

st.markdown('<div class="dash-sub">The model and the pipeline at a glance: out-of-time performance, '
            'calibration, feature drivers, and live data-engineering status. Real artifacts; no '
            'commentary.</div>', unsafe_allow_html=True)

oot = _oot()
viz = mc.load_viz_pack()
pf = mc.load_panel_facts() or {}

# ---- AI headline ----
section_heading("Model performance (out-of-time)",
                "Held-out, embargoed evaluation: the honest forward read.")
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    metric_card("PR-AUC (OOT)", f"{oot.get('pr_auc'):.3f}" if oot.get("pr_auc") else "n/a",
                "vs 0.055% base rate", tone="ok")
with k2:
    metric_card("ROC-AUC (OOT)", f"{oot.get('roc_auc'):.3f}" if oot.get("roc_auc") else "n/a",
                "ranking quality")
with k3:
    rk = oot.get("recall_at_k")
    metric_card(f"Recall@{oot.get('k') or 200}", f"{rk * 100:.1f}%" if rk else "n/a",
                "caught in review budget")
with k4:
    ece = oot.get("ece")
    metric_card("Calibration (ECE)", f"{ece:.1e}" if ece else "n/a", "lower is better")
with k5:
    metric_card("Panel", f"{pf['n_panel_rows']:,}" if pf.get("n_panel_rows") else "448k+",
                f"{oot.get('positives') or 66} OOT failures")

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

if viz:
    a1, a2 = st.columns(2)
    with a1:
        with st.spinner("Loading precision-recall curve…"):
            st.plotly_chart(mc.pr_curve_fig(viz, MODE), use_container_width=True, key="td_pr")
    with a2:
        with st.spinner("Loading calibration…"):
            st.plotly_chart(mc.calibration_fig(viz, MODE), use_container_width=True, key="td_cal")
    a3, a4 = st.columns(2)
    with a3:
        with st.spinner("Loading score distribution…"):
            st.plotly_chart(mc.score_dist_fig(viz, MODE), use_container_width=True, key="td_sd")
    with a4:
        with st.spinner("Loading feature drivers…"):
            st.plotly_chart(mc.shap_importance_fig(viz, MODE), use_container_width=True,
                            key="td_shap")
    drift = mc.drift_fig(viz, MODE) or mc.psi_fig(viz, MODE)
    if drift is not None:
        with st.spinner("Loading drift…"):
            st.plotly_chart(drift, use_container_width=True, key="td_drift")
else:
    st.caption("Model viz pack not present: train the model to populate these.")

st.markdown('<div class="dash-rule"></div>', unsafe_allow_html=True)

# ---- DE headline ----
section_heading("Data pipeline status", "Live source-to-serving health from the last run.")
gx = _gx()
rows = pipeline_status_rows()
cols = st.columns(4)
for i, r in enumerate(rows[:8]):
    with cols[i % 4]:
        metric_card(r.get("flow_name", ""), r.get("status", ""),
                    str(r.get("last_run", ""))[:16].replace("T", " "),
                    tone=status_tone(r.get("status", "")))

st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
q1, q2, q3 = st.columns(3)
with q1:
    if gx:
        ok = gx.get("success")
        metric_card("Great Expectations",
                    f"{gx.get('successful', '?')}/{gx.get('evaluated', '?')} passed",
                    "data contract gate", tone="ok" if ok else "bad")
    else:
        metric_card("Great Expectations", "n/a", "validation result not found")
with q2:
    metric_card("Pipeline flows", f"{len(rows)}", "source -> bronze -> silver -> gold -> serving")
with q3:
    metric_card("Warehouse", "DuckDB", "warehouse of record")

st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
section_heading("Run status by flow",
                "Real-time run status across sources, bronze, silver, gold, and dashboard serving; "
                "the table names the runtime responsible for each movement.")
_pf = pipeline_status_frame()
st.plotly_chart(dag_chart(_pf), use_container_width=True, key="td_sankey")
_, _tzcol = st.columns([3, 1])
with _tzcol:
    _tz_label = st.selectbox("Last-run times in", list(TZ_CHOICES), index=0, key="td_last_run_tz")
styled_table(pipeline_status_table(_pf, TZ_CHOICES[_tz_label]))

st.caption("For source contracts, dbt models, reconciliation, and the engineering stack, open the "
           "Data Engineering surface.")

page_footer()
