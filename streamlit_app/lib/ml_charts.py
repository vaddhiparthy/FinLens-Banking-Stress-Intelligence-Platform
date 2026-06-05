"""Plotly figures for the AI Engineering surface, driven entirely by the real
viz-pack (ml/artifacts/viz_pack.json) baked from the trained model + panel.

No fabrication: every series here is a real out-of-time measurement. Figures are
themed from the active palette so they read in both light and dark mode.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import plotly.graph_objects as go

from streamlit_app.lib.theme import get_palette

_PROJECT_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()
)
_VIZ_PATH = _PROJECT_ROOT / "ml" / "artifacts" / "viz_pack.json"


@lru_cache(maxsize=1)
def load_viz_pack() -> dict | None:
    if not _VIZ_PATH.exists():
        return None
    return json.loads(_VIZ_PATH.read_text())


def _base(fig: go.Figure, pal: dict, *, height: int = 340, title: str = "",
          legend: bool = True) -> go.Figure:
    # Title pinned at the very top; legend sits at the BOTTOM so the two never collide.
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=pal["text_main"]),
                   x=0, xanchor="left", y=0.97, yanchor="top") if title else None,
        height=height,
        margin=dict(l=10, r=12, t=38 if title else 12, b=54 if legend else 14),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=pal["text_muted"], size=11),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0,
                    font=dict(color=pal["text_muted"], size=10), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=pal["border"], zerolinecolor=pal["border"]),
        yaxis=dict(gridcolor=pal["border"], zerolinecolor=pal["border"]),
    )
    return fig


def pr_curve_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    c = pack["curves"]
    lg = pack.get("logit_curves", {})
    fig = go.Figure()
    if lg.get("pr_curve"):
        fig.add_scatter(
            x=[p[0] for p in lg["pr_curve"]], y=[p[1] for p in lg["pr_curve"]],
            mode="lines", name=f"Logit benchmark (AP {lg.get('pr_auc')})",
            line=dict(color=pal["text_soft"], width=1.6, dash="dot"),
        )
    fig.add_scatter(
        x=[p[0] for p in c["pr_curve"]], y=[p[1] for p in c["pr_curve"]],
        mode="lines", name=f"Calibrated LGBM (AP {c['pr_auc']})",
        line=dict(color=pal["accent"], width=2.4),
    )
    fig.add_hline(y=c["base_rate"], line=dict(color=pal["rose"], width=1, dash="dash"),
                  annotation_text=f"base rate {c['base_rate']:.3%}",
                  annotation_font=dict(size=9, color=pal["rose"]))
    fig.update_xaxes(title="Recall", range=[0, 1])
    fig.update_yaxes(title="Precision", range=[0, max(0.2, max(p[1] for p in c["pr_curve"]) * 1.1)])
    return _base(fig, pal, title="Precision-Recall (out-of-time)")


def roc_curve_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    c = pack["curves"]
    lg = pack.get("logit_curves", {})
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="chance",
                    line=dict(color=pal["border"], width=1, dash="dash"), showlegend=False)
    if lg.get("roc_curve"):
        fig.add_scatter(
            x=[p[0] for p in lg["roc_curve"]], y=[p[1] for p in lg["roc_curve"]],
            mode="lines", name=f"Logit (AUC {lg.get('roc_auc')})",
            line=dict(color=pal["text_soft"], width=1.6, dash="dot"),
        )
    fig.add_scatter(
        x=[p[0] for p in c["roc_curve"]], y=[p[1] for p in c["roc_curve"]],
        mode="lines", name=f"Calibrated LGBM (AUC {c['roc_auc']})",
        line=dict(color=pal["accent"], width=2.4),
    )
    fig.update_xaxes(title="False positive rate", range=[0, 1])
    fig.update_yaxes(title="True positive rate", range=[0, 1])
    return _base(fig, pal, title="ROC (out-of-time)")


def calibration_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    rows = pack["calibration"]
    fig = go.Figure()
    fig.add_scatter(x=[0, max(r["pred"] for r in rows) or 1], y=[0, max(r["pred"] for r in rows) or 1],
                    mode="lines", name="perfect", line=dict(color=pal["border"], width=1, dash="dash"))
    fig.add_scatter(
        x=[r["pred"] for r in rows], y=[r["obs"] for r in rows],
        mode="lines+markers", name="observed",
        line=dict(color=pal["accent"], width=2),
        marker=dict(size=[max(5, min(18, (r["n"] ** 0.5) / 3)) for r in rows], color=pal["accent"]),
    )
    fig.update_xaxes(title="Predicted probability")
    fig.update_yaxes(title="Observed failure rate")
    return _base(fig, pal, title="Calibration reliability (bubble = bin size)")


def score_dist_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    d = pack["score_distribution"]
    fig = go.Figure()
    fig.add_bar(x=d["centers"], y=d["survived"], name="survived",
                marker_color=pal["text_soft"], opacity=0.65)
    fig.add_bar(x=d["centers"], y=d["failed"], name="failed (within 4q)",
                marker_color=pal["rose"])
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Predicted distress probability")
    fig.update_yaxes(title="Bank-quarters (log)", type="log")
    return _base(fig, pal, title="Score separation: failed vs survived")


def threshold_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    s = pack["threshold_sweep"]
    fig = go.Figure()
    fig.add_scatter(x=[r["threshold"] for r in s], y=[r["precision"] for r in s],
                    mode="lines", name="precision", line=dict(color=pal["accent"], width=2))
    fig.add_scatter(x=[r["threshold"] for r in s], y=[r["recall"] for r in s],
                    mode="lines", name="recall", line=dict(color=pal["teal"], width=2))
    fig.update_xaxes(title="Flag threshold (calibrated probability)")
    fig.update_yaxes(title="Rate", range=[0, 1])
    return _base(fig, pal, title="Precision / recall vs flag threshold")


def shap_importance_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    rows = list(reversed(pack["shap_importance"]))
    labels = [r["feature"].replace("_", " ") for r in rows]
    fig = go.Figure()
    fig.add_bar(x=[r["mean_abs_shap"] for r in rows], y=labels, orientation="h",
                marker_color=pal["accent"])
    fig.update_xaxes(title="mean |SHAP| (impact on model output)")
    return _base(fig, pal, height=420, legend=False, title="Global feature importance (SHAP)")


def correlation_fig(pack: dict, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    c = pack["correlation"]
    labels = [f.replace("_", " ") for f in c["features"]]
    fig = go.Figure(go.Heatmap(
        z=c["matrix"], x=labels, y=labels,
        colorscale=[[0, pal["rose"]], [0.5, pal["content_bg"]], [1, pal["accent"]]],
        zmid=0, zmin=-1, zmax=1,
        colorbar=dict(title="r", tickfont=dict(color=pal["text_muted"], size=9)),
    ))
    fig.update_xaxes(tickangle=45, tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9))
    return _base(fig, pal, height=460, legend=False, title="Feature correlation (top SHAP features)")


def by_year_fig(pack_by_year: list, mode: str | None = None) -> go.Figure:
    pal = get_palette(mode)
    rows = [r for r in pack_by_year if r.get("pr_auc") is not None]
    fig = go.Figure()
    fig.add_bar(x=[str(r["year"]) for r in rows], y=[r["pr_auc"] for r in rows],
                name="PR-AUC", marker_color=pal["accent"])
    fig.add_scatter(x=[str(r["year"]) for r in rows], y=[r.get("failures", 0) and r["pr_auc"] for r in rows],
                    mode="markers", name="", showlegend=False, marker=dict(opacity=0))
    fig.update_yaxes(title="PR-AUC", range=[0, 1])
    return _base(fig, pal, legend=False, title="Out-of-time PR-AUC by year")


def probability_gauge(prob: float, threshold: float, mode: str | None = None) -> go.Figure:
    """A calibrated-probability gauge for one bank, banded green / amber / red."""
    pal = get_palette(mode)
    green, amber, red = pal["teal"], pal.get("sand", "#c69026"), pal["rose"]
    amber = "#c69026"
    pct = prob * 100
    cap = max(pct * 1.5, threshold * 100 * 2.5, 20)
    cap = min(cap, 100)
    bar = red if prob >= threshold else (amber if prob >= threshold / 2 else green)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(pct, 2),
        number={"suffix": "%", "font": {"size": 30, "color": pal["text_main"]}},
        gauge={
            "axis": {"range": [0, cap], "tickcolor": pal["text_soft"],
                     "tickfont": {"size": 9, "color": pal["text_soft"]}},
            "bar": {"color": bar, "thickness": 0.7},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, threshold * 100 / 2], "color": "rgba(87,171,90,0.12)"},
                {"range": [threshold * 100 / 2, threshold * 100], "color": "rgba(198,144,38,0.14)"},
                {"range": [threshold * 100, cap], "color": "rgba(229,83,75,0.12)"},
            ],
            "threshold": {"line": {"color": pal["text_soft"], "width": 2}, "thickness": 0.8,
                          "value": threshold * 100},
        },
    ))
    fig.update_layout(height=240, margin=dict(l=24, r=24, t=28, b=28),
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color=pal["text_muted"]))
    return fig


def drift_fig(pack: dict, mode: str | None = None) -> go.Figure | None:
    pal = get_palette(mode)
    feats = pack.get("drift_top_features") or []
    if not feats:
        return None
    # top_drifted_features is list[{feature, drift}] (or list[str] fallback)
    if isinstance(feats[0], dict):
        labels = [f.get("feature", "") for f in feats]
        scores = [f.get("drift", f.get("score", f.get("drift_score", 0))) for f in feats]
    else:
        labels = list(feats)
        scores = [1] * len(feats)
    labels = [str(label).replace("_", " ") for label in labels]
    fig = go.Figure()
    fig.add_bar(x=scores[::-1], y=labels[::-1], orientation="h", marker_color=pal["teal"],
                text=[f"{s:.2f}" for s in scores[::-1]], textposition="outside")
    fig.update_xaxes(title="drift score (PSI / statistical distance)", range=[0, max(scores) * 1.25])
    return _base(fig, pal, height=300, legend=False,
                 title="Most-drifted features (reference 2008-18 vs current)")
