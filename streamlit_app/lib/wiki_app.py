# ruff: noqa: E501
"""Client-side wiki: the whole encyclopedia rendered once into a single components iframe so
browsing is instant (no Streamlit rerun per article). Article bodies are converted to HTML with
mistune; ``[[Title]]`` cross-links and the section tree navigate in-app via JS. The System
Architecture article carries a live Graphviz diagram rendered in-place (viz.js + pan/zoom).

The layout is a FinLens-Wiki "Vector-2022" reading surface: a header bar (hamburger, wordmark,
search, owner name), a collapsible left sidebar, a Contents box that flips between a whole-site
browser and the current article's table of contents, smooth-scroll heading anchors, minimal
suggested-article text links, and an immersive-reader toggle. All interactivity is client-side
inside the sandboxed iframe (no Streamlit reruns).
"""

from __future__ import annotations

import html as _html
import json
import re

import mistune

from streamlit_app.lib import wiki_architecture as wa
from streamlit_app.lib import wiki_structure as ws

ARCH_SLUG = ws.slug("System Architecture")
_LINK = re.compile(r"\[\[([^\]]+)\]\]")
_md = mistune.create_markdown(escape=False, plugins=["table", "strikethrough"])


def _wikilinks(body: str) -> str:
    """Turn [[Article Title]] into an in-app anchor (data-slug) before markdown conversion."""
    def repl(m: re.Match) -> str:
        title = m.group(1).strip()
        if title in ws.ARTICLES:
            return f'<a class="wl" data-slug="{ws.slug(title)}">{_html.escape(title)}</a>'
        return _html.escape(title)
    return _LINK.sub(repl, body)


def _siblings(title: str) -> list[str]:
    """Other article titles inside the same section subsection (for 'suggested article' links)."""
    for _sid, _stitle, groups in ws.SECTIONS:
        for _sub, titles in groups:
            if title in titles:
                return [t for t in titles if t != title and t in ws.ARTICLES]
    return []


def _payload() -> dict:
    """Serialize every article to {slug: {title, summary, html, crumb, prev, next, search}}."""
    order = ws.all_titles_in_order()
    out: dict[str, dict] = {}
    for i, title in enumerate(order):
        a = ws.article(title) or {}
        sec = ws.section_of(title)
        sec_title = sec[1] if sec else ""
        branch = a.get("branch") or ""
        crumb = f"{sec_title} / {branch}" if branch and branch != sec_title else sec_title
        body_html = _md(_wikilinks(a.get("body", "")))
        prev_t = order[i - 1] if i > 0 else None
        next_t = order[i + 1] if i < len(order) - 1 else None
        # "suggested article" set: same-section siblings, then prev/next, deduped, max 6.
        sugg: list[str] = []
        for t in [*_siblings(title), prev_t, next_t]:
            if t and t not in sugg and t != title:
                sugg.append(t)
        out[ws.slug(title)] = {
            "title": title,
            "summary": a.get("summary", ""),
            "html": body_html,
            "crumb": crumb,
            "prev": ws.slug(prev_t) if prev_t else None,
            "prevT": prev_t,
            "next": ws.slug(next_t) if next_t else None,
            "nextT": next_t,
            "sugg": [{"slug": ws.slug(t), "title": t} for t in sugg[:6]],
            "search": " ".join([title, a.get("summary", ""), a.get("body", "")]).lower(),
        }
    # the System Architecture article carries the live Graphviz DOT; the SPA renders it client-side
    # (viz.js + svg-pan-zoom) so the diagram is interactive in-place — no cross-frame navigation.
    if ARCH_SLUG in out:
        out[ARCH_SLUG]["dot"] = wa.ARCHITECTURE_DOT
    return out


def _tree_html() -> str:
    """Section tree; each level-1 section is collapsed by default (#104) via a <details>; each
    leaf carries data-slug for instant in-app nav. This is the 'Browse wiki' index."""
    parts = ['<nav class="tree">']
    for _sid, stitle, groups in ws.SECTIONS:
        titles = [t for _s, ts in groups for t in ts if t in ws.ARTICLES]
        if not titles:
            continue
        parts.append('<details class="tree-sec-box">')
        parts.append(
            f'<summary class="tree-sec"><span class="tree-caret"></span>'
            f'<span class="tree-sec-t">{_html.escape(stitle)}</span>'
            f'<span class="tree-count">{len(titles)}</span></summary>'
        )
        for sub, ts in groups:
            shown = [t for t in ts if t in ws.ARTICLES]
            if not shown:
                continue
            if sub:
                parts.append(f'<div class="tree-sub">{_html.escape(sub)}</div>')
            for t in shown:
                parts.append(
                    f'<a class="tree-art" data-slug="{ws.slug(t)}" '
                    f'data-search="{_html.escape(t.lower())}">{_html.escape(t)}</a>'
                )
        parts.append("</details>")
    parts.append("</nav>")
    return "".join(parts)


def render_wiki_app(initial_slug: str | None) -> None:
    import streamlit.components.v1 as components

    from streamlit_app.lib.theme import get_palette, get_theme_mode

    p = get_palette(get_theme_mode())
    data = _payload()
    start = initial_slug if initial_slug in data else ws.slug(ws.all_titles_in_order()[0])
    s = ws.stats()
    payload_js = json.dumps(data)
    tree = _tree_html()

    doc = f"""
<!doctype html><html><head><meta charset="utf-8">
<style>
  :root {{
    --accent: {p['accent']}; --accent-deep: {p['accent_deep']}; --border: {p['border']};
    --content-bg: {p['content_bg']}; --page-bg: {p['page_bg']}; --side-bg: {p['sidebar_bg']};
    --text-main: {p['text_main']}; --text-soft: {p['text_soft']}; --text-muted: {p['text_muted']};
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; font-family: "Inter", system-ui, -apple-system, sans-serif;
    color: var(--text-main); background: var(--page-bg); }}
  a {{ color: var(--accent-deep); text-decoration: none; }}
  a:hover {{ color: var(--accent); text-decoration: underline; }}
  /* slim sleek accent scrollbars (no chunky default bars) */
  * {{ scrollbar-width: thin; scrollbar-color: rgba(191,109,71,.5) transparent; }}
  ::-webkit-scrollbar {{ width: 7px; height: 7px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: rgba(191,109,71,.45); border-radius: 8px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: rgba(191,109,71,.75); }}

  /* ---------- header bar ---------- */
  .hdr {{ display: flex; align-items: center; gap: .8rem; height: 3.1rem; padding: 0 .9rem;
    border-bottom: 1px solid var(--border); background: var(--content-bg); position: sticky; top: 0; z-index: 40; }}
  .iconbtn {{ display: inline-flex; align-items: center; justify-content: center; width: 2.1rem;
    height: 2.1rem; border: 1px solid transparent; border-radius: 9px; background: transparent;
    color: var(--text-soft); font-size: 1.15rem; cursor: pointer; line-height: 1; flex: none; }}
  .iconbtn:hover {{ background: var(--page-bg); border-color: var(--border); color: var(--accent-deep); }}
  .wordmark {{ font-weight: 800; font-size: 1.12rem; letter-spacing: -.01em; white-space: nowrap; }}
  .wordmark small {{ display: block; font-weight: 700; font-size: .54rem; letter-spacing: .14em;
    text-transform: uppercase; color: var(--accent); margin-top: -.05rem; }}
  .hsearch {{ flex: 1; max-width: 30rem; padding: .5rem .75rem; border: 1px solid var(--border);
    border-radius: 999px; background: var(--page-bg); color: var(--text-main); font-size: .85rem; }}
  .hsearch:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(191,109,71,.12); }}
  .owner {{ margin-left: auto; display: flex; align-items: center; gap: .7rem; }}
  .owner .name {{ font-size: .82rem; font-weight: 700; color: var(--text-soft); white-space: nowrap; }}
  .owner .name span {{ display: block; font-size: .58rem; font-weight: 600; color: var(--text-muted);
    letter-spacing: .04em; }}

  /* ---------- shell grid ---------- */
  .shell {{ display: grid; grid-template-columns: 16.5rem 1fr; gap: 0; height: 1437px; }}
  .shell.nosb {{ grid-template-columns: 0 1fr; }}
  .sb {{ border-right: 1px solid var(--border); background: var(--side-bg); overflow-y: auto;
    height: 100%; transition: opacity .15s ease; }}
  .shell.nosb .sb {{ opacity: 0; pointer-events: none; }}
  .sb-inner {{ padding: 1rem .85rem 2rem; }}
  .sb-stats {{ color: var(--text-soft); font-size: .66rem; margin: 0 0 .9rem; line-height: 1.5; }}

  /* ---------- contents box ---------- */
  .contents {{ border: 1px solid var(--border); border-radius: 12px; background: var(--content-bg);
    padding: .55rem .6rem .7rem; margin-bottom: 1rem; }}
  .contents-head {{ display: flex; align-items: center; gap: .4rem; margin-bottom: .5rem; }}
  .contents-title {{ font-size: .68rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--accent); }}
  .ctl-spacer {{ flex: 1; }}
  .flip {{ display: inline-flex; align-items: center; border: 1px solid var(--border); border-radius: 999px;
    overflow: hidden; background: var(--page-bg); }}
  .flip button {{ border: none; background: transparent; color: var(--text-soft); font-size: .62rem;
    font-weight: 700; padding: .22rem .5rem; cursor: pointer; line-height: 1.3; }}
  .flip button.on {{ background: var(--accent); color: #fff; }}
  .sidetoggle {{ border: 1px solid var(--border); background: var(--page-bg); color: var(--text-soft);
    border-radius: 8px; font-size: .62rem; font-weight: 700; padding: .25rem .5rem; cursor: pointer; }}
  .sidetoggle:hover {{ color: var(--accent-deep); border-color: var(--accent); }}

  /* whole-site tree (Browse wiki) */
  .tree {{ display: block; }}
  .tree.hide, .toc.hide {{ display: none; }}
  .tree-sec-box {{ border-top: 1px solid var(--border); }}
  .tree-sec-box:first-child {{ border-top: none; }}
  summary.tree-sec {{ display: flex; align-items: center; gap: .35rem; cursor: pointer;
    font-size: .64rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--accent); padding: .5rem .15rem; list-style: none; }}
  summary.tree-sec::-webkit-details-marker {{ display: none; }}
  .tree-sec-t {{ flex: 1; }}
  .tree-caret {{ width: .55rem; height: .55rem; border-right: 2px solid var(--accent);
    border-bottom: 2px solid var(--accent); transform: rotate(-45deg); transition: transform .15s ease;
    flex: none; margin-right: .1rem; }}
  details[open] > summary.tree-sec .tree-caret {{ transform: rotate(45deg); }}
  .tree-count {{ font-size: .6rem; font-weight: 700; color: var(--text-muted);
    background: var(--page-bg); border: 1px solid var(--border); border-radius: 999px; padding: 0 .4rem; }}
  .tree-sub {{ font-size: .6rem; font-weight: 700; color: var(--text-soft); margin: .45rem 0 .2rem .3rem;
    text-transform: uppercase; letter-spacing: .04em; }}
  .tree-art {{ display: block; padding: .25rem .5rem; border-left: 2px solid transparent;
    color: var(--text-muted); font-size: .8rem; cursor: pointer; border-radius: 0 6px 6px 0; }}
  .tree-art:hover {{ background: var(--page-bg); color: var(--text-main); text-decoration: none; }}
  .tree-art.active {{ border-left-color: var(--accent); color: var(--accent-deep);
    font-weight: 700; background: var(--page-bg); }}
  .tree-art.hidden {{ display: none; }}
  .noresult {{ color: var(--text-soft); font-size: .76rem; padding: .4rem .2rem; }}

  /* in-page table of contents (Browse article) */
  .toc {{ display: block; }}
  .toc a {{ display: block; color: var(--text-muted); font-size: .8rem; padding: .22rem .4rem;
    border-left: 2px solid transparent; border-radius: 0 6px 6px 0; cursor: pointer; }}
  .toc a:hover {{ background: var(--page-bg); color: var(--text-main); text-decoration: none; }}
  .toc a.lvl3 {{ padding-left: 1.25rem; font-size: .76rem; }}
  .toc a.active {{ border-left-color: var(--accent); color: var(--accent-deep); font-weight: 700;
    background: var(--page-bg); }}
  .toc-empty {{ color: var(--text-soft); font-size: .76rem; padding: .3rem .4rem; }}

  /* ---------- reading column ---------- */
  .read {{ overflow-y: auto; height: 100%; position: relative; }}
  .read-inner {{ max-width: 60rem; margin: 0 auto; padding: 1.6rem 2.4rem 3rem; position: relative; }}
  .float-tools {{ position: absolute; top: 1rem; right: 1.1rem; display: flex; gap: .4rem; z-index: 20; }}
  .crumb {{ font-size: .72rem; color: var(--text-soft); font-weight: 600; }}
  .title {{ font-size: 2.05rem; font-weight: 800; margin: .2rem 0 .3rem; letter-spacing: -.015em;
    line-height: 1.12; }}
  .lead {{ color: var(--text-muted); font-size: 1.02rem; line-height: 1.6; margin-bottom: 1.2rem;
    padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
  .body {{ font-size: .96rem; line-height: 1.75; color: var(--text-main); text-align: justify;
    -webkit-hyphens: auto; hyphens: auto; }}
  .body h2 {{ font-size: 1.4rem; font-weight: 800; margin: 1.9rem 0 .55rem; padding-bottom: .25rem;
    border-bottom: 1px solid var(--border); scroll-margin-top: 4rem; }}
  .body h3 {{ font-size: 1.12rem; font-weight: 700; margin: 1.3rem 0 .4rem; scroll-margin-top: 4rem; }}
  .body p {{ margin: .65rem 0; }}
  .body table {{ border-collapse: collapse; margin: .9rem 0; font-size: .85rem; width: 100%; }}
  .body th, .body td {{ border: 1px solid var(--border); padding: .45rem .65rem; text-align: left; }}
  .body th {{ background: var(--content-bg); }}
  .body code {{ background: var(--content-bg); padding: .1rem .3rem; border-radius: 5px;
    font-family: "JetBrains Mono", monospace; font-size: .85em; }}
  .body pre {{ background: var(--content-bg); border: 1px solid var(--border); border-radius: 10px;
    padding: .85rem 1.05rem; overflow-x: auto; }}
  .body pre code {{ background: transparent; padding: 0; }}
  .anchor {{ opacity: 0; font-weight: 400; color: var(--text-muted); margin-left: .4rem;
    font-size: .8em; cursor: pointer; }}
  .body h2:hover .anchor, .body h3:hover .anchor {{ opacity: .7; }}

  /* suggested articles: clean minimal TEXT links (no tiles) */
  .seealso {{ margin: 2.2rem 0 .6rem; padding-top: 1.1rem; border-top: 1px solid var(--border); }}
  .seealso-h {{ font-size: .68rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
    color: var(--accent); margin-bottom: .55rem; }}
  .seealso ul {{ margin: 0; padding: 0; list-style: none; columns: 2; column-gap: 2rem; }}
  .seealso li {{ margin: .2rem 0; break-inside: avoid; }}
  .seealso a {{ font-size: .86rem; cursor: pointer; }}
  .seealso a::before {{ content: "› "; color: var(--text-muted); }}

  .pager {{ display: flex; justify-content: space-between; gap: 1rem; margin: 1.8rem 0 .5rem;
    padding-top: 1rem; border-top: 1px solid var(--border); }}
  .pager a {{ font-weight: 700; font-size: .85rem; cursor: pointer; }}

  /* architecture diagram */
  .diagram {{ height: 360px; border: 1px solid var(--border); border-radius: 12px;
    background: var(--content-bg); overflow: hidden; margin: .4rem 0 1.4rem; }}
  .diagram svg {{ width: 100% !important; height: 100% !important; }}
  .diagram-msg {{ padding: 1rem; color: var(--text-soft); font-size: .85rem; }}
  .svg-pan-zoom-control-background {{ fill: var(--content-bg); opacity: .9; }}
  .svg-pan-zoom-control-element {{ fill: var(--accent); }}

  /* ---------- immersive reader ---------- */
  .shell.immersive {{ grid-template-columns: 0 1fr; }}
  .shell.immersive .sb {{ opacity: 0; pointer-events: none; }}
  .immersive .read-inner {{ max-width: 46rem; padding-top: 2.6rem; }}
  .immersive .hdr {{ display: none; }}
  body.immersive .hdr {{ display: none; }}

  @media (max-width: 760px) {{
    .shell, .shell.nosb {{ grid-template-columns: 1fr; height: auto; }}
    .sb {{ border-right: none; border-bottom: 1px solid var(--border); height: auto; }}
    .read {{ height: auto; overflow: visible; }}
    .read-inner {{ padding: 1.1rem 1.1rem 2rem; }}
    .seealso ul {{ columns: 1; }}
    .title {{ font-size: 1.6rem; }}
    .body {{ text-align: left; }}
  }}
</style>
<script src="https://cdn.jsdelivr.net/npm/@viz-js/viz@3.2.4/lib/viz-standalone.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
</head><body>
<header class="hdr" id="hdr">
  <button class="iconbtn" id="burger" title="Toggle sidebar" aria-label="Toggle sidebar">&#9776;</button>
  <div class="wordmark">FinLens-Wiki<small>Banking Stress Intelligence</small></div>
  <input id="q" class="hsearch" placeholder="Search all articles…" autocomplete="off">
</header>
<div class="shell" id="shell">
  <aside class="sb" id="sb">
    <div class="sb-inner">
      <div class="sb-stats">{s['articles']} articles · {s['sections']} sections · ~{s['read_minutes']} min read</div>
      <div class="contents">
        <div class="contents-head">
          <span class="contents-title">Contents</span>
          <span class="ctl-spacer"></span>
          <span class="flip" id="flip">
            <button data-mode="wiki" class="on">Browse wiki</button>
            <button data-mode="article">Browse article</button>
          </span>
        </div>
        <div style="margin-bottom:.5rem;">
          <button class="sidetoggle" id="sidetoggle">Hide</button>
        </div>
        <div id="noresult" class="noresult" style="display:none">No articles match.</div>
        {tree}
        <div class="toc hide" id="toc"></div>
      </div>
    </div>
  </aside>
  <main class="read" id="read">
    <div class="read-inner" id="readinner">
      <div class="float-tools">
        <button class="iconbtn" id="immersive" title="Immersive reader" aria-label="Immersive reader">&#9776;</button>
      </div>
      <div id="content"></div>
    </div>
  </main>
</div>
<script>
  const DATA = {payload_js};
  const shell = document.getElementById('shell');
  const sb = document.getElementById('sb');
  const content = document.getElementById('content');
  const read = document.getElementById('read');
  const tree = document.querySelector('.tree');
  const toc = document.getElementById('toc');
  const flip = document.getElementById('flip');
  const sideToggle = document.getElementById('sidetoggle');
  const burger = document.getElementById('burger');
  const immersiveBtn = document.getElementById('immersive');
  const q = document.getElementById('q');
  const nores = document.getElementById('noresult');
  let curSlug = null;
  let contentsMode = 'wiki';

  function setActive(slug) {{
    document.querySelectorAll('.tree-art').forEach(function(el) {{
      el.classList.toggle('active', el.getAttribute('data-slug') === slug);
    }});
  }}

  // open the section that holds the active article so the tree reflects where you are
  function revealInTree(slug) {{
    const el = document.querySelector('.tree-art[data-slug="' + slug + '"]');
    if (!el) return;
    const box = el.closest('.tree-sec-box');
    if (box && !box.open) box.open = true;
    el.scrollIntoView({{ block: 'nearest' }});
  }}

  function slugifyHeading(txt, i) {{
    return 'h-' + i + '-' + txt.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
  }}

  // build the current article's table of contents from its h2/h3 (Browse article mode)
  function buildToc() {{
    toc.innerHTML = '';
    const heads = content.querySelectorAll('.body h2, .body h3');
    if (!heads.length) {{ toc.innerHTML = '<div class="toc-empty">This article has no sections.</div>'; return; }}
    heads.forEach(function(h, i) {{
      const txt = h.dataset.htext || h.textContent;
      const id = h.id || slugifyHeading(txt, i);
      h.id = id;
      const a = document.createElement('a');
      a.textContent = txt;
      a.className = (h.tagName === 'H3') ? 'lvl3' : 'lvl2';
      a.setAttribute('data-anchor', id);
      toc.appendChild(a);
    }});
  }}

  function setContentsMode(mode) {{
    contentsMode = mode;
    flip.querySelectorAll('button').forEach(function(b) {{
      b.classList.toggle('on', b.getAttribute('data-mode') === mode);
    }});
    tree.classList.toggle('hide', mode !== 'wiki');
    toc.classList.toggle('hide', mode !== 'article');
    if (mode === 'article') buildToc();
  }}

  function renderDiagram(host, dot) {{
    if (typeof Viz === 'undefined') {{
      host.innerHTML = '<div class="diagram-msg">Interactive diagram unavailable (offline).</div>';
      return;
    }}
    Viz.instance().then(function(viz) {{
      const svg = viz.renderSVGElement(dot);
      host.appendChild(svg);
      if (typeof svgPanZoom !== 'undefined') {{
        svgPanZoom(svg, {{ zoomEnabled: true, controlIconsEnabled: true, fit: true,
          center: true, minZoom: 0.3, maxZoom: 12, zoomScaleSensitivity: 0.4 }});
      }}
    }}).catch(function() {{
      host.innerHTML = '<div class="diagram-msg">Diagram failed to render.</div>';
    }});
  }}

  function render(slug) {{
    const a = DATA[slug];
    if (!a) return;
    curSlug = slug;
    let h = '<div class="crumb">' + (a.crumb || 'Wiki') + '</div>';
    h += '<div class="title">' + a.title + '</div>';
    if (a.summary) h += '<div class="lead">' + a.summary + '</div>';
    if (a.dot) h += '<div class="diagram" id="wiki-diagram"></div>';
    h += '<div class="body">' + a.html + '</div>';
    if (a.sugg && a.sugg.length) {{
      h += '<div class="seealso"><div class="seealso-h">Suggested articles</div><ul>';
      a.sugg.forEach(function(x) {{
        h += '<li><a data-slug="' + x.slug + '">' + x.title + '</a></li>';
      }});
      h += '</ul></div>';
    }}
    h += '<div class="pager">';
    h += a.prev ? '<a data-slug="' + a.prev + '">‹ ' + a.prevT + '</a>' : '<span></span>';
    h += a.next ? '<a data-slug="' + a.next + '">' + a.nextT + ' ›</a>' : '<span></span>';
    h += '</div>';
    content.innerHTML = h;
    // give every heading a stable id + clean text, then a hover anchor for in-page deep links
    content.querySelectorAll('.body h2, .body h3').forEach(function(hd, i) {{
      hd.dataset.htext = hd.textContent;
      hd.id = slugifyHeading(hd.textContent, i);
      const sp = document.createElement('span');
      sp.className = 'anchor'; sp.textContent = '#';
      hd.appendChild(sp);
    }});
    read.scrollTop = 0;
    if (a.dot) renderDiagram(document.getElementById('wiki-diagram'), a.dot);
    setActive(slug);
    revealInTree(slug);
    if (contentsMode === 'article') buildToc();
  }}

  // smooth-scroll to a heading inside the reading column
  function jumpTo(id) {{
    const el = document.getElementById(id);
    if (!el) return;
    // scroll within whichever ancestor actually scrolls (the reading column on long articles)
    const top = read.scrollTop + el.getBoundingClientRect().top - read.getBoundingClientRect().top - 14;
    if (read.scrollHeight > read.clientHeight + 4) {{
      read.scrollTo({{ top: top, behavior: 'smooth' }});
    }} else {{
      el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}
  }}

  // delegated clicks: tree leaves, wikilinks, pager, suggested, toc anchors, heading anchors
  document.addEventListener('click', function(e) {{
    const anchorLink = e.target.closest('[data-anchor]');
    if (anchorLink) {{ e.preventDefault(); jumpTo(anchorLink.getAttribute('data-anchor')); return; }}
    const headAnchor = e.target.closest('.anchor');
    if (headAnchor && headAnchor.parentElement.id) {{ e.preventDefault(); jumpTo(headAnchor.parentElement.id); return; }}
    const t = e.target.closest('[data-slug]');
    if (t) {{ e.preventDefault(); render(t.getAttribute('data-slug')); }}
  }});

  // contents flip (Browse wiki / Browse article)
  flip.addEventListener('click', function(e) {{
    const b = e.target.closest('button[data-mode]');
    if (b) setContentsMode(b.getAttribute('data-mode'));
  }});

  // hamburger + Hide/Move-to-sidebar both toggle the sidebar; label flips
  function toggleSidebar() {{
    const hidden = shell.classList.toggle('nosb');
    sideToggle.textContent = hidden ? 'Move to sidebar' : 'Hide';
  }}
  burger.addEventListener('click', toggleSidebar);
  sideToggle.addEventListener('click', toggleSidebar);

  // immersive reader: hide chrome, widen+center column; icon flips to ✕
  immersiveBtn.addEventListener('click', function() {{
    const on = shell.classList.toggle('immersive');
    document.body.classList.toggle('immersive', on);
    immersiveBtn.innerHTML = on ? '&#10005;' : '&#9776;';
    immersiveBtn.title = on ? 'Exit immersive reader' : 'Immersive reader';
  }});

  // search filters the whole-site tree (and flips back to Browse wiki to show hits)
  q.addEventListener('input', function() {{
    const v = q.value.trim().toLowerCase();
    if (v && contentsMode !== 'wiki') setContentsMode('wiki');
    let shown = 0;
    document.querySelectorAll('.tree-sec-box').forEach(function(box) {{
      let any = false;
      box.querySelectorAll('.tree-art').forEach(function(el) {{
        const slug = el.getAttribute('data-slug');
        const hay = (DATA[slug] ? DATA[slug].search : el.getAttribute('data-search')) || '';
        const hit = !v || hay.indexOf(v) >= 0;
        el.classList.toggle('hidden', !hit);
        if (hit) {{ shown++; any = true; }}
      }});
      if (v) box.open = any;  // auto-expand sections with matches, collapse the rest
    }});
    nores.style.display = shown ? 'none' : 'block';
  }});

  // scroll-spy: highlight the active heading in the article TOC
  read.addEventListener('scroll', function() {{
    if (contentsMode !== 'article') return;
    const heads = content.querySelectorAll('.body h2, .body h3');
    const base = read.getBoundingClientRect().top;
    let cur = null;
    heads.forEach(function(h) {{ if (h.getBoundingClientRect().top - base <= 70) cur = h.id; }});
    toc.querySelectorAll('a').forEach(function(a) {{
      a.classList.toggle('active', a.getAttribute('data-anchor') === cur);
    }});
  }});

  render({json.dumps(start)});
</script></body></html>
"""
    components.html(doc, height=1500, scrolling=False)
