from functools import lru_cache

import streamlit as st

PALETTE = {
    "sidebar_bg": "#f5efe6",
    "page_bg": "#f4ede3",
    "content_bg": "#fffaf3",
    "border": "#e4d7c6",
    "text_main": "#1f2933",
    "text_muted": "#6a6b74",
    "text_soft": "#7f6b58",
    "link": "#0f5f70",
    "link_hover": "#0b4855",
    "accent": "#bf6d47",
    "accent_soft": "#f3dfcf",
    "teal": "#0f766e",
    "teal_soft": "#dbeceb",
    "rose": "#be123c",
    "sand": "#f4efe6",
    "shadow": "0 10px 30px rgba(15, 23, 42, 0.08)",
}

# Engineering theme, GitHub Dark Dimmed-derived, flat, hairline borders, one blue accent.
# sand == content_bg and accent == link so the existing gradients render flat.
DARK_PALETTE = {
    "sidebar_bg": "#1b2026",
    "page_bg": "#1c2128",
    "content_bg": "#22272e",
    "border": "#373e47",
    "text_main": "#cdd9e5",
    "text_muted": "#768390",
    "text_soft": "#768390",
    "link": "#539bf5",
    "link_hover": "#6cb6ff",
    "accent": "#539bf5",
    "accent_soft": "#1f2731",
    "teal": "#539bf5",
    "teal_soft": "#1f2731",
    "rose": "#e5534b",
    "sand": "#22272e",
    "shadow": "none",
}


def ensure_theme_state() -> None:
    st.session_state.setdefault("theme_dark", False)


def get_theme_mode() -> str:
    return "dark" if st.session_state.get("theme_dark", False) else "light"


def get_palette(mode: str | None = None) -> dict[str, str]:
    selected_mode = mode or get_theme_mode()
    return DARK_PALETTE if selected_mode == "dark" else PALETTE


def app_css(mode: str | None = None, sidebar_open: bool = False) -> str:
    # Resolve the theme first, then build from a cached builder. The CSS is ~63KB and was
    # rebuilt on every Streamlit rerun of every page; caching by (mode, sidebar_open) removes
    # that per-rerun cost (the main contributor to click-to-navigate lag).
    return _build_app_css(mode or get_theme_mode(), sidebar_open)


@lru_cache(maxsize=8)
def _build_app_css(mode: str, sidebar_open: bool = False) -> str:
    palette = get_palette(mode)
    # The left rail was retired: sections now live as top tabs and the surface
    # switch is a dropdown, so content is always full width and the sidebar hidden.
    sidebar_width = "14rem"
    content_offset = "0"
    sidebar_translate = "-14.5rem"
    sidebar_shadow = "none"
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    .stApp {{
        background:
            radial-gradient(circle at top left, transparent, transparent 30%),
            linear-gradient(180deg, {palette["page_bg"]} 0%, {palette["sidebar_bg"]} 100%);
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
    }}
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMarkdownContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stWidgetLabel"],
    [data-baseweb="tab-list"],
    [data-baseweb="tab-panel"] {{
        color: {palette["text_main"]} !important;
    }}
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp div,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6 {{
        color: inherit;
    }}
    input,
    textarea,
    [data-baseweb="input"],
    [data-baseweb="input"] input,
    [data-baseweb="textarea"],
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] > div,
    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [role="listbox"],
    [role="option"] {{
        background: {palette["content_bg"]} !important;
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    [data-baseweb="menu"] *,
    [role="listbox"] *,
    [role="option"] * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        background: transparent !important;
    }}
    [role="option"]:hover,
    [role="option"][aria-selected="true"] {{
        background: {palette["sand"]} !important;
    }}
    input::placeholder,
    textarea::placeholder {{
        color: {palette["text_muted"]} !important;
        -webkit-text-fill-color: {palette["text_muted"]} !important;
        opacity: 1 !important;
    }}
    [data-testid="stDialog"],
    [data-testid="stDialog"] *,
    div[role="dialog"],
    div[role="dialog"] * {{
        background-color: {palette["content_bg"]};
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    [data-testid="stTable"],
    [data-testid="stTable"] * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    button,
    button *,
    button[disabled],
    button[disabled] *,
    button[aria-disabled="true"],
    button[aria-disabled="true"] *,
    button:disabled,
    button:disabled *,
    [data-testid="baseButton-secondary"],
    [data-testid="baseButton-secondary"] *,
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondary"] *,
    div[data-testid="stButton"] > button,
    div[data-testid="stButton"] > button * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    div[data-testid="stTabs"] button,
    div[data-testid="stTabs"] button *,
    [data-baseweb="tab"],
    [data-baseweb="tab"] * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    div[data-testid="stTabs"] [aria-selected="true"] {{
        border-bottom: 2px solid {palette["accent"]} !important;
        box-shadow: inset 0 -2px 0 {palette["accent"]};
    }}
    div[data-testid="stPlotlyChart"] svg text {{
        fill: {palette["text_main"]} !important;
    }}
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stAppToolbar"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavSeparator"] {{
        display: none !important;
    }}
    [data-testid="stAppViewContainer"] {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}
    .block-container {{
        padding-top: .9rem;
        padding-bottom: 5.5rem;
        padding-left: 1.35rem;
        padding-right: 1.35rem;
        max-width: none !important;
        width: calc(100% - {content_offset});
        margin-left: {content_offset};
        margin-right: 0;
        transition: margin-left 240ms ease, width 240ms ease;
    }}
    [data-testid="stAppViewContainer"] > .main,
    section.main {{
        margin-left: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
    }}
    button[kind="header"],
    [data-testid="stSidebarCollapsedControl"],
    [title="Open sidebar"],
    [title="Close sidebar"],
    [aria-label="Close sidebar"],
    [aria-label="Open sidebar"],
    [data-testid="stBaseButton-headerNoPadding"],
    [data-testid="stBaseButton-header"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarHeader"] button,
    [data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarCollapseButton"],
    section[data-testid="stSidebar"] button[aria-label*="idebar"],
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"],
    section[data-testid="stSidebar"] > div > button {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] {{
        display: none !important;
        position: fixed !important;
        left: 0;
        top: 0;
        height: 100vh !important;
        width: {sidebar_width} !important;
        min-width: {sidebar_width} !important;
        max-width: {sidebar_width} !important;
        background:
            linear-gradient(180deg, {palette["content_bg"]}, {palette["sidebar_bg"]}) !important;
        border-right: 1px solid {palette["border"]};
        transform: translateX({sidebar_translate});
        transition: transform 240ms ease;
        box-shadow: {sidebar_shadow};
        z-index: 1200;
        overflow: hidden;
    }}
    section[data-testid="stSidebar"] > div {{
        background: transparent !important;
    }}
    [data-testid="stSidebarUserContent"] {{
        padding-top: 0;
    }}
    section[data-testid="stSidebar"] div[data-testid="stPageLink"] svg,
    section[data-testid="stSidebar"] div[data-testid="stPageLink"] img,
    section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] svg,
    section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] img {{
        display: none !important;
    }}
    .menu-anchor + div button {{
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 1400;
        width: 2.8rem;
        min-width: 2.8rem;
        height: 2.8rem;
        min-height: 2.8rem;
        border-radius: 999px !important;
        padding: 0 !important;
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]}) !important;
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12) !important;
    }}
    .edge-brand {{
        position: fixed;
        top: 1rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1390;
        display: flex;
        align-items: center;
        pointer-events: none;
        transition: left 240ms ease;
        padding: .42rem .88rem;
        border-radius: 999px;
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["content_bg"]});
        border: 1px solid {palette["border"]};
        box-shadow:
            0 10px 22px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    .edge-mark {{
        width: 1.95rem;
        height: 1.95rem;
        font-size: .75rem;
    }}
    .edge-brand-copy {{
        display: flex;
        flex-direction: column;
        line-height: .98;
        text-align: center;
    }}
    .edge-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .62rem;
        color: {palette["text_main"]};
        text-shadow: 0 1px 0 rgba(255,255,255,0.03);
    }}
    .edge-subtitle {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .9rem;
        font-weight: 700;
        margin-top: .06rem;
    }}
    .edge-credit {{
        position: fixed;
        top: 1rem;
        right: 1.35rem;
        z-index: 1390;
        pointer-events: none;
        text-decoration: none;
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .92rem;
        color: {palette["text_main"]};
        text-align: right;
        text-shadow: 0 1px 0 rgba(255,255,255,0.03);
        padding: .58rem .9rem;
        border-radius: 999px;
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["content_bg"]});
        border: 1px solid {palette["border"]};
        box-shadow:
            0 10px 22px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    a.edge-credit {{
        pointer-events: auto;
    }}
    .home-hero {{
        max-width: 980px;
        margin: 4.75rem auto 1.4rem auto;
        text-align: center;
        padding: 3.1rem 2rem 2.4rem;
        border-radius: 34px;
        background:
            radial-gradient(circle at 22% 0%, rgba(191,109,71,.18), transparent 32%),
            radial-gradient(circle at 80% 15%, rgba(15,118,110,.14), transparent 34%),
            linear-gradient(180deg, {palette["content_bg"]}, {palette["content_bg"]});
        border: 1px solid {palette["border"]};
        box-shadow: 0 26px 52px rgba(15, 23, 42, 0.10), inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    .home-center-brand {{
        position: fixed;
        top: 1rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1390;
        display: flex;
        align-items: center;
        padding: .42rem .88rem;
        border-radius: 999px;
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["content_bg"]});
        border: 1px solid {palette["border"]};
        box-shadow:
            0 10px 22px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.03);
        pointer-events: none;
    }}
    .home-center-copy {{
        display: flex;
        flex-direction: column;
        line-height: .98;
        text-align: center;
    }}
    .home-kicker {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .26em;
        font-size: .78rem;
        font-weight: 900;
        margin-bottom: .5rem;
    }}
    .home-title {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: clamp(3.2rem, 7vw, 6.8rem);
        line-height: .92;
        letter-spacing: -.045em;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}
    .home-credit-inline {{
        width: fit-content;
        max-width: 360px;
        margin: .85rem 2.2rem .35rem auto;
        text-align: left;
        padding: .45rem .6rem;
        border-left: 2px solid {palette["accent"]};
    }}
    .home-copy {{
        max-width: 780px;
        margin: 1.1rem auto 0;
        color: {palette["text_main"]};
        font-size: 1.08rem;
        line-height: 1.7;
        font-weight: 650;
    }}
    .home-subcopy {{
        max-width: 720px;
        margin: .72rem auto 0;
        color: {palette["text_muted"]};
        font-size: .95rem;
        line-height: 1.7;
    }}
    .home-action-divider {{
        text-align: center;
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .14em;
        font-size: .68rem;
        font-weight: 900;
    }}
    .home-credit-kicker {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .18em;
        font-size: .58rem;
        font-weight: 900;
        margin-bottom: .12rem;
    }}
    .home-credit-name {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .98rem;
        line-height: 1.2;
        text-decoration: none;
        display: inline-block;
    }}
    .home-credit-name:hover {{
        color: {palette["link_hover"]};
        text-decoration: underline;
    }}
    .home-credit-meta,
    .home-credit-link {{
        color: {palette["text_muted"]};
        font-size: .76rem;
        line-height: 1.35;
        text-decoration: none;
    }}
    .home-credit-link:hover {{
        color: {palette["link_hover"]};
        text-decoration: underline;
    }}
    .topbar-anchor + div div[data-testid="stVerticalBlockBorderWrapper"] {{
        position: sticky;
        top: 5.35rem;
        z-index: 999;
        background:
            linear-gradient(180deg, {palette["content_bg"]}, {palette["sidebar_bg"]});
        backdrop-filter: blur(14px);
        border: 1px solid {palette["border"]};
        outline: 1px solid rgba(255,255,255,0.03);
        border-radius: 24px;
        box-shadow:
            0 22px 34px rgba(15, 23, 42, 0.10),
            inset 0 1px 0 rgba(255,255,255,0.03),
            inset 0 -10px 24px rgba(191, 109, 71, 0.05);
        margin-top: 1.1rem;
        margin-bottom: .8rem;
        padding: 0 .16rem;
    }}
    .topbar-anchor + div div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        padding: 0 .42rem;
        min-height: 2.45rem;
        display: flex;
        align-items: center;
    }}
    .topbar-anchor + div div[data-testid="stVerticalBlock"] {{
        justify-content: center;
    }}
    .topbar-anchor + div div[data-testid="stHorizontalBlock"] {{
        align-items: center;
        min-height: 2.3rem;
    }}
    div[data-testid="stButton"] > button[kind="secondary"] {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
    }}
    [data-testid="stButtonGroup"] {{
        gap: .25rem;
    }}
    [data-testid="stButtonGroup"] button[kind="segmented_control"] {{
        background: {palette["content_bg"]} !important;
        border: 1px solid {palette["border"]} !important;
        color: {palette["text_muted"]} !important;
        min-height: 2.3rem;
        font-weight: 800;
    }}
    [data-testid="stButtonGroup"] button[kind="segmented_control"]:hover {{
        background: {palette["sand"]} !important;
        color: {palette["text_main"]} !important;
        border-color: {palette["border"]} !important;
    }}
    [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {{
        background: {palette["accent_soft"]} !important;
        border: 1px solid {palette["accent"]} !important;
        color: {palette["text_main"]} !important;
        box-shadow: inset 0 -2px 0 {palette["accent"]} !important;
        min-height: 2.3rem;
        font-weight: 800;
    }}
    [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    .topbar-crumb {{
        display: flex;
        align-items: baseline;
        gap: .5rem;
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        white-space: nowrap;
        overflow: hidden;
    }}
    .crumb-surface {{
        color: {palette["text_soft"]};
        font-size: .8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .1em;
    }}
    .crumb-sep {{
        color: {palette["text_soft"]};
        opacity: .6;
        font-size: .9rem;
    }}
    .crumb-section {{
        color: {palette["text_main"]};
        font-size: 1.02rem;
        font-weight: 700;
    }}
    /* Surface dropdown trigger (the small switch button) */
    .surface-pop-anchor + div [data-testid="stPopover"] > div > button,
    .surface-pop-anchor + div button {{
        border-radius: 999px !important;
        border: 1px solid {palette["border"]} !important;
        background: {palette["content_bg"]} !important;
        color: {palette["text_main"]} !important;
        min-height: 2.3rem !important;
        font-weight: 800 !important;
        font-size: .86rem !important;
        box-shadow: none !important;
        padding: .2rem .9rem !important;
    }}
    .surface-pop-anchor + div button:hover {{
        border-color: {palette["accent"]} !important;
        color: {palette["accent"]} !important;
    }}
    .pop-title {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .64rem;
        font-weight: 800;
        margin-bottom: .35rem;
    }}
    /* Dropdown panel: a distinct elevated card, not a flat cream square on cream */
    [data-testid="stPopover"] [data-baseweb="popover"] > div,
    [data-testid="stPopoverBody"] {{
        background: {palette["sidebar_bg"]} !important;
        border: 1px solid {palette["accent"]} !important;
        border-radius: 14px !important;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.22) !important;
        padding: .55rem !important;
    }}
    /* Dropdown option buttons: clear, separated list items */
    div[class*="st-key-pop_"] button {{
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        border-radius: 9px !important;
        border: 1px solid transparent !important;
        background: {palette["content_bg"]} !important;
        color: {palette["text_main"]} !important;
        font-weight: 700 !important;
        min-height: 2.2rem !important;
        box-shadow: none !important;
        margin-bottom: .25rem;
    }}
    div[class*="st-key-pop_"] button:hover {{
        border-color: {palette["accent"]} !important;
        background: {palette["accent_soft"]} !important;
        color: {palette["accent"]} !important;
    }}
    div[class*="st-key-pop_"] button:disabled {{
        background: {palette["accent_soft"]} !important;
        border-color: {palette["accent"]} !important;
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    .brandbar {{
        display: flex;
        flex-direction: column;
        align-items: center;
        line-height: 1.05;
        text-decoration: none;
    }}
    .brandbar-name {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.18rem;
        font-weight: 800;
        letter-spacing: -.01em;
        color: {palette["text_main"]};
    }}
    .brandbar-tag {{
        font-size: .68rem;
        font-weight: 600;
        letter-spacing: .14em;
        text-transform: uppercase;
        color: {palette["text_soft"]};
        margin-top: .12rem;
    }}
    .topbar-credit {{
        display: block;
        text-align: right;
        font-size: .72rem;
        font-weight: 600;
        color: {palette["text_soft"]} !important;
        text-decoration: none;
        margin-bottom: .2rem;
    }}
    .topbar-credit:hover {{
        color: {palette["accent"]} !important;
    }}
    .topbar-credit-solo {{ margin-bottom: 0; line-height: 2.4rem; }}
    /* ---- Landing page (full-bleed, scrollable) ---- */
    .landing-hero {{
        text-align: center;
        max-width: 50rem;
        margin: .6rem auto .9rem;
        padding: 0 1rem;
    }}
    .landing-eyebrow {{
        color: {palette["accent"]};
        text-transform: uppercase;
        letter-spacing: .18em;
        font-size: .7rem;
        font-weight: 800;
        margin-bottom: .55rem;
    }}
    .landing-h1 {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: clamp(2.1rem, 4.2vw, 3.2rem);
        line-height: 1.05;
        font-weight: 800;
        letter-spacing: -.03em;
        color: {palette["text_main"]};
        margin: 0 0 .7rem;
    }}
    .landing-sub {{
        max-width: 42rem;
        margin: 0 auto;
        color: {palette["text_muted"]};
        font-size: .98rem;
        line-height: 1.55;
    }}
    .landing-pick {{
        text-align: center;
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .16em;
        font-size: .72rem;
        font-weight: 800;
        margin: 1rem 0 .7rem;
    }}
    .surface-card {{
        border: 1px solid {palette["border"]};
        border-top: 3px solid {palette["accent"]};
        border-radius: 14px;
        background: {palette["content_bg"]};
        padding: 1.1rem 1.15rem .9rem;
        min-height: 9.5rem;
    }}
    .surface-card-k {{
        color: {palette["accent"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .68rem;
        font-weight: 800;
        margin-bottom: .35rem;
    }}
    .surface-card-t {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        color: {palette["text_main"]};
        font-size: 1.18rem;
        font-weight: 700;
        margin-bottom: .35rem;
    }}
    .surface-card-c {{
        color: {palette["text_muted"]};
        font-size: .86rem;
        line-height: 1.5;
    }}
    div[class*="st-key-home_open_"] button {{
        background: transparent !important;
        border: 1px solid {palette["accent"]} !important;
        color: {palette["accent"]} !important;
        -webkit-text-fill-color: {palette["accent"]} !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        min-height: 2.6rem !important;
        margin-top: .55rem;
        box-shadow: none !important;
    }}
    div[class*="st-key-home_open_"] button:hover {{
        background: {palette["accent"]} !important;
        border-color: {palette["accent"]} !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}
    div[class*="st-key-home_open_"] button:hover * {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}
    .site-footer {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: .6rem;
        margin: 3.5rem 0 .5rem;
        padding-top: 1rem;
        border-top: 1px solid {palette["border"]};
    }}
    .site-footer-brand {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-weight: 800;
        font-size: .92rem;
        color: {palette["text_main"]};
    }}
    .site-footer-note {{
        color: {palette["text_soft"]};
        font-size: .76rem;
    }}
    .site-footer-link {{
        color: {palette["text_soft"]} !important;
        font-size: .76rem;
        font-weight: 600;
        text-decoration: none;
    }}
    .site-footer-link:hover {{
        color: {palette["accent"]} !important;
    }}
    .landing-section-rule {{
        height: 1px;
        background: {palette["border"]};
        max-width: 64rem;
        margin: 2.6rem auto 1.6rem;
    }}
    .landing-h2 {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.4rem;
        font-weight: 800;
        color: {palette["text_main"]};
        margin: 1.4rem 0 .8rem;
    }}
    /* Section top-tabs (targeted via Streamlit's per-key container class) */
    div[class*="st-key-tab_"] {{
        border-bottom: 1px solid {palette["border"]};
    }}
    div[class*="st-key-tab_"] button {{
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        color: {palette["text_muted"]} !important;
        font-size: .82rem !important;
        font-weight: 700 !important;
        min-height: 2.5rem !important;
        white-space: nowrap;
        padding: .2rem .3rem !important;
        margin-bottom: -1px !important;
    }}
    div[class*="st-key-tab_"] button:hover {{
        background: transparent !important;
        color: {palette["text_main"]} !important;
        border-bottom-color: {palette["border"]} !important;
    }}
    div[class*="st-key-tab_"] button:disabled {{
        background: linear-gradient(180deg,
            color-mix(in srgb, {palette["accent"]} 10%, transparent),
            color-mix(in srgb, {palette["accent"]} 4%, transparent)) !important;
        color: {palette["accent"]} !important;
        -webkit-text-fill-color: {palette["accent"]} !important;
        border-bottom: 3px solid {palette["accent"]} !important;
        border-top-left-radius: 8px !important;
        border-top-right-radius: 8px !important;
        opacity: 1 !important;
        font-weight: 800 !important;
    }}
    div[class*="st-key-tab_"] button:disabled * {{
        color: {palette["accent"]} !important;
        -webkit-text-fill-color: {palette["accent"]} !important;
        opacity: 1 !important;
    }}
    .topbar-brand {{
        display: flex;
        align-items: center;
        gap: .8rem;
    }}
    .topbar-mark {{
        width: 2.25rem;
        height: 2.25rem;
        border-radius: 999px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, {palette["accent"]}, {palette["link"]});
        color: white;
        font-size: .85rem;
        font-weight: 800;
        letter-spacing: .04em;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
    }}
    .topbar-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.15rem;
        line-height: 1.1;
        color: {palette["text_main"]};
    }}
    .topbar-subtitle {{
        color: {palette["text_soft"]};
        font-size: .78rem;
        margin-top: .12rem;
    }}
    .topbar-author {{
        text-align: right;
    }}
    .topbar-author [data-testid="stToggle"] {{
        display:flex;
        justify-content:flex-end;
        margin-bottom:.2rem;
    }}
    .topbar-author [data-testid="stToggle"] > label {{
        gap:.35rem;
    }}
    .sidebar-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.1rem;
        color: {palette["text_main"]};
        margin-bottom: .2rem;
    }}
    .sidebar-brand-block {{
        border: 1px solid {palette["border"]};
        border-radius: 18px;
        padding: .9rem .92rem;
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
        margin-bottom: .9rem;
    }}
    .sidebar-brand-copy {{
        color: {palette["text_muted"]};
        font-size: .76rem;
        line-height: 1.45;
    }}
    .sidebar-time {{
        color: {palette["text_soft"]};
        font-size: .72rem;
        margin-top: .28rem;
        font-weight: 700;
    }}
    .sidebar-copy {{
        color: {palette["text_muted"]};
        font-size: .82rem;
        line-height: 1.55;
        margin-bottom: .85rem;
    }}
    .sidebar-group-label,
    .sidebar-section-label {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .66rem;
        font-weight: 800;
        margin: .85rem 0 .35rem 0;
    }}
    .sidebar-bottom-spacer {{
        height: 1.25rem;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] {{
        margin: 0 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {{
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        min-height: 0 !important;
        height: auto;
        border: none !important;
        border-left: 2px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        color: {palette["text_muted"]} !important;
        font-size: .84rem !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        padding: .26rem .15rem .26rem .7rem !important;
        margin: 0 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button p {{
        text-align: left;
        width: 100%;
        margin: 0 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
        background: transparent !important;
        border-left-color: {palette["border"]} !important;
        color: {palette["text_main"]} !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:disabled {{
        background: transparent !important;
        border-left: 2px solid {palette["accent"]} !important;
        color: {palette["accent"]} !important;
        -webkit-text-fill-color: {palette["accent"]} !important;
        opacity: 1 !important;
        font-weight: 700 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:disabled * {{
        color: {palette["accent"]} !important;
        -webkit-text-fill-color: {palette["accent"]} !important;
        opacity: 1 !important;
    }}
    .rail-brand {{
        display: flex;
        align-items: baseline;
        gap: .5rem;
        padding: .1rem 0 .55rem .15rem;
        margin-bottom: .55rem;
        border-bottom: 1px solid {palette["border"]};
    }}
    .rail-brand-name {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.12rem;
        font-weight: 800;
        color: {palette["text_main"]};
        letter-spacing: -.01em;
    }}
    .rail-brand-surface {{
        font-size: .64rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .1em;
        color: {palette["accent"]};
    }}
    .rail-foot {{
        margin-top: 1.1rem;
        padding-top: .6rem;
        border-top: 1px solid {palette["border"]};
    }}
    .sidebar-credit {{
        display: block;
        margin-top: .3rem;
        color: {palette["text_soft"]} !important;
        font-size: .68rem;
        font-weight: 600;
        text-decoration: none;
    }}
    .sidebar-credit:hover {{
        color: {palette["link_hover"]} !important;
        text-decoration: underline;
    }}
    .theme-toggle-anchor + div [data-testid="stToggle"] {{
        display: flex;
        justify-content: flex-end;
    }}
    .theme-toggle-anchor + div [data-testid="stToggle"] label p {{
        color: {palette["text_soft"]};
        font-size: .72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .08em;
    }}
    .topbar-action-label {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .11em;
        font-size: .58rem;
        font-weight: 700;
        margin-bottom: .18rem;
    }}
    .topbar-author-label {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .11em;
        font-size: .62rem;
        font-weight: 700;
    }}
    .topbar-author-name {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .92rem;
        line-height: 1.15;
        margin-top: .12rem;
    }}
    .topbar-actions {{
        display:flex;
        align-items:center;
        justify-content:flex-end;
        gap:.55rem;
        margin-bottom:.35rem;
    }}
    .stack-row {{
        display: flex;
        flex-wrap: wrap;
        gap: .5rem;
        margin-top: .55rem;
    }}
    .stack-chip {{
        border: 1px solid {palette["border"]};
        background: {palette["content_bg"]};
        border-radius: 999px;
        padding: .34rem .62rem;
        font-size: .76rem;
        color: {palette["text_main"]};
        font-weight: 700;
    }}
    .insight-card {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        border: 1px solid {palette["border"]};
        border-radius: 18px;
        padding: .82rem .9rem;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
        min-height: 8.25rem;
        display: flex;
        flex-direction: column;
    }}
    .insight-label {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .68rem;
        font-weight: 700;
        margin-bottom: .32rem;
    }}
    .insight-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        color: {palette["text_main"]};
        font-size: 1rem;
        margin-bottom: .2rem;
    }}
    .insight-copy {{
        color: {palette["text_muted"]};
        font-size: .82rem;
        line-height: 1.55;
    }}
    div[data-testid="stPageLink"] {{
        margin-bottom: 0;
    }}
    .topbar-anchor + div div[data-testid="stSegmentedControl"] {{
        background:
            linear-gradient(180deg, {palette["accent_soft"]}, {palette["content_bg"]});
        border: 1px solid {palette["accent"]};
        border-radius: 18px;
        padding: .22rem;
        box-shadow:
            0 10px 18px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    .surface-switch-card {{
        border: 1px solid {palette["border"]};
        border-radius: 10px;
        padding: .28rem .5rem;
        background: {palette["content_bg"]};
        margin-bottom: .22rem;
    }}
    .surface-switch-label {{
        color: {palette["text_soft"]};
        font-size: .56rem;
        font-weight: 900;
        letter-spacing: .12em;
        text-transform: uppercase;
        line-height: 1.1;
    }}
    .surface-switch-value {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .88rem;
        line-height: 1.15;
    }}
    .topbar-anchor + div div[data-testid="stSegmentedControl"] [role="radiogroup"] {{
        gap: .18rem;
    }}
    .topbar-anchor + div div[data-testid="stSegmentedControl"] label {{
        min-height: 2.2rem;
        border-radius: 14px;
        border: 1px solid transparent;
        color: {palette["text_main"]};
        font-weight: 900;
        background: transparent !important;
    }}
    .topbar-anchor + div
    div[data-testid="stSegmentedControl"]
    label[data-selected="true"] {{
        background: {palette["content_bg"]} !important;
        border-color: {palette["accent"]};
        box-shadow: 0 0 0 1px {palette["accent"]}, inset 0 -2px 0 {palette["accent"]};
    }}
    .topbar-anchor + div div[data-testid="stSegmentedControl"] label span {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    .topbar-anchor + div div[data-testid="stPageLink"] a {{
        background: {palette["content_bg"]};
        border: 1px solid transparent;
        border-radius: 10px;
        padding: .38rem .7rem;
        min-height: 2.2rem;
        box-shadow: none;
        width: 100%;
    }}
    .topbar-anchor + div div[data-testid="stPageLink"] a:hover {{
        border-color: {palette["border"]};
        background: {palette["sand"]};
    }}
    .topbar-anchor + div div[data-testid="stPageLink"] a p,
    .topbar-anchor + div div[data-testid="stPageLink"] a span {{
        color: {palette["text_main"]} !important;
        font-size: .8rem !important;
        white-space: nowrap;
    }}
    .topbar-anchor + div div[data-testid="stPageLink"] a[aria-disabled="true"] {{
        background: {palette["content_bg"]};
        border-color: {palette["accent"]};
        box-shadow: 0 0 0 1px {palette["accent"]};
    }}
    .topbar-anchor + div div[data-testid="stPageLink"] a[aria-disabled="true"] p,
    .topbar-anchor + div div[data-testid="stPageLink"] a[aria-disabled="true"] span {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    .topbar-anchor + div div[data-testid="stButton"] > button {{
        border-radius: 10px;
        min-height: 2.2rem;
        background: {palette["content_bg"]};
        box-shadow: none;
        border: 1px solid transparent;
        color: {palette["text_main"]};
        width: 100%;
        font-size: .8rem;
        font-weight: 650;
    }}
    .topbar-anchor + div div[data-testid="stButton"] > button:hover {{
        border-color: {palette["border"]};
        background: {palette["sand"]};
        color: {palette["text_main"]};
    }}
    .topbar-anchor + div div[data-testid="stButton"] > button:disabled {{
        background: {palette["content_bg"]};
        border-color: {palette["accent"]};
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        box-shadow: 0 0 0 1px {palette["accent"]};
        opacity: 1;
    }}
    .topbar-anchor + div div[data-testid="stButton"] > button:disabled * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    .surface-switch-anchor + div {{
        border: 1px solid {palette["accent"]};
        background: linear-gradient(180deg, {palette["accent_soft"]}, {palette["content_bg"]});
        border-radius: 16px;
        padding: .18rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    .surface-switch-anchor + div button {{
        min-height: 2.25rem !important;
        border-radius: 12px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        font-weight: 850 !important;
        letter-spacing: .01em;
    }}
    .surface-switch-anchor + div button:disabled {{
        background: {palette["content_bg"]} !important;
        border-color: {palette["accent"]} !important;
        box-shadow: 0 0 0 1px {palette["accent"]} !important;
    }}
    .section-menu-anchor + div {{
        border-left: 1px solid {palette["border"]};
        padding-left: .75rem;
    }}
    .section-menu-anchor + div button {{
        border-radius: 8px !important;
        min-height: 2rem !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        font-size: .77rem !important;
        font-weight: 750 !important;
    }}
    .section-menu-anchor + div button:hover {{
        background: {palette["sand"]} !important;
        border-color: {palette["border"]} !important;
    }}
    .section-menu-anchor + div button:disabled {{
        background: transparent !important;
        border-color: transparent !important;
        border-bottom: 2px solid {palette["accent"]} !important;
        border-radius: 8px 8px 4px 4px !important;
        box-shadow: none !important;
    }}
    .topbar-anchor + div button[disabled],
    .topbar-anchor + div button[aria-disabled="true"],
    .topbar-anchor + div [data-testid="baseButton-secondary"][disabled],
    .topbar-anchor + div [data-testid="stBaseButton-secondary"][disabled] {{
        background: {palette["content_bg"]} !important;
        background-color: {palette["content_bg"]} !important;
        border-color: {palette["accent"]} !important;
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        box-shadow: 0 0 0 1px {palette["accent"]} !important;
        opacity: 1 !important;
    }}
    .topbar-anchor + div button[disabled] *,
    .topbar-anchor + div button[aria-disabled="true"] * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    .section-menu-anchor + div button {{
        border-radius: 8px !important;
        min-height: 2rem !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        font-size: .77rem !important;
        font-weight: 750 !important;
    }}
    .section-menu-anchor + div button:disabled,
    .section-menu-anchor + div button[aria-disabled="true"] {{
        background: transparent !important;
        border-color: transparent !important;
        border-bottom: 2px solid {palette["accent"]} !important;
        border-radius: 8px 8px 4px 4px !important;
        box-shadow: none !important;
    }}
    div[data-testid="stPageLink"] a {{
        background: {palette["content_bg"]};
        border: 1px solid {palette["border"]};
        border-radius: 999px;
        padding: .42rem .72rem;
        min-height: 2.55rem;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
    }}
    div[data-testid="stPageLink"] a:hover {{
        border-color: {palette["accent"]};
        background: {palette["sand"]};
    }}
    div[data-testid="stPageLink"] a p,
    div[data-testid="stPageLink"] a span {{
        color: {palette["text_main"]} !important;
        font-size: .8rem !important;
        white-space: nowrap;
    }}
    div[data-testid="stPageLink"] a[aria-disabled="true"] {{
        background: linear-gradient(135deg, {palette["accent_soft"]}, {palette["teal_soft"]});
        border-color: {palette["accent"]};
    }}
    div[data-testid="stPageLink"] a[aria-disabled="true"] p,
    div[data-testid="stPageLink"] a[aria-disabled="true"] span {{
        color: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    .hero {{
        background: {palette["content_bg"]};
        border: 1px solid {palette["border"]};
        padding: 1.45rem 1.6rem;
        border-radius: 18px;
        color: {palette["text_main"]};
        box-shadow: {palette["shadow"]};
        margin-bottom: .85rem;
    }}
    .hero-kicker {{
        letter-spacing: .16em;
        text-transform: uppercase;
        font-size: .74rem;
        color: {palette["text_soft"]};
        margin-bottom: .55rem;
        font-weight: 700;
    }}
    .hero-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 2.55rem;
        line-height: 1.02;
        font-weight: 700;
        margin: 0 0 .55rem 0;
    }}
    .hero-copy {{
        max-width: 50rem;
        color: {palette["text_main"]};
        font-size: .94rem;
        margin: 0;
        line-height: 1.58;
    }}
    .pill-row {{
        display: flex;
        gap: .65rem;
        flex-wrap: wrap;
        margin-top: 1rem;
    }}
    .pill {{
        background: linear-gradient(
            135deg,
            {palette["accent_soft"]},
            {palette["teal_soft"]}
        );
        border: 1px solid {palette["border"]};
        padding: .42rem .68rem;
        border-radius: 999px;
        font-size: .8rem;
        color: {palette["text_main"]};
        font-weight: 700;
    }}
    .metric-card {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        border: 1px solid {palette["border"]};
        border-radius: 16px;
        padding: .68rem .8rem .74rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
        min-height: 5.75rem;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        margin-bottom: 0;
    }}
    .metric-label {{
        color: {palette["text_soft"]};
        font-size: .68rem;
        text-transform: uppercase;
        letter-spacing: .12em;
        font-weight: 700;
    }}
    .metric-value {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.04rem;
        font-weight: 700;
        line-height: 1.1;
        margin-top: .12rem;
    }}
    .metric-sub {{
        color: {palette["text_muted"]};
        font-size: .72rem;
        margin-top: .18rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 2rem;
    }}
    .section-label {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.15rem;
        font-weight: 600;
        margin: .85rem 0 .35rem 0;
    }}
    .subsection-copy {{
        color: {palette["text_muted"]};
        margin-top: -.15rem;
        margin-bottom: .65rem;
        font-size: .84rem;
        line-height: 1.55;
    }}
    .finlens-table-wrap {{
        overflow-x: auto;
        border: 1px solid {palette["border"]};
        border-radius: 18px;
        background: {palette["content_bg"]};
        box-shadow: {palette["shadow"]};
        padding: .25rem;
        margin-bottom: .85rem;
    }}
    .finlens-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        color: {palette["text_main"]};
        font-size: .82rem;
        line-height: 1.45;
    }}
    .finlens-table th {{
        text-align: left;
        color: {palette["text_soft"]};
        background: {palette["sand"]};
        text-transform: uppercase;
        letter-spacing: .08em;
        font-size: .66rem;
        font-weight: 800;
        padding: .72rem .78rem;
        border-bottom: 1px solid {palette["border"]};
        white-space: nowrap;
    }}
    .finlens-table td {{
        color: {palette["text_main"]};
        background: {palette["content_bg"]};
        padding: .72rem .78rem;
        border-bottom: 1px solid {palette["border"]};
        vertical-align: top;
        max-width: 26rem;
        word-break: break-word;
    }}
    .finlens-table tbody tr:nth-child(even) td {{
        background: {palette["content_bg"]};
    }}
    .finlens-table tr:last-child td {{
        border-bottom: 0;
    }}
    [data-testid="stExpander"] {{
        border: 1px solid {palette["border"]} !important;
        border-radius: 18px !important;
        background: {palette["content_bg"]} !important;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
        margin: .75rem 0;
    }}
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] details[open],
    [data-testid="stExpander"] details > div {{
        background: {palette["content_bg"]} !important;
    }}
    [data-testid="stExpander"] summary {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]}) !important;
        border-radius: 17px !important;
    }}
    [data-testid="stExpander"] details[open] summary {{
        border-bottom: 1px solid {palette["border"]} !important;
        border-bottom-left-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
    }}
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    .page-control-anchor + div {{
        max-width: 10rem;
        margin: .15rem auto .9rem auto;
        align-items: center;
    }}
    .page-control-anchor + div button {{
        min-height: 1.32rem !important;
        border-radius: 0 !important;
        padding: .02rem .12rem !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
        font-size: 1.05rem !important;
        font-weight: 850 !important;
    }}
    .page-number-display {{
        text-align: center;
        font-size: .78rem;
        font-weight: 800;
        color: {palette["text_soft"]};
        border: 1px solid {palette["border"]};
        border-radius: 6px;
        padding: .16rem .18rem;
        background: {palette["content_bg"]};
        white-space: nowrap;
    }}
    .browser-control-copy {{
        color: {palette["text_muted"]};
        font-size: .86rem;
        font-weight: 700;
        line-height: 1.45;
    }}
    .browser-control-copy + div {{
        margin-left: 0 !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        background: {palette["content_bg"]} !important;
        border: 1px solid {palette["border"]} !important;
        border-radius: 8px !important;
        color: {palette["text_main"]} !important;
        min-height: 2.15rem !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {{
        color: {palette["text_main"]} !important;
        fill: {palette["text_main"]} !important;
        opacity: 1 !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] input {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    .wiki-brand-card {{
        position: sticky;
        top: 4.4rem;
        z-index: 40;
        border: 1px solid rgba(106, 90, 72, .18);
        border-radius: 16px;
        background: {palette["content_bg"]};
        box-shadow: 0 10px 24px rgba(31,41,51,.05);
        padding: .54rem .7rem;
        width: fit-content;
        min-width: 15rem;
        margin-bottom: .55rem;
    }}
    .wiki-brand-kicker {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .72rem;
        font-weight: 700;
        color: {palette["text_soft"]};
        letter-spacing: .08em;
        text-transform: uppercase;
    }}
    .wiki-brand-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        color: {palette["text_main"]};
        font-size: 1.18rem;
        font-weight: 800;
        line-height: 1.05;
    }}
    .wiki-brand-copy {{
        color: {palette["text_muted"]};
        font-size: .72rem;
        font-weight: 650;
        line-height: 1.3;
        margin-top: .16rem;
    }}
    .wiki-nav-title {{
        color: {palette["text_soft"]};
        font-size: .7rem;
        font-weight: 900;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin: .15rem 0 .35rem;
    }}
    .wiki-nav-spaced {{
        margin-top: 1rem;
    }}
    .wiki-cluster {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .98rem;
        font-weight: 800;
        margin: .6rem 0 .18rem;
    }}
    .wiki-tree {{
        font-size: .84rem;
        line-height: 1.45;
    }}
    .wiki-tree-cluster {{
        color: {palette["text_main"]} !important;
        font-weight: 850;
        margin: .58rem 0 .18rem;
    }}
    .wiki-tree-branch {{
        color: {palette["text_soft"]};
        font-weight: 800;
        margin: .2rem 0 .08rem .35rem;
    }}
    .wiki-tree-link {{
        display: block;
        color: {palette["text_muted"]} !important;
        text-decoration: none !important;
        margin: .03rem 0 .03rem .9rem;
        padding: .02rem 0;
        background: transparent !important;
        border: 0 !important;
    }}
    .wiki-tree-link:hover {{
        color: {palette["text_main"]} !important;
        text-decoration: underline !important;
        text-decoration-color: {palette["accent"]} !important;
        text-underline-offset: 3px;
    }}
    .wiki-tree-link.active {{
        color: {palette["accent"]} !important;
        font-weight: 850;
    }}
    .wiki-head {{
        margin: .2rem 0 .9rem 0;
    }}
    .wiki-head-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.9rem;
        font-weight: 800;
        color: {palette["text_main"]};
        line-height: 1.05;
    }}
    .wiki-head-sub {{
        color: {palette["text_muted"]};
        font-size: .92rem;
        line-height: 1.55;
        margin-top: .3rem;
        max-width: 48rem;
    }}
    .wiki-toc {{
        position: sticky;
        top: 1rem;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        padding-right: .4rem;
    }}
    .wiki-toc-title {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .66rem;
        font-weight: 800;
        margin-bottom: .5rem;
    }}
    .wiki-toc-cluster {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: .82rem;
        font-weight: 800;
        margin: .7rem 0 .15rem;
    }}
    .wiki-toc-branch {{
        color: {palette["text_soft"]};
        font-size: .68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .06em;
        margin: .35rem 0 .12rem .1rem;
    }}
    .wiki-toc-link {{
        display: block;
        color: {palette["text_muted"]} !important;
        text-decoration: none !important;
        font-size: .82rem;
        line-height: 1.35;
        padding: .12rem 0 .12rem .6rem;
        border-left: 2px solid transparent;
    }}
    .wiki-toc-link:hover {{
        color: {palette["text_main"]} !important;
        border-left-color: {palette["border"]};
    }}
    .wiki-art-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.5rem;
        font-weight: 800;
        color: {palette["text_main"]};
        margin: .2rem 0 .1rem;
        scroll-margin-top: 1rem;
    }}
    .wiki-art-meta {{
        color: {palette["text_soft"]};
        font-size: .78rem;
        font-weight: 600;
        margin-bottom: .7rem;
    }}
    .wiki-art-divider {{
        height: 1px;
        background: {palette["border"]};
        margin: 1.6rem 0 1.4rem;
    }}
    /* ---- Encyclopedia: section tree + article + home ---- */
    .wiki-tree-nav {{
        position: sticky;
        top: 1rem;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        padding-right: .5rem;
        font-size: .82rem;
    }}
    .wiki-tree-home {{
        display: block;
        color: {palette["text_soft"]} !important;
        font-weight: 700;
        text-decoration: none !important;
        font-size: .76rem;
        margin-bottom: .6rem;
    }}
    .wiki-tree-home:hover {{ color: {palette["accent"]} !important; }}
    .wiki-tree-section {{
        color: {palette["text_main"]};
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-weight: 800;
        font-size: .9rem;
        margin: .85rem 0 .25rem;
    }}
    .wiki-tree-sub {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .06em;
        font-size: .64rem;
        font-weight: 700;
        margin: .4rem 0 .12rem .1rem;
    }}
    .wiki-tree-art {{
        display: block;
        color: {palette["text_muted"]} !important;
        text-decoration: none !important;
        line-height: 1.35;
        padding: .12rem 0 .12rem .65rem;
        border-left: 2px solid transparent;
    }}
    .wiki-tree-art:hover {{
        color: {palette["text_main"]} !important;
        border-left-color: {palette["border"]};
    }}
    .wiki-tree-art.active {{
        color: {palette["accent"]} !important;
        border-left-color: {palette["accent"]};
        font-weight: 700;
    }}
    .wiki-art-crumb {{
        color: {palette["text_soft"]};
        font-size: .76rem;
        font-weight: 600;
        margin-bottom: .35rem;
    }}
    .wiki-crumb-home, .wiki-crumb-home:visited {{
        color: {palette["text_soft"]} !important;
        text-decoration: none !important;
    }}
    .wiki-crumb-home:hover {{ color: {palette["accent"]} !important; }}
    .wiki-art-lead {{
        color: {palette["text_muted"]};
        font-size: 1.02rem;
        line-height: 1.6;
        font-weight: 600;
        margin: .1rem 0 1rem;
        padding-bottom: .8rem;
        border-bottom: 1px solid {palette["border"]};
    }}
    .wiki-art-nav {{
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid {palette["border"]};
    }}
    .wiki-prev, .wiki-next {{
        color: {palette["accent"]} !important;
        text-decoration: none !important;
        font-size: .86rem;
        font-weight: 600;
    }}
    .wiki-next {{ margin-left: auto; text-align: right; }}
    .wiki-home-head {{ margin-bottom: 1.4rem; }}
    .wiki-home-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 2rem;
        font-weight: 800;
        color: {palette["text_main"]};
    }}
    .wiki-home-sub {{
        color: {palette["text_muted"]};
        font-size: 1rem;
        line-height: 1.6;
        margin-top: .3rem;
        max-width: 46rem;
    }}
    .wiki-home-stats {{
        display: flex;
        flex-wrap: wrap;
        gap: 1.4rem;
        margin-top: .9rem;
        padding: .7rem 0;
        border-top: 1px solid {palette["border"]};
        border-bottom: 1px solid {palette["border"]};
        color: {palette["text_soft"]};
        font-size: .82rem;
    }}
    .wiki-home-stats b {{ color: {palette["text_main"]}; font-size: 1rem; }}
    .wiki-home-section {{
        display: block;
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.2rem;
        font-weight: 800;
        color: {palette["text_main"]} !important;
        text-decoration: none !important;
        margin: 1.5rem 0 .6rem;
    }}
    .wiki-home-section:hover {{ color: {palette["accent"]} !important; }}
    .wiki-browse-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
        gap: .6rem;
    }}
    .wiki-browse-card {{
        display: flex;
        flex-direction: column;
        gap: .2rem;
        border: 1px solid {palette["border"]};
        border-radius: 10px;
        padding: .65rem .75rem;
        text-decoration: none !important;
        background: {palette["content_bg"]};
    }}
    .wiki-browse-card:hover {{ border-color: {palette["accent"]}; }}
    .wiki-browse-t {{
        color: {palette["text_main"]};
        font-weight: 700;
        font-size: .86rem;
    }}
    .wiki-browse-s {{
        color: {palette["text_muted"]};
        font-size: .76rem;
        line-height: 1.4;
    }}
    .browser-stage-anchor + div button {{
        min-height: 4.2rem !important;
        border-radius: 18px !important;
        text-align: left !important;
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]}) !important;
        border: 1px solid {palette["border"]} !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05) !important;
        font-size: .78rem !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
    }}
    .browser-table-anchor + div button {{
        min-height: 2.05rem !important;
        border-radius: 999px !important;
        background: {palette["content_bg"]} !important;
        border: 1px solid {palette["border"]} !important;
        box-shadow: none !important;
        font-size: .72rem !important;
        font-weight: 800 !important;
    }}
    .chart-note {{
        border-left: 3px solid {palette["accent"]};
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["content_bg"]});
        border-radius: 12px;
        padding: .72rem .82rem;
        margin: .48rem 0 .9rem 0;
        box-shadow: 0 5px 14px rgba(15, 23, 42, 0.04);
    }}
    .chart-note-title {{
        color: {palette["text_main"]};
        font-weight: 800;
        font-size: .8rem;
        margin-bottom: .16rem;
    }}
    .chart-note-copy {{
        color: {palette["text_muted"]};
        font-size: .8rem;
        line-height: 1.45;
    }}
    .status-ribbon {{
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        background: linear-gradient(135deg, {palette["accent_soft"]}, {palette["teal_soft"]});
        border: 1px solid {palette["border"]};
        border-radius: 999px;
        color: {palette["text_main"]};
        font-size: .75rem;
        font-weight: 700;
        padding: .34rem .62rem;
        margin-bottom: .75rem;
    }}
    .page-hero {{
        margin-bottom: .75rem;
    }}
    .page-eyebrow {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .7rem;
        font-weight: 700;
        margin-bottom: .38rem;
    }}
    .page-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 2rem;
        line-height: 1.05;
        color: {palette["text_main"]};
        margin-bottom: .38rem;
    }}
    .ew-badge {{
        display: inline-block;
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.35rem;
        font-weight: 900;
        letter-spacing: .02em;
        padding: .3rem .9rem;
        border-radius: 12px;
        border: 1px solid transparent;
    }}
    .ew-sub {{
        color: {palette["text_muted"]};
        font-size: .9rem;
        line-height: 1.55;
        margin-top: .55rem;
        max-width: 30rem;
    }}
    .ew-actual {{
        margin-top: .7rem;
        color: {palette["text_soft"]};
        font-size: .9rem;
        font-weight: 600;
    }}
    .ew-pill {{
        display: inline-block;
        padding: .12rem .55rem;
        border-radius: 999px;
        font-weight: 800;
        font-size: .82rem;
        margin-left: .3rem;
    }}
    .ew-ok {{ background: rgba(87,171,90,.16); color: #3fa34d; border-color: rgba(87,171,90,.5); }}
    .ew-warn {{ background: rgba(198,144,38,.16); color: #b67d10; border-color: rgba(198,144,38,.5); }}
    .ew-danger {{ background: rgba(229,83,75,.16); color: #d64f45; border-color: rgba(229,83,75,.5); }}
    .ew-flow {{
        display: flex;
        align-items: stretch;
        gap: .5rem;
        margin: .2rem 0 1rem;
        flex-wrap: wrap;
    }}
    .ew-flow-step {{
        flex: 1 1 0;
        min-width: 11rem;
        border: 1px solid {palette["border"]};
        border-radius: 10px;
        padding: .55rem .7rem;
        background: {palette["content_bg"]};
        color: {palette["text_muted"]};
        font-size: .8rem;
        line-height: 1.4;
    }}
    .ew-flow-step b {{ color: {palette["text_main"]}; }}
    .ew-flow-arrow {{
        align-self: center;
        color: {palette["accent"]};
        font-size: 1.2rem;
        font-weight: 800;
    }}
    .page-wiki-link {{
        display: inline-block;
        margin-top: .4rem;
        color: {palette["accent"]} !important;
        font-size: .78rem;
        font-weight: 700;
        text-decoration: none !important;
        border: 1px solid {palette["border"]};
        border-radius: 999px;
        padding: .2rem .7rem;
        background: {palette["content_bg"]};
        transition: border-color .12s ease, background .12s ease;
    }}
    .page-wiki-link:hover {{
        text-decoration: none !important;
        border-color: {palette["accent"]};
        background: {palette["sand"]};
    }}
    .page-intro {{
        color: {palette["text_muted"]};
        margin-bottom: .7rem;
        line-height: 1.58;
        font-size: .9rem;
    }}
    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {{
        background: {palette["content_bg"]};
        border-radius: 18px;
        border: 1px solid {palette["border"]};
        box-shadow: {palette["shadow"]};
        padding: .45rem .55rem;
    }}
    div[data-testid="stInfo"] {{
        background: {palette["content_bg"]};
        border: 1px solid {palette["border"]};
        color: {palette["text_main"]};
    }}
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {{
        background: {palette["content_bg"]};
        border-color: {palette["border"]};
        border-radius: 12px;
    }}
    .empty-card {{
        border: 1px dashed {palette["border"]};
        border-radius: 16px;
        padding: 1rem 1.1rem;
        background: {palette["content_bg"]};
        color: {palette["text_muted"]};
    }}
    div[data-testid="stPopover"] button {{
        border-radius: 999px;
        border: 1px solid {palette["border"]};
        background: {palette["content_bg"]};
        color: {palette["text_main"]};
        min-height: 2.65rem;
        font-size: .88rem;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
    }}
    div[data-testid="stPopover"] button:hover {{
        border-color: {palette["accent"]};
        background: {palette["sand"]};
    }}
    div[data-testid="stButton"] > button {{
        border-radius: 16px;
        border: 1px solid {palette["border"]};
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        color: {palette["text_main"]};
        min-height: 2.75rem;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
    }}
    div[data-testid="stButton"] > button:hover {{
        border-color: {palette["accent"]};
        color: {palette["accent"]};
    }}
    .welcome-summary {{
        color: {palette["text_muted"]};
        line-height: 1.6;
        font-size: .92rem;
        margin-bottom: .9rem;
    }}
    .welcome-grid {{
        display:grid;
        grid-template-columns:repeat(2, minmax(0, 1fr));
        gap:.8rem;
        margin:.45rem 0 1rem 0;
    }}
    .welcome-card {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        border: 1px solid {palette["border"]};
        border-radius: 18px;
        padding: .82rem .95rem;
        min-height: 9.4rem;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    }}
    .welcome-kicker {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .66rem;
        font-weight: 800;
        margin-bottom: .38rem;
    }}
    .welcome-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1.18rem;
        color: {palette["text_main"]};
        margin-bottom: .3rem;
    }}
    .welcome-copy {{
        color: {palette["text_muted"]};
        font-size: .85rem;
        line-height: 1.55;
    }}
    .tech-bulletin {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        border: 1px solid {palette["border"]};
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: {palette["shadow"]};
        margin-bottom: .9rem;
    }}
    .tech-bulletin-title {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        color: {palette["text_main"]};
        font-size: 1.08rem;
        margin-bottom: .28rem;
    }}
    .tech-bulletin-copy {{
        color: {palette["text_muted"]};
        font-size: .86rem;
        line-height: 1.6;
    }}
    .flow-grid {{
        display: flex;
        gap: .75rem;
        align-items: stretch;
        margin-bottom: .8rem;
        overflow-x: auto;
        padding-bottom: .2rem;
    }}
    .flow-card {{
        background: linear-gradient(180deg, {palette["content_bg"]}, {palette["sand"]});
        border: 1px solid {palette["border"]};
        border-radius: 18px;
        padding: .92rem .95rem;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
        min-height: 11rem;
        min-width: 14.5rem;
    }}
    .flow-step {{
        color: {palette["text_soft"]};
        text-transform: uppercase;
        letter-spacing: .12em;
        font-size: .62rem;
        font-weight: 800;
        margin-bottom: .34rem;
    }}
    .flow-name {{
        font-family: "Inter", system-ui, -apple-system, sans-serif;
        font-size: 1rem;
        color: {palette["text_main"]};
        margin-bottom: .28rem;
    }}
    .flow-copy {{
        color: {palette["text_muted"]};
        font-size: .8rem;
        line-height: 1.55;
        margin-bottom: .55rem;
    }}
    .flow-metric {{
        color: {palette["text_main"]};
        font-size: .76rem;
        font-weight: 700;
        margin-bottom: .18rem;
    }}
    .flow-arrow {{
        display:flex;
        align-items:center;
        justify-content:center;
        color:{palette["text_soft"]};
        font-size:1.35rem;
        padding-top:1.8rem;
    }}
    .status-chip-ok, .status-chip-pending {{
        display:inline-flex;
        align-items:center;
        gap:.35rem;
        border-radius:999px;
        padding:.24rem .56rem;
        font-size:.74rem;
        font-weight:800;
    }}
    .status-chip-ok {{
        background:{palette["teal_soft"]};
        color:{palette["teal"]};
    }}
    .status-chip-pending {{
        background:{palette["accent_soft"]};
        color:{palette["accent"]};
    }}
    div[data-testid="stToggle"] label p {{
        color: {palette["text_main"]};
        font-size: .76rem;
    }}
    @media (max-width: 920px) {{
        .block-container {{
            padding-top: .9rem;
            padding-left: .95rem;
            padding-right: .95rem;
            width: 100%;
            margin-left: 0;
        }}
        .topbar-author {{
            text-align: left;
        }}
        .hero {{
            padding: 1.15rem 1rem;
            border-radius: 16px;
        }}
        .hero-title {{
            font-size: 2rem;
        }}
        .welcome-grid {{
            grid-template-columns:1fr;
        }}
        .edge-brand {{
            left: calc(.95rem + {content_offset});
            top: .92rem;
        }}
        .edge-title {{
            font-size: .88rem;
        }}
        .edge-subtitle {{
            font-size: .64rem;
        }}
        .edge-credit {{
            top: .92rem;
            right: 1rem;
            font-size: .78rem;
            max-width: 10rem;
        }}
        .flow-grid {{
            flex-direction: column;
        }}
        .flow-arrow {{
            transform: rotate(90deg);
            padding-top: 0;
        }}
        div[data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
        }}
        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {{
            padding: .45rem .5rem;
        }}
    }}

    /* ---- Wiki article typography: a readable measure + heading rhythm (no giant blocks) ---- */
    .st-key-wiki_article_body {{ max-width: 760px; }}
    .st-key-wiki_article_body [data-testid="stMarkdownContainer"] p {{
        text-align: left;
        line-height: 1.74;
        font-size: 1.02rem;
        margin: 0 0 1.05rem 0;
        color: {palette["text_main"]};
    }}
    .st-key-wiki_article_body h2 {{
        font-size: 1.32rem; font-weight: 750; letter-spacing: -.01em;
        color: {palette["text_main"]};
        margin: 1.9rem 0 .55rem 0; padding-bottom: .3rem;
        border-bottom: 1px solid {palette["border"]};
    }}
    .st-key-wiki_article_body h3 {{
        font-size: 1.08rem; font-weight: 700; color: {palette["text_main"]};
        margin: 1.35rem 0 .4rem 0;
    }}
    .st-key-wiki_article_body ul, .st-key-wiki_article_body ol {{
        margin: 0 0 1.05rem 1.1rem; line-height: 1.7;
    }}
    .st-key-wiki_article_body li {{ margin: .2rem 0; }}
    .st-key-wiki_article_body code {{
        background: {palette["sand"]}; border: 1px solid {palette["border"]};
        border-radius: 5px; padding: .04rem .3rem; font-size: .9em;
    }}
    .st-key-wiki_article_body a {{ color: {palette["link"]}; }}
    .wiki-art-title, .wiki-art-lead, .wiki-art-crumb {{ max-width: 760px; }}
    .wiki-art-lead {{ font-size: 1.12rem; line-height: 1.6; color: {palette["text_soft"]}; }}

    /* ---- Floating assistant widget (bottom-right, every page) ---- */
    .st-key-finlens_chat_closed {{
        position: fixed; right: 22px; bottom: 22px; z-index: 9990; width: auto !important;
    }}
    .st-key-finlens_chat_closed [data-testid="stButton"] > button {{
        border-radius: 999px !important;
        background: {palette["accent"]} !important;
        color: #fff !important; border: none !important;
        box-shadow: 0 10px 26px rgba(15,23,42,.22) !important;
        font-weight: 700 !important; padding: .58rem 1.2rem !important;
        transition: transform .12s ease, box-shadow .12s ease;
    }}
    .st-key-finlens_chat_closed [data-testid="stButton"] > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 14px 32px rgba(15,23,42,.28) !important;
    }}
    .st-key-finlens_chat_closed [data-testid="stButton"] > button p {{
        color: #fff !important; -webkit-text-fill-color: #fff !important; font-weight: 700;
    }}
    .st-key-finlens_chat_open {{
        position: fixed; right: 22px; bottom: 22px; z-index: 9990;
        width: 405px !important; max-width: 92vw;
        max-height: 82vh; overflow-y: auto; overflow-x: hidden;
        background: {palette["content_bg"]};
        border: 1px solid {palette["border"]};
        border-radius: 18px;
        box-shadow: 0 20px 52px rgba(15,23,42,.30);
        padding: .7rem .85rem .45rem;
    }}
    .finlens-chat-title {{
        font-weight: 800; font-size: 1.05rem; color: {palette["text_main"]};
        padding-top: .15rem;
    }}
    .st-key-finlens_chat_open [data-testid="stChatMessage"] {{
        padding: .25rem .15rem; background: transparent;
    }}
    </style>
    """
