# ruff: noqa: E402
"""Dynamic institutional risk report for any U.S. bank in the panel.

Every field is filled in real time from the live model and the governed panel: the calibrated
4-quarter distress probability, the SHAP risk drivers, the bank's CAMELS-aligned ratios against
peer medians, and (for banks that actually failed) the regulator-stated cause with its citation.
Reached standalone via a bank picker, or from the floating assistant ("full report on <bank>").
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from finlens_ml import scenario
from finlens_ml.scenario import humanize_feature
from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_footer, page_intro, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_palette, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, metric_card, section_heading

st.set_page_config(page_title="FinLens | Bank Report", layout="wide",
                   initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("predictive", BUSINESS_PAGE)
record_page_view("bank_report", BUSINESS_PAGE)
MODE = get_theme_mode()
PAL = get_palette(MODE)


@st.cache_data(show_spinner=False)
def _directory() -> pd.DataFrame:
    return scenario.live_bank_directory()


@st.cache_data(show_spinner=False)
def _peer_medians() -> dict:
    return scenario.baseline_features()


@st.cache_data(show_spinner=False)
def _failure_causes() -> pd.DataFrame:
    try:
        from finlens_ml.failure_cause_labels import load_failure_causes
        return load_failure_causes()
    except Exception:
        return pd.DataFrame()


# Key interpretable ratios to profile against peers (subset of the feature contract).
_PROFILE_FEATURES = [
    "tier1_leverage", "tier1_rwa_ratio", "total_capital_ratio", "noncurrent_loans_ratio",
    "net_charge_offs_ratio", "roa", "nim", "uninsured_deposit_ratio",
    "securities_to_assets", "loans_to_deposits",
]

page_intro(
    "Institutional Risk Report",
    "Bank Distress Report",
    "A point-in-time institutional assessment generated from the live FinLens model and the "
    "governed Call Report panel. Figures are model estimates on the most recent available "
    "filing, not ratings, supervisory findings, or advice.",
)


# ---- resolve the target bank ----
dir_df = _directory()
names = dir_df["bank_name"].tolist()

# A bank handed over from the assistant takes precedence, then a manual picker.
pending_cert = st.session_state.pop("report_cert", None)
pending_name = st.session_state.pop("report_bank", None)
default_idx = 0
if pending_cert is not None and (dir_df["cert"] == int(pending_cert)).any():
    default_idx = int(dir_df.index[dir_df["cert"] == int(pending_cert)][0])
elif pending_name:
    matches = dir_df.index[dir_df["bank_name"].str.lower() == str(pending_name).lower()]
    if len(matches):
        default_idx = int(matches[0])

pick = st.selectbox("Select an institution", names, index=min(default_idx, len(names) - 1),
                    key="report_pick")
row_cert = int(dir_df.iloc[names.index(pick)]["cert"])

rec = scenario.latest_row_for_cert(row_cert)
if not rec:
    st.warning("No filing on record for that institution.")
    page_footer()
    st.stop()

scored = scenario.score_features(rec["features"])
prob = scored["probability"]
threshold = scored["threshold"]
flagged = scored["flagged"]
causes = _failure_causes()
crow = causes[causes["cert"] == row_cert] if not causes.empty else pd.DataFrame()
ever_failed = not crow.empty or bool(rec.get("actual_label_4"))


# ---- header band ----
state = rec.get("state") or "—"
quarter = rec.get("quarter") or "—"
tier = ("Elevated" if flagged else ("Watch" if prob >= threshold * 0.5 else "Low"))
tier_color = {"Elevated": PAL["rose"], "Watch": PAL["accent"], "Low": PAL["teal"]}[tier]
st.markdown(
    f'<div style="border:1px solid {PAL["border"]};border-left:5px solid {tier_color};'
    f'border-radius:14px;padding:1rem 1.2rem;margin:.2rem 0 1rem;background:{PAL["content_bg"]}">'
    f'<div style="font-size:1.45rem;font-weight:800;color:{PAL["text_main"]}">{pick}</div>'
    f'<div style="color:{PAL["text_muted"]};font-size:.9rem;margin-top:.15rem">'
    f'FDIC CERT {row_cert} &nbsp;·&nbsp; {state} &nbsp;·&nbsp; as of {quarter} &nbsp;·&nbsp; '
    f'<b style="color:{tier_color}">{tier} distress signal</b></div></div>',
    unsafe_allow_html=True,
)

# ---- executive assessment ----
section_heading("Executive assessment",
                "The model's calibrated probability that this institution enters failure within "
                "four quarters of the filing above, against the review threshold.")
k1, k2, k3, k4 = st.columns(4)
with k1:
    metric_card("4-quarter distress probability", f"{prob:.2%}",
                "calibrated, not a forecast of certain failure")
with k2:
    metric_card("Review threshold", f"{threshold:.0%}",
                "flagged for review above this")
with k3:
    metric_card("Signal", "Flagged" if flagged else "Not flagged",
                "relative to threshold")
with k4:
    outcome = ("Failed within 4q" if rec.get("actual_label_4") == 1
               else ("Survived the window" if rec.get("outcome_known") else "Outcome not yet elapsed"))
    metric_card("Actual outcome", outcome, "backtest where the window has closed")

_verdict = (
    f"As of {quarter}, the model assigns **{pick}** a {prob:.2%} four-quarter distress "
    f"probability, {'above' if flagged else 'below'} the {threshold:.0%} review threshold. "
    "Bank failure is a sub-1% base-rate event, so even an elevated estimate means the "
    "institution is most probably sound; the figure is a screening signal, not a prediction "
    "of certain failure."
)
st.markdown(_verdict)


# ---- risk drivers (SHAP) ----
reasons = [r for r in scored.get("reasons", []) if r.get("shap") is not None]
if reasons:
    section_heading("Key risk drivers",
                    "The features moving this institution's score most, from the model's SHAP "
                    "attribution. Positive bars raise estimated risk; negative bars lower it.")
    rdf = pd.DataFrame([{
        "Driver": humanize_feature(r["feature"]),
        "Value": (f"{r['value']:.3f}" if isinstance(r.get("value"), (int, float)) else "—"),
        "Contribution": round(float(r["shap"]), 4),
        "Direction": ("raises risk" if r["shap"] > 0 else "lowers risk"),
    } for r in reasons])
    cda, cdb = st.columns([1.15, 1])
    with cda:
        fig = go.Figure()
        ordered = rdf.sort_values("Contribution")
        fig.add_bar(
            x=ordered["Contribution"], y=ordered["Driver"], orientation="h",
            marker_color=[PAL["rose"] if v > 0 else PAL["teal"] for v in ordered["Contribution"]],
        )
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PAL["text_main"]), title="SHAP contribution to the distress score",
        )
        fig.update_xaxes(title="contribution", zeroline=True, zerolinecolor=PAL["border"])
        st.plotly_chart(fig, use_container_width=True)
    with cdb:
        st.dataframe(rdf, hide_index=True, use_container_width=True, height=320)


# ---- financial profile vs peers ----
peers = _peer_medians()
prof_rows = []
for f in _PROFILE_FEATURES:
    v = rec["features"].get(f)
    med = peers.get(f)
    if v is None or med is None:
        continue
    prof_rows.append({
        "Ratio": humanize_feature(f),
        "This bank": round(float(v), 4),
        "Peer median": round(float(med), 4),
        "vs peers": f"{(float(v) - float(med)):+.4f}",
    })
if prof_rows:
    section_heading("Financial profile against peers",
                    "Selected CAMELS-aligned Call Report ratios for this institution against the "
                    "panel median (all U.S. banks, all quarters).")
    st.dataframe(pd.DataFrame(prof_rows), hide_index=True, use_container_width=True)


# ---- regulatory record (known failures) ----
if not crow.empty:
    c = crow.iloc[0]
    section_heading("Regulatory record",
                    "For institutions that failed, the regulator-determined primary cause and the "
                    "source document.")
    rc1, rc2 = st.columns([1, 1.3])
    with rc1:
        metric_card("Failure year", str(c.get("failure_year", "—")),
                    f"visibility class: {c.get('visibility', '—')}")
        metric_card("Source confidence", str(c.get("confidence", "—")).title(),
                    str(c.get("source_type", "")))
    with rc2:
        st.markdown(f"**Regulator-determined cause:** {c.get('cause', '—')}")
        if isinstance(c.get("quote"), str) and c["quote"].strip():
            st.markdown(f"> {c['quote']}")
        if isinstance(c.get("source_url"), str) and c["source_url"].startswith("http"):
            st.markdown(f"[Source document]({c['source_url']})")


# ---- predictive context ----
section_heading("How to read this report",
                "The model context behind the number above.")
st.markdown(
    "- The score is a **calibrated probability** from a monotone, bagged gradient-boosted hazard "
    "model evaluated out-of-time; a 5% score corresponds to roughly a 5% historical failure rate.\n"
    "- Failure is **rare** (out-of-time base rate ~0.06%), so precision is low in absolute terms; "
    "the model is used to rank a review budget, not to make binary calls.\n"
    "- Some failures are **structurally invisible** on quarterly financials (fraud, sudden runs); "
    "the model is scoped to credit-visible distress, which is why a known failure can still score "
    "low. See the failure-type decomposition on the AI Engineering surface.\n"
    "- This is a research demonstration, not financial, investment, deposit, or supervisory advice, "
    "and not a rating. For decisions about a bank, rely only on official U.S. regulator sources."
)

page_footer()
