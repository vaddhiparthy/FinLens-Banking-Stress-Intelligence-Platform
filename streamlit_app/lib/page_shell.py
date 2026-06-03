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
        "banks": "pages/1_Banks.py",
        "metrics": "pages/2_Metrics.py",
        "predictive": "pages/3_Predictive_Analytics.py",
        "wiki": "pages/6_Wiki.py",
        "pipeline": "pages/4_Under_The_Hood.py",
        "status": "pages/4_Under_The_Hood.py",
        "classification": "pages/4_Under_The_Hood.py",
        "implementation": "pages/4_Under_The_Hood.py",
        "administration": "pages/4_Under_The_Hood.py",
        "decisions": "pages/4_Under_The_Hood.py",
    }
    return page_map[page_key]


def _business_pages() -> list[tuple[str, str, str, str]]:
    pages = [
        ("overview", "pages/0_Stress_Pulse.py", "Stress Pulse", ":material/space_dashboard:"),
        ("banks", "pages/1_Banks.py", "Failure Forensics", ":material/account_balance:"),
        ("metrics", "pages/2_Metrics.py", "Macro Transmission", ":material/show_chart:"),
        (
            "predictive",
            "pages/3_Predictive_Analytics.py",
            "Predictive Analytics",
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
        ("predictive", "Predictive Analytics"),
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
        ("contracts", "Feature Contracts"),
        ("stack", "AI Stack"),
        ("quality", "Model Quality"),
        ("decisions", "Model Decisions"),
        ("administration", "Administration"),
        ("wiki", "AI Wiki"),
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
            st.switch_page("pages/4_Under_The_Hood.py")

def status_ribbon(text: str) -> None:
    st.markdown(f'<div class="status-ribbon">{text}</div>', unsafe_allow_html=True)


def page_intro(eyebrow: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="page-eyebrow">{eyebrow}</div>
            <div class="page-title">{title}</div>
            <div class="page-intro">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_SURFACES = [
    (BUSINESS_PAGE, "Business", "pages/0_Stress_Pulse.py"),
    (TECHNICAL_PAGE, "Data Engineering", "pages/4_Under_The_Hood.py"),
    (AI_PAGE, "AI Engineering", "pages/7_AI_Engineering.py"),
]


def _navigate_section(mode: str, key: str) -> None:
    if key == "home":
        st.switch_page(_page_path("home"))
        return
    if mode == AI_PAGE:
        st.session_state["ai_section"] = key
        st.rerun()
    elif mode == TECHNICAL_PAGE:
        if key == "wiki":
            st.switch_page(_page_path("wiki"))
        else:
            st.session_state["technical_section"] = key
            st.switch_page("pages/4_Under_The_Hood.py")
    else:  # business — each section is its own page
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


def top_navigation(active_page: str, mode: str) -> None:
    _set_surface_mode(mode)
    current_label = _SURFACE_META.get(mode, _SURFACE_META[BUSINESS_PAGE])[0]

    st.markdown('<div class="topbar-anchor"></div>', unsafe_allow_html=True)
    bar_left, bar_right = st.columns([4.0, 1.0], vertical_alignment="center")
    with bar_left:
        st.markdown('<div class="surface-pop-anchor"></div>', unsafe_allow_html=True)
        with st.popover(current_label, icon=":material/swap_horiz:"):
            st.markdown('<div class="pop-title">Switch surface</div>', unsafe_allow_html=True)
            for smode, slabel, spath in _SURFACES:
                if st.button(
                    slabel,
                    key=f"pop_{smode}_{active_page}",
                    use_container_width=True,
                    disabled=(mode == smode),
                ):
                    _set_surface_mode(smode)
                    st.switch_page(spath)
    with bar_right:
        st.markdown('<div class="theme-toggle-anchor"></div>', unsafe_allow_html=True)
        dark = st.toggle(
            "Dark", value=st.session_state.get("theme_dark", False),
            key=f"theme_toggle_{active_page}",
        )
        if dark != st.session_state.get("theme_dark", False):
            st.session_state["theme_dark"] = dark
            st.rerun()

    _render_section_tabs(active_page, mode)
