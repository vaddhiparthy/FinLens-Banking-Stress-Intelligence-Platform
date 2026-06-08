# ruff: noqa: E501
"""Client-side wiki: the whole encyclopedia rendered once into a single components iframe so
browsing is instant (no Streamlit rerun per article). Article bodies are converted to HTML with
mistune; ``[[Title]]`` cross-links and the section tree navigate in-app via JS. The one article
with a live Graphviz diagram (System Architecture) stays on its Streamlit route (it keeps the
interactive pan/zoom diagram); the SPA links out to it.
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
        out[ws.slug(title)] = {
            "title": title,
            "summary": a.get("summary", ""),
            "html": body_html,
            "crumb": crumb,
            "prev": ws.slug(prev_t) if prev_t else None,
            "prevT": prev_t,
            "next": ws.slug(next_t) if next_t else None,
            "nextT": next_t,
            "search": " ".join([title, a.get("summary", ""), a.get("body", "")]).lower(),
        }
    # the System Architecture article carries the live Graphviz DOT; the SPA renders it client-side
    # (viz.js + svg-pan-zoom) so the diagram is interactive in-place — no cross-frame navigation.
    if ARCH_SLUG in out:
        out[ARCH_SLUG]["dot"] = wa.ARCHITECTURE_DOT
    return out


def _tree_html() -> str:
    """Static section tree; each leaf carries data-slug for instant in-app nav."""
    parts = ['<nav class="tree">']
    for _sid, stitle, groups in ws.SECTIONS:
        titles = [t for _s, ts in groups for t in ts if t in ws.ARTICLES]
        if not titles:
            continue
        parts.append(f'<div class="tree-sec">{_html.escape(stitle)}</div>')
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
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; font-family: "Inter", system-ui, -apple-system, sans-serif;
    color: {p['text_main']}; background: {p['page_bg']}; }}
  a {{ color: {p['accent_deep']}; text-decoration: none; }}
  a:hover {{ color: {p['accent']}; }}
  .wrap {{ display: grid; grid-template-columns: 17rem 1fr; gap: 1.4rem; height: 1480px;
    padding: .2rem .2rem .2rem 0; }}
  .side {{ border-right: 1px solid {p['border']}; padding-right: 1rem; overflow-y: auto; height: 100%; }}
  .brand {{ font-weight: 800; font-size: 1.15rem; }}
  .brand small {{ display: block; font-weight: 700; font-size: .58rem; letter-spacing: .12em;
    text-transform: uppercase; color: {p['accent']}; margin-top: .1rem; }}
  .stats {{ color: {p['text_soft']}; font-size: .68rem; margin: .5rem 0 .7rem; }}
  .search {{ width: 100%; padding: .5rem .6rem; border: 1px solid {p['border']}; border-radius: 10px;
    background: {p['content_bg']}; color: {p['text_main']}; font-size: .82rem; margin-bottom: .7rem; }}
  .tree-sec {{ font-size: .64rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase;
    color: {p['accent']}; margin: .85rem 0 .3rem; }}
  .tree-sub {{ font-size: .62rem; font-weight: 700; color: {p['text_soft']}; margin: .5rem 0 .2rem; }}
  .tree-art {{ display: block; padding: .25rem .5rem; border-left: 2px solid transparent;
    color: {p['text_muted']}; font-size: .82rem; cursor: pointer; border-radius: 0 6px 6px 0; }}
  .tree-art:hover {{ background: {p['content_bg']}; color: {p['text_main']}; }}
  .tree-art.active {{ border-left-color: {p['accent']}; color: {p['accent_deep']};
    font-weight: 700; background: {p['content_bg']}; }}
  .tree-art.hidden {{ display: none; }}
  /* the collapsible-tree toggle is desktop-hidden (tree always open in the grid); shown on mobile */
  #treebox > summary.tree-toggle {{ display: none; list-style: none; }}
  #treebox > summary.tree-toggle::-webkit-details-marker {{ display: none; }}
  .main {{ overflow-y: auto; height: 100%; padding-right: .6rem; }}
  .crumb {{ font-size: .72rem; color: {p['text_soft']}; font-weight: 600; }}
  .title {{ font-size: 1.9rem; font-weight: 800; margin: .15rem 0 .25rem; letter-spacing: -.01em; }}
  .lead {{ color: {p['text_muted']}; font-size: 1rem; line-height: 1.55; margin-bottom: 1.1rem;
    padding-bottom: .9rem; border-bottom: 1px solid {p['border']}; }}
  .body {{ font-size: .95rem; line-height: 1.7; color: {p['text_main']}; max-width: 46rem; }}
  .lead {{ max-width: 46rem; }}
  .body h2 {{ font-size: 1.3rem; margin: 1.5rem 0 .5rem; }}
  .body h3 {{ font-size: 1.08rem; margin: 1.2rem 0 .4rem; }}
  .body table {{ border-collapse: collapse; margin: .8rem 0; font-size: .85rem; }}
  .body th, .body td {{ border: 1px solid {p['border']}; padding: .4rem .6rem; text-align: left; }}
  .body th {{ background: {p['content_bg']}; }}
  .body code {{ background: {p['content_bg']}; padding: .1rem .3rem; border-radius: 5px;
    font-family: "JetBrains Mono", monospace; font-size: .85em; }}
  .body pre {{ background: {p['content_bg']}; border: 1px solid {p['border']}; border-radius: 10px;
    padding: .8rem 1rem; overflow-x: auto; }}
  .pager {{ display: flex; justify-content: space-between; gap: 1rem; margin: 1.8rem 0 1rem;
    padding-top: 1rem; border-top: 1px solid {p['border']}; }}
  .pager a {{ font-weight: 700; font-size: .85rem; cursor: pointer; }}
  .noresult {{ color: {p['text_soft']}; font-size: .8rem; padding: .4rem .5rem; }}
  .diagram {{ height: 340px; border: 1px solid {p['border']}; border-radius: 12px;
    background: {p['content_bg']}; overflow: hidden; margin: .2rem 0 1.3rem; }}
  .diagram svg {{ width: 100% !important; height: 100% !important; }}
  .diagram-msg {{ padding: 1rem; color: {p['text_soft']}; font-size: .85rem; }}
  .svg-pan-zoom-control-background {{ fill: {p['content_bg']}; opacity: .9; }}
  .svg-pan-zoom-control-element {{ fill: {p['accent']}; }}
  /* ---- mobile: stack the tree above full-width content; iframe height fits content (one scroll) ---- */
  @media (max-width: 700px) {{
    .wrap {{ grid-template-columns: 1fr; height: auto; gap: .6rem; padding: 0; }}
    .side {{ border-right: none; border-bottom: 1px solid {p['border']}; padding-right: 0;
      padding-bottom: .6rem; height: auto; overflow: visible; }}
    /* min-width:0 lets the grid item shrink below the wide svg's intrinsic size (no page overflow) */
    .main {{ height: auto; overflow: visible; padding-right: 0; min-width: 0 !important; }}
    .title {{ font-size: 1.5rem; }}
    .lead {{ font-size: .92rem; }}
    .body {{ font-size: .92rem; }}
    /* phone: show the diagram at natural (legible) size; the frame fits the svg's full HEIGHT so
       every node is visible (no vertical hunting / empty bands), and scrolls only HORIZONTALLY to
       pan the wide graph. Pinned to viewport width so the page never overflows. */
    .diagram {{ height: auto !important; width: 100% !important; max-width: 100% !important;
      min-width: 0 !important; overflow-x: auto !important; overflow-y: hidden !important;
      -webkit-overflow-scrolling: touch; }}
    .diagram svg {{ width: auto !important; height: auto !important; max-width: none !important;
      display: block; }}
    /* show the collapsible tree toggle as a tappable bar */
    #treebox > summary.tree-toggle {{
      display: flex; align-items: center; gap: .4rem; cursor: pointer;
      font-weight: 800; font-size: .8rem; letter-spacing: .04em; text-transform: uppercase;
      color: {p['accent']}; padding: .5rem .2rem; border: 1px solid {p['border']};
      border-radius: 10px; background: {p['content_bg']};
    }}
    #treebox > summary.tree-toggle::before {{ content: "☰"; font-size: .95rem; }}
    #treebox[open] > summary.tree-toggle::before {{ content: "✕"; }}
  }}
</style>
<script src="https://cdn.jsdelivr.net/npm/@viz-js/viz@3.2.4/lib/viz-standalone.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
</head><body>
<div class="wrap">
  <aside class="side">
    <div class="brand">FinLens Wiki<small>Banking Stress Intelligence</small></div>
    <div class="stats">{s['articles']} articles · {s['sections']} sections · ~{s['read_minutes']} min read</div>
    <input id="q" class="search" placeholder="Search the wiki…" autocomplete="off">
    <div id="noresult" class="noresult" style="display:none">No articles match.</div>
    <details id="treebox" open>
      <summary class="tree-toggle">Browse articles</summary>
      {tree}
    </details>
  </aside>
  <main class="main" id="main"></main>
</div>
<script>
  const DATA = {payload_js};
  const main = document.getElementById('main');
  const isMobile = window.matchMedia('(max-width: 700px)').matches;
  const treebox = document.getElementById('treebox');
  if (isMobile && treebox) treebox.removeAttribute('open');  // start collapsed on phones
  function fitHeight() {{
    // mobile only: grow the component iframe to fit content so the page has ONE natural scroll
    // (desktop keeps the fixed 1500px frame — untouched)
    if (!isMobile) return;
    try {{ if (window.frameElement) window.frameElement.style.height = (document.body.scrollHeight + 24) + 'px'; }}
    catch (e) {{ /* cross-origin: leave default height */ }}
  }}
  if (treebox) treebox.addEventListener('toggle', fitHeight);
  function setActive(slug) {{
    document.querySelectorAll('.tree-art').forEach(function(el) {{
      el.classList.toggle('active', el.getAttribute('data-slug') === slug);
    }});
  }}
  function renderDiagram(host, dot) {{
    // client-side Graphviz (viz.js) + pan/zoom, fit to frame; degrade gracefully if a CDN is down
    if (typeof Viz === 'undefined') {{
      host.innerHTML = '<div class="diagram-msg">Interactive diagram unavailable (offline).</div>';
      return;
    }}
    Viz.instance().then(function(viz) {{
      const svg = viz.renderSVGElement(dot);
      host.appendChild(svg);
      // Phone: render the diagram at natural size in a scrollable frame so node labels are legible
      // and the user pans by dragging/scrolling. svg-pan-zoom's fit-to-width shrank it to an
      // unreadable thumbnail and kept re-fitting whenever fitHeight() resized the iframe.
      // Desktop keeps the interactive pan/zoom diagram (unchanged).
      if (!isMobile && typeof svgPanZoom !== 'undefined') {{
        svgPanZoom(svg, {{ zoomEnabled: true, controlIconsEnabled: true, fit: true,
          center: true, minZoom: 0.3, maxZoom: 12, zoomScaleSensitivity: 0.4 }});
      }}
      fitHeight();
    }}).catch(function() {{
      host.innerHTML = '<div class="diagram-msg">Diagram failed to render.</div>';
    }});
  }}
  function render(slug) {{
    const a = DATA[slug];
    if (!a) return;
    let h = '<div class="crumb">' + (a.crumb || 'Wiki') + '</div>';
    h += '<div class="title">' + a.title + '</div>';
    if (a.summary) h += '<div class="lead">' + a.summary + '</div>';
    if (a.dot) h += '<div class="diagram" id="wiki-diagram"></div>';
    h += '<div class="body">' + a.html + '</div>';
    h += '<div class="pager">';
    h += a.prev ? '<a data-slug="' + a.prev + '">‹ ' + a.prevT + '</a>' : '<span></span>';
    h += a.next ? '<a data-slug="' + a.next + '">' + a.nextT + ' ›</a>' : '<span></span>';
    h += '</div>';
    main.innerHTML = h;
    main.scrollTop = 0;
    if (isMobile) window.scrollTo(0, 0);
    if (a.dot) renderDiagram(document.getElementById('wiki-diagram'), a.dot);
    setActive(slug);
    document.querySelectorAll('.tree-art').forEach(function(el) {{
      if (el.getAttribute('data-slug') === slug) el.scrollIntoView({{block: 'nearest'}});
    }});
    if (isMobile && treebox) treebox.removeAttribute('open');  // collapse tree after picking
    fitHeight();
  }}
  // delegate clicks: tree leaves, in-body wikilinks, pager
  document.addEventListener('click', function(e) {{
    const t = e.target.closest('[data-slug]');
    if (t) {{ e.preventDefault(); render(t.getAttribute('data-slug')); }}
  }});
  // search filters the tree
  const q = document.getElementById('q');
  const nores = document.getElementById('noresult');
  q.addEventListener('input', function() {{
    const v = q.value.trim().toLowerCase();
    if (isMobile && treebox && v) treebox.setAttribute('open', '');  // reveal filtered results
    let shown = 0;
    document.querySelectorAll('.tree-art').forEach(function(el) {{
      const slug = el.getAttribute('data-slug');
      const hay = (DATA[slug] ? DATA[slug].search : el.getAttribute('data-search')) || '';
      const hit = !v || hay.indexOf(v) >= 0;
      el.classList.toggle('hidden', !hit);
      if (hit) shown++;
    }});
    nores.style.display = shown ? 'none' : 'block';
    fitHeight();
  }});
  render({json.dumps(start)});
  window.addEventListener('load', fitHeight);
  window.addEventListener('resize', fitHeight);
  setTimeout(fitHeight, 400);
</script></body></html>
"""
    components.html(doc, height=1500, scrolling=False)
