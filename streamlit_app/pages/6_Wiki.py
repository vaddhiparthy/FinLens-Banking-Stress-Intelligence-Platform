# ruff: noqa: E402,E501

import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit_app.lib import wiki_architecture as wa
from streamlit_app.lib import wiki_structure as ws
from streamlit_app.lib.page_shell import home_navigation, page_footer
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, styled_table

st.set_page_config(page_title="FinLens | Wiki", layout="wide", initial_sidebar_state="collapsed")
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
record_page_view("wiki", "shared")
home_navigation()


_LINK = re.compile(r"\[\[([^\]]+)\]\]")


def _wikilinks(body: str) -> str:
    """Convert [[Article Title]] cross-links into clickable article links."""
    def repl(m: re.Match) -> str:
        title = m.group(1).strip()
        if title in ws.ARTICLES:
            return f'<a target="_self" href="?article={ws.slug(title)}">{title}</a>'
        return title
    return _LINK.sub(repl, body)


def _matches(query: str) -> set[str] | None:
    if not query:
        return None
    q = query.lower()
    hits = set()
    for t, a in ws.ARTICLES.items():
        hay = " ".join([t, a.get("summary", ""), a.get("body", "")]).lower()
        if q in hay:
            hits.add(t)
    return hits


# ---- routing ----
# The landing dives straight into the introduction article (an encyclopedia opens on content,
# not a wall of tiles); the section tree on the left handles browsing.
slug = st.query_params.get("article", "")
current = ws.title_for_slug(slug) if slug else None
if current is None:
    _order = ws.all_titles_in_order()
    current = _order[0] if _order else None
query = st.text_input(
    "Search the wiki", key="wiki_search", placeholder="Search articles…",
    label_visibility="collapsed",
).strip()
hits = _matches(query)

left, main = st.columns([0.92, 3.08], gap="large")

# ---- left: section tree ----
with left:
    nav = ['<nav class="wiki-tree-nav">']
    nav.append('<a class="wiki-tree-home" target="_self" href="?article=">FinLens Wiki: home</a>')
    for _sid, stitle, groups in ws.SECTIONS:
        sec_titles = [t for _s, ts in groups for t in ts if t in ws.ARTICLES
                      and (hits is None or t in hits)]
        if not sec_titles:
            continue
        nav.append(f'<div class="wiki-tree-section">{stitle}</div>')
        for sub, titles in groups:
            shown = [t for t in titles if t in ws.ARTICLES and (hits is None or t in hits)]
            if not shown:
                continue
            if sub:
                nav.append(f'<div class="wiki-tree-sub">{sub}</div>')
            for t in shown:
                cls = "wiki-tree-art active" if t == current else "wiki-tree-art"
                nav.append(f'<a class="{cls}" target="_self" href="?article={ws.slug(t)}">{t}</a>')
    nav.append("</nav>")
    st.markdown("\n".join(nav), unsafe_allow_html=True)

# ---- main: article or home ----
with main:
    if current:
        a = ws.article(current)
        sec = ws.section_of(current)
        sec_title = sec[1] if sec else ""
        branch = a.get("branch") or ""
        crumb = sec_title
        if branch and branch != sec_title:
            crumb = f"{sec_title} / {branch}"
        home = '<a class="wiki-crumb-home" target="_self" href="?article=">Wiki</a>'
        st.markdown(
            f'<div class="wiki-art-crumb">{home} › {crumb}</div>'
            f'<div class="wiki-art-title">{current}</div>'
            f'<div class="wiki-art-lead">{a.get("summary", "")}</div>',
            unsafe_allow_html=True,
        )
        # an article may declare a native diagram (real Graphviz, rendered before the prose)
        if a.get("diagram") == "system_architecture":
            st.graphviz_chart(wa.ARCHITECTURE_DOT, use_container_width=True)
        with st.container(key="wiki_article_body"):
            st.markdown(_wikilinks(a["body"]), unsafe_allow_html=True)
        # contextual index tables retained from the legacy wiki
        if current == "How This Wiki Is Organized":
            rows = [{"Section": s, "Articles": len([t for _x, ts in g for t in ts if t in ws.ARTICLES])}
                    for _i, s, g in ws.SECTIONS]
            styled_table(__import__("pandas").DataFrame(rows))
        prev, nxt = ws.neighbours(current)
        nav_html = '<div class="wiki-art-nav">'
        if prev:
            nav_html += f'<a class="wiki-prev" target="_self" href="?article={ws.slug(prev)}">‹ {prev}</a>'
        if nxt:
            nav_html += f'<a class="wiki-next" target="_self" href="?article={ws.slug(nxt)}">{nxt} ›</a>'
        nav_html += "</div>"
        st.markdown(nav_html, unsafe_allow_html=True)
    else:
        s = ws.stats()
        st.markdown(
            '<div class="wiki-home-head">'
            '<div class="wiki-home-title">FinLens Wiki</div>'
            '<div class="wiki-home-sub">The reference for the platform: the banking domain, '
            'the architecture, the data engineering, and the model.</div>'
            f'<div class="wiki-home-stats">'
            f'<span><b>{s["articles"]}</b> articles</span>'
            f'<span><b>{s["sections"]}</b> sections</span>'
            f'<span><b>{s["words"]:,}</b> words</span>'
            f'<span><b>~{s["read_minutes"]}</b> min read</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        for _sid, stitle, groups in ws.SECTIONS:
            titles = [t for _s, ts in groups for t in ts if t in ws.ARTICLES]
            if not titles:
                continue
            first = titles[0]
            cards = "".join(
                f'<a class="wiki-browse-card" target="_self" href="?article={ws.slug(t)}">'
                f'<span class="wiki-browse-t">{t}</span>'
                f'<span class="wiki-browse-s">{ws.ARTICLES[t].get("summary", "")}</span></a>'
                for t in titles
            )
            st.markdown(
                f'<a class="wiki-home-section" target="_self" href="?article={ws.slug(first)}">{stitle}</a>'
                f'<div class="wiki-browse-grid">{cards}</div>',
                unsafe_allow_html=True,
            )

page_footer()
