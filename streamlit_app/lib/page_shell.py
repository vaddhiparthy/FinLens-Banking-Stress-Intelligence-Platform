from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

BUSINESS_PAGE = "business"
TECHNICAL_PAGE = "technical"
SIDEBAR_ENABLED = True
AI_PAGE = "ai"  # third surface: Machine Learning / AI engineering


def _set_surface_mode(mode: str) -> None:
    st.session_state["surface_mode"] = mode


def _page_path(page_key: str) -> str:
    page_map = {
        "home": "app.py",
        "overview": "pages/0_Stress_Pulse.py",
        "banks": "pages/1_Failure_Forensics.py",
        "metrics": "pages/2_Macro_Transmission.py",
        "predictive": "pages/3_Early_Warning.py",
        "wiki": "pages/6_Wiki.py",
        "pipeline": "pages/4_Data_Engineering.py",
        "status": "pages/4_Data_Engineering.py",
        "classification": "pages/4_Data_Engineering.py",
        "implementation": "pages/4_Data_Engineering.py",
        "administration": "pages/4_Data_Engineering.py",
        "decisions": "pages/4_Data_Engineering.py",
    }
    return page_map[page_key]


def _business_pages() -> list[tuple[str, str, str, str]]:
    pages = [
        ("overview", "pages/0_Stress_Pulse.py", "Stress Pulse", ":material/space_dashboard:"),
        ("banks", "pages/1_Failure_Forensics.py", "Failure Forensics", ":material/account_balance:"),
        ("metrics", "pages/2_Macro_Transmission.py", "Macro Transmission", ":material/show_chart:"),
        (
            "predictive",
            "pages/3_Early_Warning.py",
            "Early Warning",
            ":material/neurology:",
        ),
        ("wiki", "pages/6_Wiki.py", "Wiki", ":material/menu_book:"),
    ]
    return pages


def _business_sections() -> list[tuple[str, str]]:
    sections = [
        ("overview", "Stress Pulse"),
        ("banks", "Failure Forensics"),
        ("metrics", "Macro Transmission"),
        ("predictive", "Early Warning"),
        ("wiki", "Wiki"),
    ]
    return sections


def _technical_sections() -> list[tuple[str, str]]:
    return [
        ("pipeline", "Live Pipeline"),
        ("classification", "Source Contracts"),
        ("implementation", "Engineering Stack"),
        ("status", "Data Quality"),
        ("decisions", "Architecture Decisions"),
        ("administration", "Administration"),
        ("wiki", "Wiki"),
    ]


def _ai_sections() -> list[tuple[str, str]]:
    return [
        ("pipeline", "AI Pipeline"),
        ("notebook", "Notebook"),
        ("contracts", "Feature Contracts"),
        ("stack", "AI Stack"),
        ("quality", "Model Quality"),
        ("decisions", "Model Decisions"),
        ("administration", "Administration"),
        ("wiki", "Wiki"),
    ]


def get_technical_section() -> str:
    if "technical_section" not in st.session_state:
        st.session_state["technical_section"] = "pipeline"
    return st.session_state["technical_section"]


def get_ai_section() -> str:
    if "ai_section" not in st.session_state:
        st.session_state["ai_section"] = "pipeline"
    return st.session_state["ai_section"]


def _current_section_label(active_page: str, mode: str) -> str:
    if mode == AI_PAGE:
        lookup = dict(_ai_sections())
        return lookup.get(get_ai_section(), "")
    if mode == TECHNICAL_PAGE:
        lookup = dict(_technical_sections())
        return lookup.get(get_technical_section(), "")
    lookup = dict(_business_sections())
    return lookup.get(active_page, "")


@st.fragment(run_every="1s")
def _render_sidebar_clock() -> None:
    now = datetime.now(ZoneInfo("America/New_York"))
    st.markdown(
        f"""
        <div class="sidebar-time">{now.strftime("%A, %B %d, %Y")}</div>
        <div class="sidebar-time">{now.strftime("%I:%M:%S %p ET")}</div>
        """,
        unsafe_allow_html=True,
    )


_SURFACE_META = {
    BUSINESS_PAGE: ("Business", "Banking, risk, and executive view"),
    TECHNICAL_PAGE: ("Data Engineering", "Sourcing, transforms, and serving"),
    AI_PAGE: ("AI Engineering", "The bank-distress model, end to end"),
}


def render_sidebar(active_page: str, mode: str) -> None:
    if not SIDEBAR_ENABLED:
        return
    surface_label, _ = _SURFACE_META.get(mode, _SURFACE_META[BUSINESS_PAGE])
    with st.sidebar:
        st.markdown(
            f"""
            <div class="rail-brand">
                <span class="rail-brand-name">FinLens</span>
                <span class="rail-brand-surface">{surface_label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_sidebar_sections(active_page, mode)
        st.markdown('<div class="rail-foot">', unsafe_allow_html=True)
        _render_sidebar_clock()
        st.markdown(
            '<a class="sidebar-credit" href="https://surya.vaddhiparthy.com" '
            'target="_blank">Built by Sri Surya S. Vaddhiparthy</a></div>',
            unsafe_allow_html=True,
        )


def _render_sidebar_sections(active_page: str, mode: str) -> None:
    """Section navigation rendered as side-tabs in the left rail. The surface switch
    lives in the top bar; sections (one axis down) live here for every surface."""
    st.markdown('<div class="sidebar-section-label">Sections</div>', unsafe_allow_html=True)
    if mode == AI_PAGE:
        current = get_ai_section()
        if st.button("Home", key=f"side_ai_home_{active_page}", use_container_width=True):
            st.switch_page(_page_path("home"))
        for key, label in _ai_sections():
            if st.button(
                label, key=f"side_ai_{key}_{active_page}", use_container_width=True,
                disabled=current == key,
            ):
                st.session_state["ai_section"] = key
                st.rerun()
        return
    if mode == BUSINESS_PAGE:
        sections = [("home", "Home"), *_business_sections()]
        for key, label in sections:
            if st.button(
                label, key=f"side_b_{key}_{active_page}", use_container_width=True,
                disabled=active_page == key,
            ):
                st.switch_page(_page_path(key))
        return
    # technical / data engineering
    sections = [("home", "Home"), *_technical_sections()]
    current = get_technical_section()
    for key, label in sections:
        if key in ("home", "wiki"):
            if st.button(label, key=f"side_t_{key}_{active_page}", use_container_width=True):
                st.switch_page(_page_path(key))
            continue
        if st.button(
            label, key=f"side_t_{key}_{active_page}", use_container_width=True,
            disabled=current == key,
        ):
            st.session_state["technical_section"] = key
            st.switch_page("pages/4_Data_Engineering.py")

def status_ribbon(text: str) -> None:
    st.markdown(f'<div class="status-ribbon">{text}</div>', unsafe_allow_html=True)


def page_footer() -> None:
    """Consistent site footer on every page: anchors short pages and carries the
    standing provenance/credit so no page ends in dead space."""
    st.markdown(
        '<div class="site-footer">'
        '<span class="site-footer-brand">FinLens</span>'
        '<span class="site-footer-note">Public FDIC &amp; FRED data · open-source stack'
        '</span>'
        '<a class="site-footer-link" href="https://surya.vaddhiparthy.com" '
        'target="_blank">Built by Surya Vaddhiparthy</a>'
        '</div>',
        unsafe_allow_html=True,
    )


def page_intro(eyebrow: str, title: str, copy: str, wiki_slug: str | None = None) -> None:
    link = (
        f'<a class="page-wiki-link" href="/Wiki?article={wiki_slug}" target="_self">'
        "Read the full article in the Wiki ›</a>"
        if wiki_slug else ""
    )
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="page-eyebrow">{eyebrow}</div>
            <div class="page-title">{title}</div>
            <div class="page-intro">{copy}</div>
            {link}
        </div>
        """,
        unsafe_allow_html=True,
    )


_SURFACES = [
    (BUSINESS_PAGE, "Business", "pages/0_Stress_Pulse.py"),
    (TECHNICAL_PAGE, "Data Engineering", "pages/4_Data_Engineering.py"),
    (AI_PAGE, "AI Engineering", "pages/7_AI_Engineering.py"),
]


def _navigate_section(mode: str, key: str) -> None:
    if key == "home":
        st.switch_page(_page_path("home"))
        return
    if mode == AI_PAGE:
        if key == "wiki":  # one encyclopedia, not a per-surface copy
            st.switch_page(_page_path("wiki"))
        else:
            st.session_state["ai_section"] = key
            st.rerun()
    elif mode == TECHNICAL_PAGE:
        if key == "wiki":
            st.switch_page(_page_path("wiki"))
        else:
            st.session_state["technical_section"] = key
            st.switch_page("pages/4_Data_Engineering.py")
    else:  # business, each section is its own page
        st.switch_page(_page_path(key))


def _render_section_tabs(active_page: str, mode: str) -> None:
    if mode == AI_PAGE:
        items = [("home", "Home"), *_ai_sections()]
        current = get_ai_section()

        def is_active(k: str) -> bool:
            return k == current
    elif mode == TECHNICAL_PAGE:
        items = [("home", "Home"), *_technical_sections()]
        current = get_technical_section()

        def is_active(k: str) -> bool:
            return k != "home" and k == current
    else:
        items = [("home", "Home"), *_business_sections()]

        def is_active(k: str) -> bool:
            return k == active_page

    st.markdown('<div class="sectiontabs-anchor"></div>', unsafe_allow_html=True)
    cols = st.columns(len(items))
    for col, (key, label) in zip(cols, items, strict=False):
        with col:
            if st.button(
                label,
                key=f"tab_{mode}_{key}_{active_page}",
                use_container_width=True,
                disabled=is_active(key),
            ):
                _navigate_section(mode, key)


def _render_top_bar(active_page: str, mode: str) -> None:
    """The single persistent chrome used on every page: surface dropdown (left),
    centred FinLens wordmark, credit (right). Identical placement everywhere."""
    is_home = mode == "home"
    trigger = "Explore surfaces" if is_home else _SURFACE_META.get(mode, _SURFACE_META[BUSINESS_PAGE])[0]

    st.markdown('<div class="topbar-anchor"></div>', unsafe_allow_html=True)
    bar_left, bar_center, bar_right = st.columns([1.25, 2.5, 1.25], vertical_alignment="center")
    with bar_left:
        st.markdown('<div class="surface-pop-anchor"></div>', unsafe_allow_html=True)
        with st.expander(trigger, expanded=False, icon=":material/grid_view:"):
            st.markdown('<div class="pop-title">Go to surface</div>', unsafe_allow_html=True)
            if not is_home and st.button(
                "Home", key=f"pop_home_{active_page}", use_container_width=True
            ):
                st.switch_page(_page_path("home"))
            for smode, slabel, spath in _SURFACES:
                if st.button(
                    slabel,
                    key=f"pop_{smode}_{active_page}",
                    use_container_width=True,
                    disabled=(mode == smode),
                ):
                    _set_surface_mode(smode)
                    st.switch_page(spath)
    with bar_center:
        st.markdown(
            '<div class="brandbar">'
            '<span class="brandbar-name">FinLens</span>'
            '<span class="brandbar-tag">Banking Stress Intelligence</span></div>',
            unsafe_allow_html=True,
        )
    with bar_right:
        st.markdown(
            '<a class="topbar-credit topbar-credit-solo" href="https://surya.vaddhiparthy.com" '
            'target="_blank">Built by Surya Vaddhiparthy</a>',
            unsafe_allow_html=True,
        )


def top_navigation(active_page: str, mode: str) -> None:
    _set_surface_mode(mode)
    _render_top_bar(active_page, mode)
    _render_section_tabs(active_page, mode)


def home_navigation() -> None:
    """Top bar for the landing page: same chrome, no section tabs."""
    _render_top_bar("home", "home")
