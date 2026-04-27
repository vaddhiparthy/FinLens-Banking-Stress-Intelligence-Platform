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

DARK_PALETTE = {
    "sidebar_bg": "#151412",
    "page_bg": "#181614",
    "content_bg": "#221f1b",
    "border": "#3d342c",
    "text_main": "#f2eadf",
    "text_muted": "#c0b4a4",
    "text_soft": "#b89d84",
    "link": "#8dc7cf",
    "link_hover": "#a9d8df",
    "accent": "#d48b66",
    "accent_soft": "#413027",
    "teal": "#79b7af",
    "teal_soft": "#223432",
    "rose": "#dc6c8c",
    "sand": "#2f2923",
    "shadow": "0 16px 32px rgba(0, 0, 0, 0.34)",
}


def ensure_theme_state() -> None:
    st.session_state["theme_dark"] = False


def get_theme_mode() -> str:
    return "light"


def get_palette(mode: str | None = None) -> dict[str, str]:
    selected_mode = mode or get_theme_mode()
    return DARK_PALETTE if selected_mode == "dark" else PALETTE


def app_css(mode: str | None = None, sidebar_open: bool = False) -> str:
    palette = get_palette(mode)
    sidebar_width = "14rem"
    content_offset = "15rem" if sidebar_open else "0"
    sidebar_translate = "0" if sidebar_open else "-14.5rem"
    sidebar_shadow = palette["shadow"] if sidebar_open else "none"
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(243, 223, 207, 0.16), transparent 30%),
            linear-gradient(180deg, {palette["page_bg"]} 0%, {palette["sidebar_bg"]} 100%);
        color: {palette["text_main"]};
        font-family: "Manrope", system-ui, sans-serif;
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
        padding-bottom: 3rem;
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
    section[data-testid="stSidebar"] > div > button {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] {{
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
        left: calc(1.35rem + {content_offset});
        z-index: 1390;
        display: flex;
        align-items: center;
        gap: .65rem;
        pointer-events: none;
        transition: left 240ms ease;
        padding: .46rem .82rem;
        border-radius: 999px;
        background: linear-gradient(180deg, rgba(255,250,243,0.96), rgba(244,239,230,0.94));
        border: 1px solid {palette["border"]};
        box-shadow:
            0 10px 22px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.5);
    }}
    .edge-mark {{
        width: 1.95rem;
        height: 1.95rem;
        font-size: .75rem;
    }}
    .edge-brand-copy {{
        display: flex;
        flex-direction: column;
        line-height: 1.05;
    }}
    .edge-title {{
        font-family: "Fraunces", Georgia, serif;
        font-size: 1rem;
        color: {palette["text_main"]};
        text-shadow: 0 1px 0 rgba(255,255,255,0.24);
    }}
    .edge-subtitle {{
        color: {palette["text_soft"]};
        font-size: .72rem;
        font-weight: 500;
        margin-top: .12rem;
    }}
    .edge-credit {{
        position: fixed;
        top: 1rem;
        right: 1.35rem;
        z-index: 1390;
        pointer-events: none;
        font-family: "Fraunces", Georgia, serif;
        font-size: .92rem;
        color: {palette["text_main"]};
        text-align: right;
        text-shadow: 0 1px 0 rgba(255,255,255,0.24);
        padding: .58rem .9rem;
        border-radius: 999px;
        background: linear-gradient(180deg, rgba(255,250,243,0.96), rgba(244,239,230,0.94));
        border: 1px solid {palette["border"]};
        box-shadow:
            0 10px 22px rgba(15, 23, 42, 0.08),
            inset 0 1px 0 rgba(255,255,255,0.5);
    }}
    .topbar-anchor + div div[data-testid="stVerticalBlockBorderWrapper"] {{
        position: sticky;
        top: 5.35rem;
        z-index: 999;
        background:
            linear-gradient(180deg, {palette["content_bg"]}, {palette["sidebar_bg"]});
        backdrop-filter: blur(14px);
        border: 1px solid {palette["border"]};
        outline: 1px solid rgba(255, 255, 255, 0.32);
        border-radius: 24px;
        box-shadow:
            0 22px 34px rgba(15, 23, 42, 0.10),
            inset 0 1px 0 rgba(255, 255, 255, 0.26),
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
        font-family: "Fraunces", Georgia, serif;
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
        font-family: "Fraunces", Georgia, serif;
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
    .sidebar-group-label {{
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
        font-family: "Fraunces", Georgia, serif;
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
        font-family: "Fraunces", Georgia, serif;
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
            linear-gradient(180deg, {palette["content_bg"]}, rgba(243, 223, 207, 0.58));
        border: 1px solid {palette["border"]};
        border-radius: 14px;
        padding: .18rem;
        box-shadow:
            0 8px 16px rgba(15, 23, 42, 0.06),
            inset 0 1px 0 rgba(255,255,255,0.22);
    }}
    .topbar-anchor + div div[data-testid="stSegmentedControl"] [role="radiogroup"] {{
        gap: .18rem;
    }}
    .topbar-anchor + div div[data-testid="stSegmentedControl"] label {{
        min-height: 2.2rem;
        border-radius: 10px;
        border: 1px solid transparent;
        color: {palette["text_main"]};
        font-weight: 700;
        background: {palette["content_bg"]} !important;
    }}
    .topbar-anchor + div
    div[data-testid="stSegmentedControl"]
    label[data-selected="true"] {{
        background: {palette["content_bg"]};
        border-color: {palette["accent"]};
        box-shadow: inset 0 -2px 0 {palette["accent"]};
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
        font-family: "Fraunces", Georgia, serif;
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
        font-family: "Fraunces", Georgia, serif;
        font-size: 1.04rem;
        font-weight: 700;
        line-height: 1.1;
        margin-top: .12rem;
    }}
    .metric-sub {{
        color: {palette["text_muted"]};
        font-size: .72rem;
        margin-top: .18rem;
    }}
    .section-label {{
        color: {palette["text_main"]};
        font-family: "Fraunces", Georgia, serif;
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
        border-bottom: 1px solid rgba(228, 215, 198, 0.62);
        vertical-align: top;
        max-width: 26rem;
        word-break: break-word;
    }}
    .finlens-table tbody tr:nth-child(even) td {{
        background: rgba(244, 239, 230, 0.42);
    }}
    .finlens-table tr:last-child td {{
        border-bottom: 0;
    }}
    [data-testid="stExpander"] {{
        border: 1px solid {palette["border"]} !important;
        border-radius: 18px !important;
        background: rgba(255, 250, 243, 0.62) !important;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
        margin: .75rem 0;
    }}
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {{
        color: {palette["text_main"]} !important;
        -webkit-text-fill-color: {palette["text_main"]} !important;
    }}
    [data-testid="stSlider"] {{
        background: rgba(255, 250, 243, 0.7);
        border: 1px solid {palette["border"]};
        border-radius: 999px;
        padding: .18rem .75rem .1rem;
        margin: .25rem auto .95rem;
    }}
    [data-testid="stSlider"] label,
    [data-testid="stSlider"] label * {{
        color: {palette["text_soft"]} !important;
        -webkit-text-fill-color: {palette["text_soft"]} !important;
        font-size: .72rem !important;
        font-weight: 800 !important;
        letter-spacing: .08em;
        text-transform: uppercase;
    }}
    .chart-note {{
        border-left: 3px solid {palette["accent"]};
        background: linear-gradient(180deg, rgba(255,250,243,0.82), rgba(244,239,230,0.72));
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
        font-family: "Fraunces", Georgia, serif;
        font-size: 2rem;
        line-height: 1.05;
        color: {palette["text_main"]};
        margin-bottom: .38rem;
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
        background: linear-gradient(180deg, #fffdf9, #f8f2e8);
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
        font-family: "Fraunces", Georgia, serif;
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
        font-family: "Fraunces", Georgia, serif;
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
        font-family: "Fraunces", Georgia, serif;
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
    </style>
    """
