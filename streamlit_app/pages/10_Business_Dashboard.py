# ruff: noqa: E402
"""Business Dashboard: the most decision-relevant business visualizations on one page, no write-ups.

Curated from the Business surface (Stress Pulse, Failure Forensics, Macro Transmission), grouped
headline -> detail. Reads the live Gold warehouse; honest-empty if a table is missing.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit_app.lib import business_charts as bc
from streamlit_app.lib.data import load_failures, load_metrics, load_stress_pulse
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, metric_card, section_heading

st.set_page_config(page_title="FinLens | Business Dashboard", layout="wide",
                   initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
home_navigation()
record_page_view("business_dashboard", "business")

st.markdown('<div class="dash-title">Business Dashboard</div>'
            '<div class="dash-sub">The banking story at a glance: earnings, asset quality, the 2023 '
            'rate shock, failures, and the macro backdrop. Live public data; no commentary.</div>',
            unsafe_allow_html=True)

stress = load_stress_pulse()
failures = load_failures()
metrics = load_metrics()


def _fmt(v, prefix="", suffix="", dp=2):
    try:
        return f"{prefix}{float(v):,.{dp}f}{suffix}"
    except (TypeError, ValueError):
        return "n/a"


# ---- headline KPIs ----
k1, k2, k3, k4, k5 = st.columns(5)
if not stress.empty:
    latest = stress.iloc[-1]
    pb = stress["problem_banks"].dropna() if "problem_banks" in stress else stress.iloc[0:0]
    nc = stress["noncurrent_rate"].dropna() if "noncurrent_rate" in stress else stress.iloc[0:0]
    with k1:
        metric_card("Aggregate net income", _fmt(latest.get("net_income"), prefix="$", suffix="B", dp=1),
                    f"as of {latest.get('quarter', '')}")
    with k2:
        metric_card("Industry ROA", _fmt(latest.get("roa"), suffix="%"), "return on assets")
    with k3:
        metric_card("Industry NIM", _fmt(latest.get("nim"), suffix="%"), "net interest margin")
    with k4:
        if len(pb):
            metric_card("Problem banks", f"{pb.iloc[-1]:,.0f}", "FDIC problem list")
        elif len(nc):
            metric_card("Noncurrent loan rate", f"{nc.iloc[-1]:.2f}%", "credit stress signal")
        else:
            metric_card("Problem banks", "n/a", "not in current feed")
else:
    with k1:
        metric_card("Stress pulse", "n/a", "no data loaded")
with k5:
    metric_card("FDIC failures", f"{len(failures):,}" if not failures.empty else "n/a",
                "cumulative since 2000")

st.markdown('<div class="dash-rule"></div>', unsafe_allow_html=True)

# ---- results (the signals that matter) ----
section_heading("Profitability & asset quality", "Industry earnings and the credit-stress signals.")
r1, r2 = st.columns(2)
with r1:
    if bc.has_chart_data(stress, ["net_income", "roa"]):
        st.plotly_chart(bc.earnings_chart(stress), use_container_width=True, key="dash_earn")
    else:
        st.caption("Earnings data unavailable.")
with r2:
    if bc.has_chart_data(stress, ["noncurrent_rate", "nco_rate"]):
        st.plotly_chart(bc.asset_quality_chart(stress), use_container_width=True, key="dash_aq")
    else:
        st.caption("Asset-quality data unavailable.")

r3, r4 = st.columns(2)
with r3:
    if bc.has_chart_data(stress, ["afs_losses", "htm_losses"]):
        st.plotly_chart(bc.unrealized_losses_chart(stress), use_container_width=True, key="dash_afs")
    else:
        st.caption("Unrealized-loss data unavailable.")
with r4:
    if not failures.empty:
        st.plotly_chart(bc.state_map(failures), use_container_width=True, key="dash_map")
    else:
        st.caption("Failure data unavailable.")

st.markdown('<div class="dash-rule"></div>', unsafe_allow_html=True)

# ---- supporting context ----
section_heading("Macro backdrop & resolutions", "The conditions around the banks, and who absorbed "
                "the failures.")
s1, s2 = st.columns(2)
with s1:
    if not metrics.empty:
        st.caption("Macro signals (FRED)")
        for sid, label in (("UNRATE", "Unemployment %"), ("DGS10", "10-year Treasury %"),
                           ("BAA10Y", "Baa credit spread %")):
            sub = metrics[metrics["series_id"] == sid].sort_values("date")
            if not sub.empty:
                st.caption(label)
                st.line_chart(sub.set_index("date")["value"], height=110)
    else:
        st.caption("Macro data unavailable.")
with s2:
    if not failures.empty and "acquirer" in failures and failures["acquirer"].notna().any():
        st.plotly_chart(bc.acquirer_chart(failures), use_container_width=True, key="dash_acq")
    else:
        st.caption("Acquirer detail not standardized in the current feed.")

page_footer()
