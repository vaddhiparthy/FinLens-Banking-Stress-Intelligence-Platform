# ruff: noqa: E402
"""AI Inference: a dedicated chat console. Right column is the chat; the left column is a live
'glorified filter' preview that renders the resolved bank's facts, distress score, and SHAP drivers
as you ask. Backed by the cited RAG path + OpenRouter, with a silent per-session cap.
"""

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit_app.lib import chat_widget as cw
from streamlit_app.lib import ml_charts as mc
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, section_heading

st.set_page_config(page_title="FinLens | AI Inference", layout="wide",
                   initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
home_navigation()
record_page_view("ai_inference", "ai")
MODE = get_theme_mode()


def _shap_diverging(reasons: list[dict]):
    """Two-directional SHAP bar: red = pushed risk up, green = pushed risk down."""
    import finlens_ml.scenario as scenario
    rows = [r for r in reasons if r.get("shap") is not None][:8]
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: r["shap"])
    labels = [scenario.humanize_feature(str(r["feature"])) for r in rows]
    vals = [float(r["shap"]) for r in rows]
    colors = ["#be123c" if v > 0 else "#2f8f6b" for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker_color=colors,
                           hovertemplate="%{y}: %{x:+.3f}<extra></extra>"))
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#1f2933"),
                      xaxis=dict(title="SHAP push on this score (+ raises risk, − lowers)",
                                 zeroline=True, zerolinecolor="#cbb9a6"))
    return fig


_PROFILE_LITE = [
    ("roa", "Return on assets"), ("nim", "Net interest margin"),
    ("noncurrent_loans_ratio", "Noncurrent loans"), ("tier1_leverage", "Tier-1 leverage"),
    ("uninsured_deposit_ratio", "Uninsured deposits"), ("loans_to_deposits", "Loans / deposits"),
]


def _render_bank_facts(cert: int, bank: str, row: dict, result: dict) -> None:
    """Deeper insights for the resolved bank: what actually happened + key ratios vs peers,
    using the same governed sources as the full Bank Report."""
    import pandas as pd
    import finlens_ml.scenario as scenario

    # ---- what actually happened (real backtest outcome + regulator-stated cause if it failed) ----
    label = row.get("actual_label_4")
    known = row.get("outcome_known")
    outcome = ("Failed within four quarters of this filing" if label == 1
               else "Survived the four-quarter window" if known
               else "Outcome window has not fully elapsed yet")
    st.markdown("**What actually happened**")
    cause_shown = False
    try:
        from finlens_ml.failure_cause_labels import load_failure_causes
        causes = load_failure_causes()
        crow = causes[causes["cert"] == cert] if not causes.empty else pd.DataFrame()
        if not crow.empty:
            c = crow.iloc[0]
            st.markdown(f"{outcome}. Regulator-determined cause: **{c.get('cause', '—')}** "
                        f"({c.get('failure_year', '—')}).")
            if isinstance(c.get("quote"), str) and c["quote"].strip():
                st.caption(f"“{c['quote'].strip()}”")
            cause_shown = True
    except Exception:  # noqa: BLE001
        pass
    if not cause_shown:
        st.caption(outcome + ". Backtest label from the governed panel where the window has closed.")

    # ---- key ratios vs peer medians (compact subset of the Bank Report profile) ----
    try:
        peers = scenario.baseline_features()
    except Exception:  # noqa: BLE001
        peers = {}
    prof = []
    for f, lbl in _PROFILE_LITE:
        v, med = row["features"].get(f), peers.get(f)
        if v is None or med is None:
            continue
        prof.append({"Ratio": lbl, "This bank": round(float(v), 4),
                     "Peer median": round(float(med), 4),
                     "vs peers": f"{float(v) - float(med):+.4f}"})
    if prof:
        st.markdown("**Key ratios vs peer medians**")
        st.dataframe(pd.DataFrame(prof), hide_index=True, use_container_width=True)

    if st.button("Open the full Bank Report →", key="inf_open_report",
                 use_container_width=True):
        st.session_state["report_cert"] = cert
        st.session_state["report_bank"] = bank
        st.switch_page("pages/8_Bank_Report.py")


def _render_preview(out: dict) -> None:
    """Left preview: when a bank is resolved, show its live score + drivers."""
    bank = out.get("bank_name")
    cert = out.get("bank_cert")
    if not bank or cert is None:
        section_heading("Live preview", "Ask about a U.S. bank on the right and its model read "
                        "appears here: score, risk tier, and what drives it.")
        if out.get("answer"):
            st.markdown(out["answer"])
        return
    try:
        import finlens_ml.scenario as scenario
        # Same source as the full Bank Report so the read matches across surfaces.
        row = scenario.latest_row_for_cert(int(cert)) or scenario.latest_known_row_for_cert(int(cert))
        result = scenario.score_features(row["features"]) if row else None
    except Exception:  # noqa: BLE001
        row, result = None, None
    st.markdown(f'<div class="dash-title">{bank.title()}</div>'
                f'<div class="dash-sub">FDIC CERT {cert}'
                + (f" · {row.get('state')}" if row and row.get("state") else "")
                + (f" · scored as of {row.get('quarter')}" if row else "") + "</div>",
                unsafe_allow_html=True)
    if result is None:
        st.info("No scoreable quarter for this institution.")
        if out.get("answer"):
            st.markdown(out["answer"])
        return
    prob, thr = result["probability"], result["threshold"]
    tier, cls = (("HIGH RISK", "danger") if prob >= thr
                 else ("ELEVATED", "warn") if prob >= thr / 2 else ("LOW RISK", "ok"))
    # verdict headline at the top of the card, then gauge + drivers side by side (no dead space)
    st.markdown(
        f'<div class="ew-badge ew-{cls}">{tier}</div>'
        f'<div class="ew-sub">Calibrated probability of financial distress within four '
        f'quarters: <b>{prob * 100:.3f}%</b> ({prob * 1e4:.1f} bps). Review threshold '
        f'{thr * 100:.0f}%.</div>', unsafe_allow_html=True)
    gcol, scol = st.columns([1, 1.5], vertical_alignment="top")
    with gcol:
        # zoom the dial so the small probability + the threshold bands are readable, not crushed
        # near zero on a 0-100% axis (the gauge's cap is built for exactly this)
        cap = max(thr * 100 * 1.5, prob * 100 * 3, 15.0)
        st.plotly_chart(mc.probability_gauge(prob, thr, MODE, cap=cap), use_container_width=True,
                        key="inf_gauge")
    with scol:
        fig = _shap_diverging(result.get("reasons", []))
        if fig is not None:
            st.markdown("**What drives this score**")
            st.caption("Each bar is a feature's push on THIS bank's score: red (right) raised the "
                       "risk, green (left) lowered it; longer = bigger effect.")
            st.plotly_chart(fig, use_container_width=True, key="inf_shap")
    _render_bank_facts(int(cert), bank, row, result)


st.markdown('<div class="dash-title">AI Inference</div>'
            '<div class="dash-sub">Interrogate any U.S. bank. The model read renders live on the '
            'left as you chat.</div>', unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .st-key-inf_chat_panel {
        border: 1px solid #e4d7c6; border-radius: 16px; background: #fffaf3;
        padding: 1rem 1.1rem; box-shadow: 0 10px 30px rgba(15, 23, 42, .06);
    }
    .st-key-inf_chat_panel [data-testid="stChatInput"] { margin-top: .4rem; }
    .inf-disclaimer { color: #7f6b58; font-size: .76rem; text-align: center; margin-top: .6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state
ss.setdefault("chat_history", [])
ss.setdefault("chat_live_count", 0)

left, right = st.columns([2.6, 1], gap="large")

with right:
    with st.container(key="inf_chat_panel"):
        st.markdown('<div class="finlens-chat-title">Chat</div>', unsafe_allow_html=True)
        if not ss.chat_history:
            with st.chat_message("assistant", avatar=cw._AVATAR["assistant"]):
                st.markdown("Ask about any U.S. bank, the model, or the data. For example: "
                            "_Why did Silicon Valley Bank fail?_")
        for i, msg in enumerate(ss.chat_history):
            with st.chat_message(msg["role"], avatar=cw._AVATAR.get(msg["role"])):
                if msg["role"] == "assistant" and isinstance(msg.get("out"), dict):
                    cw._render_answer(msg["out"], i)
                else:
                    st.markdown(msg["content"])
        if ss.chat_live_count >= cw.MAX_LIVE_QUERIES:
            st.info("You've been rate limited.")
        else:
            prompt = st.chat_input("Ask a question")
            if prompt:
                with st.spinner("Retrieving filings, scoring the bank, synthesizing…"):
                    out = cw._ask(prompt, example=False)
                ss.chat_history.append({"role": "user", "content": prompt})
                ss.chat_history.append({"role": "assistant", "content": out.get("answer", ""),
                                        "out": out})
                st.rerun()
        st.markdown('<div class="inf-disclaimer">AI can and will make mistakes.</div>',
                    unsafe_allow_html=True)

with left:
    last = next((m["out"] for m in reversed(ss.chat_history)
                 if m["role"] == "assistant" and isinstance(m.get("out"), dict)), None)
    if last is None:
        with st.container(border=True):
            section_heading("Live preview", "Ask about a U.S. bank on the right and its model read "
                            "appears here: distress score, risk tier, and the SHAP drivers behind it.")
    else:
        with st.container(border=True):
            _render_preview(last)

page_footer()
