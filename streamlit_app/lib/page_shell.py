from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

BUSINESS_PAGE = "business"
TECHNICAL_PAGE = "technical"
SIDEBAR_ENABLED = False
STRESS_LAB_ENABLED = False


def _set_surface_mode(mode: str) -> None:
    st.session_state["surface_mode"] = mode


def _page_path(page_key: str) -> str:
    page_map = {
        "home": "app.py",
        "overview": "pages/0_Stress_Pulse.py",
        "banks": "pages/1_Banks.py",
        "metrics": "pages/2_Metrics.py",
        "predictive": "pages/3_Predictive_Analytics.py",
        "business_docs": "pages/5_Business_Knowledge.py",
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
    if STRESS_LAB_ENABLED:
        pages.append(("stress", "pages/3_Stress_Lab.py", "Stress Lab", ":material/model_training:"))
    return pages


def _business_sections() -> list[tuple[str, str]]:
    sections = [
        ("overview", "Stress Pulse"),
        ("banks", "Failure Forensics"),
        ("metrics", "Macro Transmission"),
        ("predictive", "Predictive Analytics"),
        ("wiki", "Wiki"),
    ]
    if STRESS_LAB_ENABLED:
        sections.append(("stress", "Stress Lab"))
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


def get_technical_section() -> str:
    if "technical_section" not in st.session_state:
        st.session_state["technical_section"] = "pipeline"
    return st.session_state["technical_section"]


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


def render_sidebar(active_page: str, mode: str) -> None:
    if not SIDEBAR_ENABLED:
        return
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand-block">
                <div class="topbar-brand">
                    <div class="topbar-mark">FL</div>
                    <div>
                        <div class="sidebar-title">FinLens</div>
                        <div class="sidebar-brand-copy">Banking stress intelligence</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_sidebar_clock()

        st.markdown('<div class="sidebar-bottom-spacer"></div>', unsafe_allow_html=True)

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


def top_navigation(active_page: str, mode: str) -> None:
    _set_surface_mode(mode)
    render_sidebar(active_page, mode)

    st.markdown(
        """
        <div class="edge-brand">
            <span class="edge-brand-copy">
                <span class="edge-title">FinLens</span>
                <span class="edge-subtitle">Banking</span>
                <span class="edge-subtitle">Stress Intelligence</span>
            </span>
        </div>
        <div class="edge-credit">Built by Sri Surya S. Vaddhiparthy</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 1.35rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="topbar-anchor"></div>', unsafe_allow_html=True)
    current_surface_label = "Technical" if mode == TECHNICAL_PAGE else "Business"

    with st.container(border=True):
        top_left, top_right = st.columns([1.45, 3.55], vertical_alignment="center")
        with top_left:
            st.markdown(
                f"""
                <div class="surface-switch-card">
                    <div class="surface-switch-label">Current Surface</div>
                    <div class="surface-switch-value">{current_surface_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            switch_label = (
                "Switch to Business Surface"
                if mode == TECHNICAL_PAGE
                else "Switch to Technical Surface"
            )
            if st.button(
                switch_label,
                key=f"surface_switch_{active_page}",
                use_container_width=True,
            ):
                if mode == TECHNICAL_PAGE:
                    _set_surface_mode(BUSINESS_PAGE)
                    st.switch_page("pages/0_Stress_Pulse.py")
                else:
                    _set_surface_mode(TECHNICAL_PAGE)
                    st.switch_page("pages/4_Under_The_Hood.py")
        with top_right:
            st.markdown('<div class="section-menu-anchor"></div>', unsafe_allow_html=True)
            if mode == BUSINESS_PAGE:
                sections = [("home", "Home"), *_business_sections()]
                page_columns = st.columns(len(sections), vertical_alignment="center")
                for column, (key, label) in zip(page_columns, sections, strict=False):
                    with column:
                        if st.button(
                            label,
                            key=f"top_business_{key}_{active_page}",
                            disabled=active_page == key,
                            use_container_width=True,
                        ):
                            st.switch_page(_page_path(key))
            else:
                sections = [("home", "Home"), *_technical_sections()]
                section_columns = st.columns(len(sections), vertical_alignment="center")
                current_section = get_technical_section()
                for column, (key, label) in zip(section_columns, sections, strict=False):
                    with column:
                        if key == "home":
                            if st.button(
                                label,
                                key=f"top_section_{key}_{active_page}",
                                use_container_width=True,
                            ):
                                st.switch_page(_page_path(key))
                            continue
                        if key == "wiki":
                            if st.button(
                                label,
                                key=f"top_section_{key}_{active_page}",
                                use_container_width=True,
                            ):
                                st.switch_page(_page_path(key))
                            continue
                        if st.button(
                            label,
                            key=f"top_section_{key}_{active_page}",
                            disabled=current_section == key,
                            use_container_width=True,
                        ):
                            st.session_state["technical_section"] = key
                            st.switch_page("pages/4_Under_The_Hood.py")
