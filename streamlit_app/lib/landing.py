"""Bento-grid landing: surfaces the highest value+aesthetic visuals (chosen by adversarial review)
as real-data preview tiles that click through to the live surfaces. Rendered as a single CSS-grid
block via st.markdown so it stays responsive (no fixed-height iframe) and the links navigate natively.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "landing"

# Real headline numbers (verified from ml/artifacts: panel_facts.json, viz_pack.json, metrics_h4.json).
_KPIS = [
    ("448,661", "bank-quarters analyzed"),
    ("8,803", "banks · 2008–2026"),
    ("0.855", "ROC-AUC, out-of-time"),
    ("54.5%", "failures caught in top 200"),
    ("$0", "infra · 100% public data"),
]


@lru_cache(maxsize=16)
def _data_uri(name: str) -> str:
    p = _ASSETS / name
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _img_tile(area: str, img: str, kicker: str, title: str, caption: str, href: str,
              badge: str = "", cta: str = "") -> str:
    badge_html = f'<span class="fl-badge">{badge}</span>' if badge else ""
    cta_html = f'<span class="fl-cta">{cta} →</span>' if cta else '<span class="fl-cta">Open →</span>'
    return f"""
    <a class="fl-tile fl-img" style="grid-area:{area}" href="{href}" target="_self">
      <div class="fl-figwrap"><img src="{_data_uri(img)}" alt="{title}"/>{badge_html}</div>
      <div class="fl-meta">
        <div><span class="fl-kicker">{kicker}</span>
        <span class="fl-title">{title}</span>
        <span class="fl-cap">{caption}</span></div>
        {cta_html}
      </div>
    </a>"""


def _entry_tile(area: str, icon: str, title: str, caption: str, href: str) -> str:
    return f"""
    <a class="fl-tile fl-entry" style="grid-area:{area}" href="{href}" target="_self">
      <span class="fl-ico">{icon}</span>
      <div><span class="fl-title">{title}</span><span class="fl-cap">{caption}</span></div>
      <span class="fl-arrow">→</span>
    </a>"""


def render_landing() -> None:
    kpis = "".join(
        f'<div class="fl-kpi"><span class="fl-num">{n}</span>'
        f'<span class="fl-klabel">{l}</span></div>'
        for n, l in _KPIS
    )

    hero = f"""
    <a class="fl-tile fl-img fl-hero" style="grid-area:hero" href="Early_Warning" target="_self">
      <div class="fl-figwrap fl-gaugewrap">
        <img src="{_data_uri('gauge.png')}" alt="distress gauge"/>
        <div class="fl-gauge-overlay">
          <span class="fl-gauge-val">79.9%</span>
          <span class="fl-gauge-sub">probability of distress</span>
        </div>
        <span class="fl-badge">HIGH RISK</span>
      </div>
      <div class="fl-meta">
        <div><span class="fl-kicker">Live model inference</span>
        <span class="fl-title">Score any U.S. bank for distress</span>
        <span class="fl-cap">Calibrated probability of failure within four quarters, backtested here
        on a bank that actually failed.</span></div>
        <span class="fl-cta">Score a bank →</span>
      </div>
    </a>"""
    tiles = [
        hero,
        _img_tile("map", "map.png", "Geography", "Where banks fail",
                  "FDIC failures by state, 2008–2026.", "Business_Dashboard", cta="Business"),
        _img_tile("pr", "prcurve.png", "Model quality", "Precision–recall, out-of-time",
                  "PR-AUC 0.301 against a 0.06% failure base rate.", "Technical_Dashboard",
                  cta="Technical"),
        _img_tile("shap", "shap.png", "Explainability", "What drives each score",
                  "Global SHAP feature attribution.", "AI_Engineering", cta="AI pipeline"),
        _img_tile("sankey", "sankey.png", "Data engineering", "The live pipeline",
                  "FDIC · FFIEC · FRED → Bronze → Silver → Gold, quality-gated.",
                  "Data_Engineering", cta="Data engineering"),
        _entry_tile("chat", "◆", "Ask the model", "Cited assistant + live read.", "AI_Inference"),
        _entry_tile("wiki", "❖", "FinLens-Wiki", "The full encyclopedia.", "Wiki"),
        _entry_tile("arch", "▦", "Architecture", "Full-screen, zoomable system diagram.",
                    "Architecture"),
    ]

    html = f"""
<div class="fl-bento">
  <div class="fl-lede">An early-warning read on U.S. bank distress, built end to end from free
    public data and a calibrated, SHAP-explained machine-learning model.</div>
  <div class="fl-kpis">{kpis}</div>
  <div class="fl-grid">{''.join(tiles)}</div>
</div>
{_CSS}
"""
    st.markdown(html, unsafe_allow_html=True)


_CSS = """
<style>
.fl-bento {max-width: 1180px; margin: .1rem auto 1rem; padding: 0 .4rem;}
.fl-lede {text-align:center; max-width: 680px; margin: 0 auto 1.1rem; color:#5a4d3e !important;
  font-size: 1.0rem; line-height: 1.55;}
/* Kill Streamlit's default link-blue everywhere inside the bento; brand colors win. */
.fl-bento a, .fl-bento a:link, .fl-bento a:visited, .fl-bento a:hover {color:#1f2933 !important;
  text-decoration:none !important;}
.fl-kpis {display:grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 1.25rem;}
.fl-kpi {background:#fffaf3; border:1px solid #ece1d0; border-top:3px solid #bf6d47;
  border-radius:12px; padding:1rem .6rem .85rem; text-align:center;}
.fl-num {display:block; font-size:1.9rem; font-weight:800; color:#1f2933 !important;
  letter-spacing:-.015em; font-variant-numeric: tabular-nums; line-height:1;}
.fl-klabel {display:block; font-size:.64rem; font-weight:700; text-transform:uppercase;
  letter-spacing:.07em; color:#8a7a67 !important; margin-top:.4rem; line-height:1.25;}
.fl-grid {display:grid; grid-template-columns: repeat(6, 1fr);
  grid-template-rows: 172px 172px 184px 108px; gap:18px;
  grid-template-areas:
    "hero hero hero hero map  map"
    "hero hero hero hero pr   pr"
    "shap shap sankey sankey sankey sankey"
    "chat chat wiki wiki arch arch";}
.fl-tile {display:flex; flex-direction:column; background:#fffaf3; border:1px solid #e7dccb;
  border-radius:16px; padding:.75rem .85rem; overflow:hidden;
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;}
.fl-tile:hover {transform: translateY(-3px); border-color:#bf6d47;
  box-shadow: 0 16px 38px rgba(31,41,51,.14);}
.fl-img .fl-figwrap {position:relative; flex:1; min-height:0; display:flex; align-items:center;
  justify-content:center; padding:.1rem;}
.fl-img img {max-width:100%; max-height:100%; width:auto; object-fit:contain;}
.fl-badge {position:absolute; top:6px; right:6px; background:#8f3f22 !important; color:#fff7ef !important;
  font-size:.6rem; font-weight:800; letter-spacing:.07em; padding:.22rem .55rem; border-radius:999px;}
.fl-meta {display:flex; align-items:flex-end; justify-content:space-between; gap:.5rem;
  margin-top:.5rem;}
.fl-kicker {display:block; font-size:.57rem; font-weight:800; text-transform:uppercase;
  letter-spacing:.13em; color:#bf6d47 !important;}
.fl-title {display:block; font-weight:800; color:#1f2933 !important; font-size:.96rem;
  line-height:1.2; margin-top:.14rem;}
.fl-cap {display:block; font-size:.72rem; color:#8a7766 !important; line-height:1.35;
  margin-top:.2rem;}
.fl-cta, .fl-arrow {white-space:nowrap; font-size:.74rem; font-weight:800; color:#bf6d47 !important;}
.fl-tile[style*="hero"] {padding:1rem 1.1rem;}
.fl-tile[style*="hero"] .fl-title {font-size:1.3rem;}
.fl-tile[style*="hero"] .fl-cap {font-size:.84rem; max-width:60ch;}
.fl-tile[style*="hero"] .fl-figwrap {padding:.1rem .4rem; align-items:flex-end;}
.fl-tile[style*="hero"] .fl-gaugewrap img {max-height:none; width:86%;}
/* gauge value overlaid as perfectly-centered HTML (the chart is arc-only) */
.fl-gaugewrap {position:relative;}
.fl-gauge-overlay {position:absolute; left:0; right:0; bottom:11%; text-align:center;
  pointer-events:none;}
.fl-gauge-val {display:block; font-size:2.9rem; font-weight:800; color:#1f2933 !important;
  line-height:1; letter-spacing:-.02em; font-variant-numeric:tabular-nums;}
.fl-gauge-sub {display:block; font-size:.6rem; font-weight:800; text-transform:uppercase;
  letter-spacing:.12em; color:#8a7766 !important; margin-top:.35rem;}
.fl-entry {flex-direction:row; align-items:center; gap:.7rem; justify-content:flex-start;}
.fl-entry .fl-ico {font-size:1.15rem; color:#bf6d47 !important; background:#f4e8da;
  width:2.1rem; height:2.1rem; display:flex; align-items:center; justify-content:center;
  border-radius:10px; flex:none;}
.fl-entry .fl-arrow {margin-left:auto; font-size:1.05rem;}
/* trim the trailing empty band below the footer on the landing */
[data-testid="stMainBlockContainer"] {padding-bottom: 1.4rem !important;}
/* the map fills its tile (crops the redundant in-chart title + colorbar margins) */
.fl-tile[style*="map"] .fl-figwrap {padding:0;}
.fl-tile[style*="map"] img {object-fit:cover; width:100%; height:100%; object-position:50% 48%;}
@media (max-width: 820px) {
  .fl-tile[style*="map"] img {object-fit:contain;}
  .fl-kpis {grid-template-columns: repeat(2, 1fr); gap:10px;}
  .fl-kpi {padding:.6rem .5rem .55rem;}
  .fl-num {font-size:1.5rem;}
  .fl-klabel {margin-top:.25rem; font-size:.6rem;}
  .fl-grid {grid-template-columns: 1fr; grid-template-rows: none; gap:14px;
    grid-template-areas: "hero" "map" "pr" "shap" "sankey" "chat" "wiki" "arch";}
  .fl-img .fl-figwrap {min-height: 160px;}
  .fl-tile[style*="hero"] .fl-figwrap {min-height: 200px;}
  .fl-gauge-val {font-size:2.4rem;}
  .hdr-name {text-align:center !important;}
}
</style>
"""
