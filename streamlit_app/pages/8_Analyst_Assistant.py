# ruff: noqa: E402
"""FullLens Analyst Assistant (Capstone 3): a cited RAG chatbot over the regulator-sourced
failure corpus + the live model. Retrieval and citations are real; answer synthesis uses a
local Ollama model when one is reachable, otherwise a fully-cited extractive fallback ($0)."""

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

from streamlit_app.lib.page_shell import BUSINESS_PAGE, page_footer, page_intro, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import chart_note, inject_styles

st.set_page_config(page_title="FinLens | Analyst Assistant", layout="wide",
                   initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=True))
top_navigation("analyst", BUSINESS_PAGE)
record_page_view("analyst_assistant", BUSINESS_PAGE)

page_intro(
    "Business Surface",
    "Analyst Assistant",
    "Ask a banking-risk question. The assistant retrieves from a corpus of regulator failure "
    "reports (FDIC OIG, OCC, Federal Reserve) and the model's own findings, pulls the live "
    "distress score for any bank you name, and answers with citations. Retrieval and citations "
    "are real; the written answer is synthesized by a local model when one is available, "
    "otherwise shown as the cited source excerpts.",
)


@st.cache_resource(show_spinner=False)
def _rag():
    from rag.trace import traced_answer
    return traced_answer


examples = [
    "Why did Silicon Valley Bank fail?",
    "What caused Heartland Tri-State Bank to fail?",
    "What is the addressable PR-AUC and how does it differ from pooled?",
    "Did the GRU sequence model beat the gradient-boosted model?",
]
q = st.text_input("Your question", value=examples[0], key="aa_q",
                  placeholder="e.g. Why did Silicon Valley Bank fail?")
st.caption("Examples: " + "  ·  ".join(examples))

if st.button("Ask", type="primary") and q.strip():
    try:
        traced_answer = _rag()
        with st.spinner("Retrieving sources, scoring the bank, synthesizing…"):
            out = traced_answer(q.strip())
    except Exception as e:  # noqa: BLE001
        st.error(f"Assistant backend unavailable: {e}")
        st.stop()

    mode = "local LLM" if out.get("used_llm") else "extractive (no local LLM reachable)"
    st.markdown(f"**Answer** ({mode}):")
    st.write(out["answer"])

    mp = out.get("model_pred")
    if mp:
        st.info(f"Live FullLens model score for the named bank as of {mp['quarter']}: "
                f"calibrated 4-quarter distress probability {mp['probability']:.3f} "
                f"(review threshold {mp['threshold']:.2f}). Note: a low score on a known "
                "rate/liquidity or fraud failure is the decomposition's point, not an error.")

    if out.get("citations"):
        st.markdown("**Sources**")
        for c in out["citations"]:
            st.markdown(f"- {c}")

    tr = out.get("trace", {})
    st.caption(f"Traced: {tr.get('latency_ms', '?')} ms, {tr.get('n_retrieved', 0)} docs "
               f"retrieved, {tr.get('n_citations', 0)} citations, cost $0 (local).")

chart_note(
    "Please read this",
    "Answers are grounded in public regulator documents and a backtested model; this is a "
    "research demonstration, not financial, investment, deposit, or supervisory advice, and "
    "not a rating. For decisions about a bank rely only on official U.S. regulator sources.",
)

page_footer()
