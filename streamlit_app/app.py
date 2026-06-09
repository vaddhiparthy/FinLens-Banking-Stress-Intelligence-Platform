# ruff: noqa: E402,E501

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

from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.landing import render_landing
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles

st.set_page_config(
    page_title="FinLens: Banking Stress Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("home", "landing")

st.markdown(
    """
    <style>
    div[role="dialog"] { border-radius: 18px !important; }
    div[role="dialog"] button[aria-label="Close"] { display: none !important; }
    div[role="dialog"] [data-testid="stVerticalBlock"] { gap: .6rem !important; }
    div[role="dialog"] div[data-testid="stButton"] > button {
        background: #bf6d47 !important; border: 1px solid #bf6d47 !important;
        border-radius: 11px !important; box-shadow: 0 8px 20px rgba(15,23,42,.16) !important;
        margin-top: .2rem;
    }
    div[role="dialog"] div[data-testid="stButton"] > button:hover {
        background: #a85b38 !important; border-color: #a85b38 !important;
    }
    div[role="dialog"] div[data-testid="stButton"] > button,
    div[role="dialog"] div[data-testid="stButton"] > button * {
        color: #fff !important; -webkit-text-fill-color: #fff !important; font-weight: 700 !important;
    }
    div[role="dialog"] div[data-testid="stButton"] > button * { background: transparent !important; }
    .gate-brand { font-weight: 800; letter-spacing: .02em; color: #bf6d47; font-size: .82rem;
        text-transform: uppercase; margin-bottom: .1rem; }

    /* Single clean window: vertically center the whole content group so top and bottom whitespace
       are balanced (no giant forehead, no dead space dumped under the footer). */
    .block-container { padding-top: .4rem !important; padding-bottom: .4rem !important;
        min-height: calc(100vh - .8rem); display: flex !important; flex-direction: column; }
    /* the inner vertical block fills the height; center its children so whitespace is balanced */
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
        justify-content: center !important; }
    .nav-anchor { height: 0; margin: 0; }
    /* full-width intro (NOT constrained/centered), ~1.5-line gap under the header */
    .home-intro { text-align: left; color: #6a6b74; font-size: 1.02rem; line-height: 1.65;
        margin: 2.4rem 0 1.8rem; max-width: none; }
    /* a touch of separation from the footer */
    .site-footer { margin-top: 1.6rem !important; }
    /* Browse rectangle */
    .st-key-browse_box { border: 1px solid #e4d7c6; border-radius: 18px; background: #fffaf3;
        padding: 1.1rem 1.6rem; box-shadow: 0 10px 30px rgba(15,23,42,.06); }
    .browse-col-h { font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase;
        color: #bf6d47; margin: .1rem 0 .6rem; }
    /* full-height vertical divider = border on the first column (auto-centered, equal-height cols) */
    .st-key-browse_box [data-testid="stHorizontalBlock"] { align-items: stretch; }
    .st-key-browse_box [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
        border-right: 1px solid #e4d7c6; padding-right: 1.6rem; }
    .st-key-browse_box [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
        padding-left: 1.6rem; }
    /* Browse links: clean text + accent hover (no boxes); description lives in the button help tip */
    div[class*="st-key-nav_"] button {
        background: transparent !important; border: none !important; box-shadow: none !important;
        color: #1f2933 !important; font-weight: 700 !important; font-size: 1rem !important;
        text-align: left !important; justify-content: flex-start !important;
        padding: .3rem 0 !important; min-height: 0 !important;
    }
    /* keep the chevron and the label as one left-packed unit (Streamlit centers the inner flex) */
    div[class*="st-key-nav_"] button > div {
        justify-content: flex-start !important; width: auto !important; }
    div[class*="st-key-nav_"] button::before {
        content: "›"; margin-right: .45rem; color: #bf6d47; font-weight: 800; }
    div[class*="st-key-nav_"] button:hover,
    div[class*="st-key-nav_"] button:hover * {
        color: #bf6d47 !important; -webkit-text-fill-color: #bf6d47 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.dialog("Important Use Notice", width="small", dismissible=False)
def _legal_disclaimer() -> None:
    st.markdown('<div class="gate-brand">FinLens · Banking Stress Intelligence</div>',
                unsafe_allow_html=True)
    st.markdown(
        """
        FinLens is a personal portfolio project built to demonstrate data engineering,
        public-data integration, and banking analytics presentation. It is not affiliated
        with or endorsed by any regulator or financial institution.

        Do not use this project as financial, investment, regulatory, or supervisory advice.
        For decisions about a bank, deposit, investment, or financial institution, rely only
        on official U.S. government and regulator sources.
        """,
    )
    if st.button("I understand", key="accept_home_disclaimer", use_container_width=True,
                 type="primary"):
        st.session_state["home_disclaimer_accepted"] = True
        st.query_params["ack"] = "1"  # survive a page refresh / new session too
        st.rerun()


def _disclaimer_persistence() -> None:
    """Remember acceptance in the browser (localStorage) so the use-notice shows ONCE, ever — it
    survives server restarts, refreshes, new sessions, and arriving at home from another page.
    Streamlit's sandboxed component iframe can't redirect the top frame, but it CAN read/write the
    parent DOM (same-origin), so: if the browser already accepted, remove the dialog the moment it
    renders; and persist acceptance when 'I understand' is clicked."""
    import streamlit.components.v1 as _components
    _components.html(
        """
        <script>
        (function () {
          var doc; try { doc = window.parent.document; } catch (e) { return; }
          var KEY = 'finlens_disclaimer_ack';
          function accepted() { try { return window.localStorage.getItem(KEY) === '1'; }
                                catch (e) { return false; } }
          function isNotice(el) { return /Important Use Notice/i.test(el.textContent || ''); }
          function kill() {
            doc.querySelectorAll('[role="dialog"]').forEach(function (d) {
              if (isNotice(d)) {
                var modal = d.closest('[data-baseweb="modal"]') || d.closest('[data-testid="stDialog"]');
                (modal || d).remove();
              }
            });
          }
          if (accepted()) {
            kill();
            var obs = new MutationObserver(kill);
            obs.observe(doc.body, { childList: true, subtree: true });
            setTimeout(function () { obs.disconnect(); }, 6000);
          }
          // persist as soon as the user accepts (and on any future render where ack=1 is in the URL)
          if (new URLSearchParams(doc.location.search).get('ack') === '1') {
            try { window.localStorage.setItem(KEY, '1'); } catch (e) {}
          }
          doc.addEventListener('click', function (e) {
            var b = e.target.closest('button');
            if (b && /I understand/i.test(b.textContent || '')) {
              try { window.localStorage.setItem(KEY, '1'); } catch (e) {}
            }
          }, true);
        })();
        </script>
        """,
        height=0,
    )


_disclaimer_persistence()
# Accepted if the in-session flag (internal navigation) or the URL flag (refresh) is set; the
# localStorage layer above removes the dialog for browsers that accepted in any prior session.
_acked = st.session_state.get("home_disclaimer_accepted") or st.query_params.get("ack") == "1"
if not _acked:
    _legal_disclaimer()

home_navigation()

# The landing is a bento showcase: real-data preview tiles (chosen by adversarial value+aesthetic
# review) that click through to the live surfaces. See streamlit_app/lib/landing.py.
render_landing()

page_footer()
