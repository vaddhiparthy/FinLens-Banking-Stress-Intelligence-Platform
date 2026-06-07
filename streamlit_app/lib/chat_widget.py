"""Floating, rate-limited FinLens assistant, shown bottom-right on every page.

Backed by the local $0 RAG path (rag.trace.traced_answer): retrieval and citations are real,
synthesis is a local Ollama model with a fully-cited extractive fallback. Common questions are
answered instantly from a committed cache; live questions are capped per session. When a question
names a bank, the assistant offers a one-click full institutional report.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

MAX_LIVE_QUERIES = 10
# Custom chat avatars (replaces Streamlit's default robot icon).
_AVATAR = {"assistant": "🏦", "user": "🙋"}
_PROJECT_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()
)

@st.cache_resource(show_spinner=False)
def _backend():
    from rag.trace import traced_answer
    return traced_answer


@st.cache_data(show_spinner=False)
def _demo_cache() -> dict:
    import json
    p = _PROJECT_ROOT / "rag" / "demo_answers.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _with_bank(out: dict, question: str) -> dict:
    """Ensure a bank-related answer carries bank_name/bank_cert so the 'full report' button
    renders (cached demo answers don't include these)."""
    if not out.get("bank_name"):
        try:
            from rag.graph import _detect_bank
            hit = _detect_bank(question)
            if hit:
                out = {**out, "bank_cert": hit[0], "bank_name": hit[1]}
        except Exception:  # noqa: BLE001
            pass
    return out


def _ask(question: str, *, example: bool) -> dict:
    """Starter examples are free (cached or run without spending budget); user-typed questions
    count against the per-session live budget. Bank questions answer instantly (deterministic,
    model-grounded); only open-ended questions hit the local LLM."""
    demo = _demo_cache()
    if question in demo:
        return _with_bank({**demo[question], "question": question}, question)
    if not example:
        st.session_state["chat_live_count"] = st.session_state.get("chat_live_count", 0) + 1
    try:
        return _with_bank(_backend()(question), question)
    except Exception as exc:  # noqa: BLE001
        return {"question": question, "answer": f"The local assistant is unavailable: {exc}",
                "citations": [], "used_llm": False}


def _render_answer(out: dict, idx: int) -> None:
    st.markdown(out.get("answer", ""))
    mp = out.get("model_pred")
    if mp:
        st.caption(
            f"Live model score for {out.get('bank_name', 'the named bank')} as of "
            f"{mp.get('quarter')}: {mp.get('probability', 0):.2%} four-quarter distress "
            f"probability (review threshold {mp.get('threshold', 0):.0%})."
        )
    cits = out.get("citations") or []
    if cits:
        with st.expander(f"Sources ({len(cits)})"):
            for c in cits:
                if isinstance(c, str) and c.startswith("http"):
                    st.markdown(f"- [{c}]({c})")
                else:
                    st.markdown(f"- `{c}`")
    bank = out.get("bank_name")
    cert = out.get("bank_cert")
    if bank:
        if st.button(f"Open full report on {bank}", key=f"chat_report_{idx}",
                     use_container_width=True):
            st.session_state["report_bank"] = bank
            if cert is not None:
                st.session_state["report_cert"] = cert
            st.switch_page("pages/8_Bank_Report.py")


def render_chat_widget() -> None:
    ss = st.session_state
    ss.setdefault("chat_open", False)
    ss.setdefault("chat_history", [])
    ss.setdefault("chat_live_count", 0)

    if not ss.chat_open:
        with st.container(key="finlens_chat_closed"):
            if st.button("Ask FinLens", key="chat_launch_btn"):
                ss.chat_open = True
                st.rerun()
        return

    with st.container(key="finlens_chat_open"):
        head_l, head_r = st.columns([5, 1], vertical_alignment="center")
        head_l.markdown('<div class="finlens-chat-title">FinLens Assistant</div>',
                        unsafe_allow_html=True)
        if head_r.button("✕", key="chat_close_btn", help="Close"):
            ss.chat_open = False
            st.rerun()
        if not ss.chat_history:
            with st.chat_message("assistant", avatar=_AVATAR["assistant"]):
                st.markdown(
                    "Hi. Ask me about any U.S. bank (for example, _Tell me about Comerica Bank_ "
                    "or _Why did Silicon Valley Bank fail?_), or about the model and the data. "
                    "Answers are grounded in the live model and regulator filings, and run "
                    "locally at no cost."
                )

        for i, msg in enumerate(ss.chat_history):
            with st.chat_message(msg["role"], avatar=_AVATAR.get(msg["role"])):
                if msg["role"] == "assistant" and isinstance(msg.get("out"), dict):
                    _render_answer(msg["out"], i)
                else:
                    st.markdown(msg["content"])

        remaining = MAX_LIVE_QUERIES - ss.chat_live_count
        if remaining <= 0:
            st.info(f"Live-question limit reached ({MAX_LIVE_QUERIES} per session). "
                    "Refresh the page to start a new session.")
        else:
            prompt = st.chat_input(f"Ask a question  ·  {remaining} live left")
            if prompt:
                with st.spinner("Retrieving filings, scoring the bank, synthesizing locally…"):
                    out = _ask(prompt, example=False)
                ss.chat_history.append({"role": "user", "content": prompt})
                ss.chat_history.append({"role": "assistant", "content": out.get("answer", ""),
                                        "out": out})
                st.rerun()
