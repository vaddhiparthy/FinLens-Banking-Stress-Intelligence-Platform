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
        row = scenario.latest_known_row_for_cert(int(cert)) or scenario.latest_row_for_cert(int(cert))
        result = scenario.score_features(row["features"]) if row else None
    except Exception:  # noqa: BLE001
        result = None
    st.markdown(f'<div class="dash-title">{bank.title()}</div>'
                f'<div class="dash-sub">FDIC CERT {cert}'
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
        st.plotly_chart(mc.probability_gauge(prob, thr, MODE), use_container_width=True,
                        key="inf_gauge")
    with scol:
        fig = _shap_diverging(result.get("reasons", []))
        if fig is not None:
            st.markdown("**What drives this score** "
                        "<span title='Each bar is a feature\\'s SHAP contribution to THIS score. "
                        "Red bars (right) pushed the risk up; green bars (left) pulled it down. "
                        "Longer = bigger influence.' style='cursor:help;color:#bf6d47;'>ⓘ</span>",
                        unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, key="inf_shap")


st.markdown('<div class="dash-title">AI Inference</div>'
            '<div class="dash-sub">Interrogate any U.S. bank. The model read renders live on the '
            'left as you chat.</div>', unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("chat_history", [])
ss.setdefault("chat_live_count", 0)

left, right = st.columns([2.6, 1], gap="large")

with right:
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
            ss.chat_history.append({"role": "assistant", "content": out.get("answer", ""), "out": out})
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
