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
    """ALL years on the x-axis (no silent drop of calm cohorts). Years with n_pos>=3
    draw a real PR-AUC bar; calm years (n_pos<3) draw a muted floor/pooled bar with a
    'low power' annotation, so the near-floor-in-calm-years story is VISIBLE."""
    pal = get_palette(mode)
    rows = sorted(pack_by_year, key=lambda r: str(r.get("year")))
    fig = go.Figure()
    real_x, real_y, calm_x, calm_y, notes = [], [], [], [], []
    for r in rows:
        yr = str(r.get("year"))
        npos = r.get("n_pos", r.get("failures", 0)) or 0
        pr = r.get("pr_auc")
        low = r.get("low_power", npos < 3)
        if not low and pr is not None and pr == pr:
            real_x.append(yr); real_y.append(pr)
        else:
            val = r.get("pooled_pr_auc")
            calm_x.append(yr); calm_y.append(val if (val is not None and val == val) else 0.0)
            notes.append((yr, val))
    if real_x:
        fig.add_bar(x=real_x, y=real_y, name="PR-AUC (n_pos≥3)", marker_color=pal["accent"])
    if calm_x:
        fig.add_bar(x=calm_x, y=calm_y, name="calm year (n_pos<3, low power)",
                    marker_color=pal["text_soft"], opacity=0.5)
        for yr, val in notes:
            fig.add_annotation(x=yr, y=(val or 0.0), yshift=10, text="low power",
                               showarrow=False, font=dict(size=8, color=pal["text_soft"]))
    fig.update_yaxes(title="PR-AUC", range=[0, 1])
    return _base(fig, pal, legend=True, title="Out-of-time PR-AUC by year (all cohorts shown)")


def psi_fig(pack: dict, mode: str | None = None) -> go.Figure | None:
    """Population Stability Index per feature (reference <=2018 vs current 2019+),
    with the standard 0.1 (moderate) and 0.25 (significant) reference lines."""
    pal = get_palette(mode)
    rows = pack.get("psi") or []
    if not rows:
        return None
    rows = rows[:12][::-1]
    labels = [r["feature"].replace("_", " ") for r in rows]
    vals = [r["psi"] for r in rows]
    colors = [pal["rose"] if v >= 0.25 else ("#c69026" if v >= 0.1 else pal["teal"]) for v in vals]
    fig = go.Figure()
    fig.add_bar(x=vals, y=labels, orientation="h", marker_color=colors,
                text=[f"{v:.2f}" for v in vals], textposition="outside")
    fig.add_vline(x=0.1, line=dict(color=pal["text_soft"], width=1, dash="dot"))
    fig.add_vline(x=0.25, line=dict(color=pal["rose"], width=1, dash="dot"))
    fig.update_xaxes(title="PSI (>0.1 moderate shift, >0.25 significant)",
                     range=[0, max(max(vals) * 1.25, 0.3)])
    return _base(fig, pal, height=360, legend=False,
                 title="Feature stability (PSI): reference vs current")


def probability_gauge(prob: float, threshold: float, mode: str | None = None,
                      cap: float | None = None) -> go.Figure:
    """A calibrated-probability gauge for one bank, banded green / amber / red. `cap` sets the
    axis maximum as a percentage (default 100). A smaller cap makes small, realistic distress
    probabilities (and slider moves) visible instead of a frozen needle near zero."""
    pal = get_palette(mode)
    green, amber, red = pal["teal"], pal.get("sand", "#c69026"), pal["rose"]
    amber = "#c69026"
    pct = prob * 100
    cap = 100.0 if cap is None else max(threshold * 100 * 1.2, float(cap))
    ndp = 2 if cap >= 20 else 3  # more decimals when the axis is zoomed in
    ticks = [round(cap * f, 2) for f in (0, 0.25, 0.5, 0.75, 1.0)]
    bar = red if prob >= threshold else (amber if prob >= threshold / 2 else green)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(pct, ndp),
        number={"suffix": "%", "font": {"size": 30, "color": pal["text_main"]}},
        gauge={
            "axis": {"range": [0, cap], "tickcolor": pal["text_soft"],
                     "tickvals": ticks, "ticksuffix": "%",
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


# ---- Tier A presentation: tuning, optimism, ablation (read m['study'] / pack) ----

def optuna_history_fig(study: dict, mode: str | None = None) -> go.Figure:
    """Best-so-far inner-CV PR-AUC over Optuna trials. Reads study['opt_history']."""
    pal = get_palette(mode)
    hist = study.get("opt_history") or []
    fig = go.Figure()
    fig.add_scatter(x=list(range(1, len(hist) + 1)), y=hist, mode="lines",
                    name="best inner-CV PR-AUC", line=dict(color=pal["accent"], width=2))
    fig.update_xaxes(title="trial")
    fig.update_yaxes(title="best inner-CV PR-AUC")
    return _base(fig, pal, height=300, legend=False, title="Hyperparameter search progress")


def optuna_importance_fig(study: dict, mode: str | None = None) -> go.Figure:
    """Hyperparameter importance (fANOVA). Reads study['param_importance'] (dict).
    Degenerate guard: <2 varied params -> single bar + note."""
    pal = get_palette(mode)
    imp = study.get("param_importance") or {}
    items = sorted(imp.items(), key=lambda kv: kv[1])
    fig = go.Figure()
    if len(items) < 2:
        lbl = items[0][0] if items else "n/a"
        val = items[0][1] if items else 0.0
        fig.add_bar(x=[val], y=[lbl], orientation="h", marker_color=pal["text_soft"])
        fig.add_annotation(x=0, y=0, yshift=20, xref="paper", text="single dominant param",
                           showarrow=False, font=dict(size=9, color=pal["text_soft"]))
    else:
        fig.add_bar(x=[v for _, v in items], y=[k.replace("_", " ") for k, v in items],
                    orientation="h", marker_color=pal["accent"])
    fig.update_xaxes(title="relative importance")
    return _base(fig, pal, height=320, legend=False, title="Which hyperparameters mattered")


def optuna_slice_fig(study: dict, mode: str | None = None, n: int = 4) -> go.Figure | None:
    """Top-n param slice scatters (param value vs inner-fold PR-AUC). Returns None when
    study['slice_signal_ok'] is False (noise-dominated at low n_pos -> suppress)."""
    pal = get_palette(mode)
    if not study.get("slice_signal_ok", True):
        return None
    slices = study.get("slices") or {}
    facet_npos = study.get("slice_facet_n_pos") or {}
    params = list(slices.keys())[:n]
    if not params:
        return None
    from plotly.subplots import make_subplots
    rows = (len(params) + 1) // 2
    fig = make_subplots(rows=rows, cols=2, subplot_titles=[p.replace("_", " ") for p in params])
    for i, p in enumerate(params):
        r, c = i // 2 + 1, i % 2 + 1
        pts = slices[p]
        fig.add_scatter(x=[d[0] for d in pts], y=[d[1] for d in pts], mode="markers",
                        marker=dict(color=pal["accent"], size=5), showlegend=False, row=r, col=c)
        np_med = facet_npos.get(p)
        if np_med is not None:
            sfx = "" if i == 0 else str(i + 1)
            fig.add_annotation(text=f"median n_pos≈{np_med}", showarrow=False,
                               xref=f"x{sfx} domain", yref=f"y{sfx} domain", x=0.5, y=1.0,
                               font=dict(size=8, color=pal["text_soft"]), row=r, col=c)
    return _base(fig, pal, height=180 * rows + 60, legend=False,
                 title="Param slices (inner-fold PR-AUC)")


def trial_stability_fig(study: dict, mode: str | None = None) -> go.Figure:
    """Per-trial inner-fold PR-AUC spread. Reads study['trial_stability'] = list of
    {trial, mean, std} or per-fold arrays."""
    pal = get_palette(mode)
    ts = study.get("trial_stability") or []
    fig = go.Figure()
    x = [t.get("trial", i) for i, t in enumerate(ts)]
    means = [t.get("mean") for t in ts]
    stds = [t.get("std", 0) for t in ts]
    fig.add_scatter(x=x, y=means, mode="markers", name="trial mean",
                    marker=dict(color=pal["accent"], size=4),
                    error_y=dict(type="data", array=stds, color=pal["text_soft"], thickness=0.6))
    fig.update_xaxes(title="trial")
    fig.update_yaxes(title="inner-fold PR-AUC (mean ± std)")
    return _base(fig, pal, height=300, legend=False, title="Trial stability across inner folds")


def optimism_fig(study: dict, mode: str | None = None) -> go.Figure:
    """Inner-CV PR-AUC vs OOT PR-AUC (the optimism gap). Reads study['optimism'] =
    {inner_pr_auc, oot_pr_auc, gap, ratio}."""
    pal = get_palette(mode)
    o = study.get("optimism") or {}
    inner, oot = o.get("inner_pr_auc", 0), o.get("oot_pr_auc", 0)
    fig = go.Figure()
    fig.add_bar(x=["inner-CV", "out-of-time"], y=[inner, oot],
                marker_color=[pal["text_soft"], pal["accent"]],
                text=[f"{inner:.3f}", f"{oot:.3f}"], textposition="outside")
    ratio = o.get("ratio")
    if ratio:
        fig.add_annotation(x=0.5, xref="paper", y=max(inner, oot), yshift=18,
                           text=f"optimism ratio {ratio:.1f}× (expected, not a defect)",
                           showarrow=False, font=dict(size=10, color=pal["text_muted"]))
    fig.update_yaxes(title="PR-AUC", range=[0, max(inner, oot) * 1.25 or 1])
    return _base(fig, pal, height=300, legend=False, title="Optimism: inner-CV vs out-of-time")


def ablation_forest_fig(pack: dict, mode: str | None = None) -> go.Figure:
    """Effective-challenge ladder as a point+interval forest on a FIXED [0,0.35] axis;
    rungs ordered by point estimate. CIs overlap by construction at n_pos≈66 — the
    subtitle states that so overlap reads as expected, not inconclusive."""
    pal = get_palette(mode)
    rungs = (pack.get("ablation") or {}).get("rungs") or []
    rungs = sorted(rungs, key=lambda r: (r.get("ap_point") is not None, r.get("ap_point") or 0))
    fig = go.Figure()
    for r in rungs:
        name = r["name"][:26]
        pt = r.get("ap_point")
        status = r.get("status", "shipped")
        if pt is None:
            fig.add_scatter(x=[0.01], y=[name], mode="markers",
                            marker=dict(color=pal["text_soft"], size=8, symbol="x"),
                            name=status, showlegend=False)
            fig.add_annotation(x=0.01, y=name, text=f"  {status}", showarrow=False,
                               xanchor="left", font=dict(size=9, color=pal["text_soft"]))
            continue
        ci = r.get("ap_ci") or [pt, pt]
        grey = status in ("did_not_ship",) or "nconstrained" in r["name"]
        color = pal["text_soft"] if grey else pal["accent"]
        fig.add_scatter(x=[pt], y=[name], mode="markers",
                        marker=dict(color=color, size=10),
                        error_x=dict(type="data", symmetric=False,
                                     array=[ci[1] - pt], arrayminus=[pt - ci[0]],
                                     color=color, thickness=1.2),
                        name=name, showlegend=False,
                        hovertext=f"AP {pt:.3f} CI[{ci[0]:.3f},{ci[1]:.3f}] "
                                  f"P(>shipped)={r.get('p_better_vs_shipped','-')}")
    # shipped reference = the actual served model's OOT PR-AUC (from the pack), not a
    # hardcoded value; label it with that number so it never contradicts the headline.
    served = (pack.get("curves") or {}).get("pr_auc")
    if served is not None:
        fig.add_vline(x=served, line=dict(color=pal["rose"], width=1.2, dash="dash"),
                      annotation_text=f"shipped {served:.3f}",
                      annotation_font=dict(size=9, color=pal["rose"]))
    # x-axis must contain the widest CI whisker (not a hardcoded cap that clips them and
    # makes the uncertainty look smaller than it is).
    ci_his = [r.get("ap_ci")[1] for r in rungs if r.get("ap_ci")]
    xmax = round(max([0.35] + [h * 1.05 for h in ci_his]), 2)
    fig.update_xaxes(title="OOT PR-AUC (average precision)", range=[0, xmax])
    # explanation placed ABOVE the title (separate rows, generous top margin) so the two
    # never overprint.
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1.20, showarrow=False,
                       xanchor="left", font=dict(size=9, color=pal["text_muted"]),
                       text="CIs overlap by construction at n_pos≈66; rank by point estimate, "
                            "not CI separation. The served model is the 12-seed BAGGED ensemble; "
                            "the single, tuned, and unconstrained models are challengers, "
                            "none statistically separable at this positive count.")
    fig = _base(fig, pal, height=380, legend=False)
    fig.update_layout(margin=dict(l=10, r=12, t=72, b=14),
                      title=dict(text="Effective-challenge ladder", x=0, xanchor="left",
                                 y=0.99, yanchor="top",
                                 font=dict(size=13, color=pal["text_main"])))
    return fig


def multi_horizon_pr_fig(pack: dict, mode: str | None = None) -> go.Figure | None:
    """4q vs 8q PR curves (different holdouts/base rates, labeled distinctly). Returns
    None if pack['curves_h8'] is absent (8q not headline-eligible)."""
    pal = get_palette(mode)
    c4 = pack.get("curves"); c8 = pack.get("curves_h8")
    if not c8:
        return None
    fig = go.Figure()
    fig.add_scatter(x=[p[0] for p in c4["pr_curve"]], y=[p[1] for p in c4["pr_curve"]],
                    mode="lines", name=f"4-quarter (AP {c4['pr_auc']})",
                    line=dict(color=pal["accent"], width=2.2))
    fig.add_scatter(x=[p[0] for p in c8["pr_curve"]], y=[p[1] for p in c8["pr_curve"]],
                    mode="lines", name=f"8-quarter (AP {c8['pr_auc']})",
                    line=dict(color=pal["teal"], width=2.2, dash="dot"))
    fig.add_hline(y=c4["base_rate"], line=dict(color=pal["accent"], width=1, dash="dash"),
                  annotation_text="4q base rate", annotation_font=dict(size=8, color=pal["accent"]))
    fig.add_hline(y=c8["base_rate"], line=dict(color=pal["teal"], width=1, dash="dash"),
                  annotation_text="8q base rate", annotation_font=dict(size=8, color=pal["teal"]))
    fig.update_xaxes(title="Recall", range=[0, 1])
    fig.update_yaxes(title="Precision", range=[0, 1])
    return _base(fig, pal, height=340, title="Multi-horizon PR (different denominators)")


def capacity_curve_fig(pack: dict, mode: str | None = None) -> go.Figure:
    """Recall vs review budget k (banks flagged). Reads pack['capacity_curve'] =
    list of {k, recall, precision}. No vague population-% anchor string."""
    pal = get_palette(mode)
    cc = pack.get("capacity_curve") or []
    fig = go.Figure()
    fig.add_scatter(x=[d["k"] for d in cc], y=[d["recall"] for d in cc], mode="lines",
                    name="recall@k", line=dict(color=pal["accent"], width=2.2))
    fig.add_scatter(x=[d["k"] for d in cc], y=[d.get("precision", 0) for d in cc], mode="lines",
                    name="precision@k", line=dict(color=pal["teal"], width=1.8, dash="dot"))
    fig.update_xaxes(title="review budget k (banks flagged)")
    fig.update_yaxes(title="rate", range=[0, 1])
    return _base(fig, pal, height=320, title="Capacity curve: recall vs review budget")


@lru_cache(maxsize=1)
def load_decomposition() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "failure_decomposition.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_sequence() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "sequence_challenger.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_pooled_vs_addressable() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "pooled_vs_addressable.json"
    return json.loads(p.read_text()) if p.exists() else None


_PVA_LABEL = {"monotone_gbm_served": "Monotone GBM (served)", "unconstrained_gbm": "Unconstrained GBM",
              "penalized_logit": "Penalized logit", "random_forest": "Random forest", "xgboost": "XGBoost"}


def pooled_vs_addressable_fig(pva: dict, mode: str | None = None) -> go.Figure:
    """The robustness proof: pooled vs addressable PR-AUC for EVERY model family. The
    addressable lift is positive across all of them, so the gap is a property of the
    evaluation set (the structurally-invisible failures), not of any one model."""
    pal = get_palette(mode)
    rows = pva.get("models", [])
    names = [_PVA_LABEL.get(r["model"], r["model"]) for r in rows]
    fig = go.Figure()
    fig.add_bar(x=names, y=[r["pr_auc_pooled"] for r in rows], name="pooled (all failures)",
                marker_color=pal["text_soft"])
    fig.add_bar(x=names, y=[r["pr_auc_addressable"] for r in rows],
                name="addressable (invisible removed)", marker_color=pal["accent"])
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="out-of-time PR-AUC", range=[0, 0.55])
    fig.update_xaxes(tickangle=-20)
    return _base(fig, pal, title="Pooled vs addressable PR-AUC, every model family")


def sequence_vs_gbm_fig(seq: dict, mode: str | None = None) -> go.Figure:
    """GRU challenger vs served GBM out-of-time PR-AUC, with the GBM bootstrap CI band so
    the 'not separable' claim is visible (the GRU bar sits inside the band)."""
    pal = get_palette(mode)
    gru = seq.get("oot_pr_auc_gru", 0.0)
    gbm = seq.get("oot_pr_auc_gbm_served", 0.0)
    ci = seq.get("gbm_pr_auc_ci") or [gbm, gbm]
    fig = go.Figure()
    fig.add_bar(x=["Served GBM", "GRU challenger"], y=[gbm, gru],
                marker_color=[pal["accent"], pal["text_soft"]],
                text=[f"{gbm:.3f}", f"{gru:.3f}"], textposition="outside")
    fig.add_hrect(y0=ci[0], y1=ci[1], fillcolor=pal["accent"], opacity=0.10, line_width=0,
                  annotation_text="GBM bootstrap CI", annotation_position="top left",
                  annotation_font=dict(size=9, color=pal["text_soft"]))
    fig.update_yaxes(title="out-of-time PR-AUC", range=[0, max(0.5, ci[1] * 1.15)])
    return _base(fig, pal, height=300, legend=False,
                 title="GRU sequence challenger vs served GBM (not separable)")


_MODE_LABEL = {
    "credit_visible": "credit-visible (model scope)",
    "rate_liquidity_visible": "rate/liquidity-visible",
    "invisible": "invisible (no signal)",
}


def failure_mix_by_year_fig(decomp: dict, mode: str | None = None) -> go.Figure:
    """Stacked failure-type mix per FILING year (a positive is a filing that fails within
    the next 4 quarters, so failures land later). Makes the two collapse mechanisms
    visible: the 2022 filing cohort is rate/liquidity-dominated (the 2023 wave, wrong cohort
    for a credit model), the 2024 filing cohort is invisible/fraud-dominated."""
    pal = get_palette(mode)
    by = decomp.get("by_filing_year", decomp.get("by_year_type", {}))
    years = sorted(by.keys())
    colors = {"credit_visible": pal["accent"], "rate_liquidity_visible": pal["teal"],
              "invisible": pal["rose"]}
    fig = go.Figure()
    for key in ("credit_visible", "rate_liquidity_visible", "invisible"):
        fig.add_bar(x=years, y=[by.get(y, {}).get(key, 0) for y in years],
                    name=_MODE_LABEL[key], marker_color=colors[key])
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="failure bank-quarters")
    fig.update_xaxes(title="filing year (failure occurs within the next 4 quarters)")
    return _base(fig, pal, title="Failure-type mix by filing-year cohort")


def addressable_pr_fig(decomp: dict, mode: str | None = None) -> go.Figure:
    """Full vs addressable (invisible failures removed) out-of-time PR-AUC, with 95%
    bootstrap CI whiskers so the bars are not read as bare point estimates."""
    pal = get_palette(mode)
    full = decomp.get("pr_auc_full", 0.0)
    addr = decomp.get("pr_auc_addressable", 0.0)
    npos = decomp.get("n_oot_positives", 0)
    addr_n = decomp.get("addressable_positives", 0)
    fci = decomp.get("pr_auc_full_ci"); aci = decomp.get("pr_auc_addressable_ci")
    fig = go.Figure()
    err = None
    if fci and aci:
        err = dict(type="data", symmetric=False,
                   array=[fci[1] - full, aci[1] - addr],
                   arrayminus=[full - fci[0], addr - aci[0]],
                   color=pal["text_muted"], thickness=1.4, width=6)
    fig.add_bar(x=[f"Full OOT ({npos})", f"Addressable ({addr_n})"], y=[full, addr],
                marker_color=[pal["text_soft"], pal["accent"]],
                error_y=err,
                text=[f"{full:.3f}", f"{addr:.3f}"], textposition="outside")
    top = max([0.5, addr * 1.25] + ([aci[1] * 1.1] if aci else []))
    fig.update_yaxes(title="PR-AUC (95% CI)", range=[0, top])
    return _base(fig, pal, height=300, legend=False,
                 title="PR-AUC: full vs structurally-addressable failures (with 95% CI)")


# ---- Robustness & validation cross-checks (artifact loaders + figures) ----

@lru_cache(maxsize=1)
def load_calibration_bakeoff() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "calibration_bakeoff.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_cblr_robustness() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "cblr_robustness.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_b1_compare() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "b1_compare.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_competing_risks() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "competing_risks.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_fine_gray() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "fine_gray.json"
    return json.loads(p.read_text()) if p.exists() else None


_CBLR_LABEL = {
    "baseline": "Native-null (served)",
    "cblr_indicator": "Explicit CBLR flag",
    "drop_rwa_post2020": "Drop feature (prior work)",
}


def cblr_variants_fig(cblr: dict, mode: str | None = None) -> go.Figure:
    """Addressable PR-AUC under three treatments of the 2020Q1 capital-ratio reporting
    break. The two legitimate handlings tie; naively dropping the feature craters it,
    so the break is handled correctly and the measurement is robust to the choice."""
    pal = get_palette(mode)
    rows = cblr.get("variants", [])
    names = [_CBLR_LABEL.get(r["variant"], r["variant"]) for r in rows]
    vals = [r.get("pr_auc_addressable_threshold", 0.0) for r in rows]
    cis = [r.get("pr_auc_addressable_threshold_ci") for r in rows]
    colors = [pal["accent"] if r["variant"] != "drop_rwa_post2020" else pal["rose"] for r in rows]
    err = None
    if all(cis):
        err = dict(type="data", symmetric=False,
                   array=[c[1] - v for c, v in zip(cis, vals)],
                   arrayminus=[v - c[0] for c, v in zip(cis, vals)],
                   color=pal["text_muted"], thickness=1.4, width=6)
    fig = go.Figure()
    fig.add_bar(x=names, y=vals, marker_color=colors, error_y=err,
                text=[f"{v:.3f}" for v in vals], textposition="outside")
    fig.update_yaxes(title="addressable PR-AUC (95% CI)", range=[0, 0.45])
    fig.update_xaxes(tickangle=-15)
    return _base(fig, pal, height=320, legend=False,
                 title="2020Q1 CBLR break: robust to handling, harmed only by dropping the feature")


@lru_cache(maxsize=1)
def load_panel_facts() -> dict | None:
    """Single source of truth for panel counts / quarter range / OOT facts (regenerated by
    ml/scripts/export_panel_facts.py) so the UI never hardcodes these drift-prone numbers."""
    p = _PROJECT_ROOT / "ml" / "artifacts" / "panel_facts.json"
    return json.loads(p.read_text()) if p.exists() else None


@lru_cache(maxsize=1)
def load_maxout_experiment() -> dict | None:
    p = _PROJECT_ROOT / "ml" / "artifacts" / "maxout_experiment.json"
    return json.loads(p.read_text()) if p.exists() else None


_MAXOUT_LABEL = {
    "baseline_light": "Light baseline",
    "heavy_tune": "Heavy tuning",
    "bagged": "Bagged (served)",
    "blend_avg": "Blend (avg)",
    "stack_logit": "Stacked logit",
}
_MAXOUT_ORDER = ["baseline_light", "heavy_tune", "bagged", "blend_avg", "stack_logit"]


def maxout_ladder_fig(mx: dict, mode: str | None = None) -> go.Figure:
    """The 'did maxing out help?' ladder: progressively heavier modelling (light → heavy tune →
    bagged → blend → stack) on the same out-of-time holdout, with 95% CIs. The bagged config is
    the served one; the CIs overlap heavily, which is the data-ceiling finding (at 66 positives
    more modelling effort does not separate)."""
    pal = get_palette(mode)
    res = mx.get("results", {})
    keys = [k for k in _MAXOUT_ORDER if k in res]
    names = [_MAXOUT_LABEL.get(k, k) for k in keys]
    vals = [res[k].get("pr_auc", 0.0) for k in keys]
    cis = [res[k].get("ci") for k in keys]
    colors = [pal["accent"] if k == "bagged" else pal["text_soft"] for k in keys]
    err = None
    if all(cis):
        err = dict(type="data", symmetric=False,
                   array=[c[1] - v for c, v in zip(cis, vals)],
                   arrayminus=[v - c[0] for c, v in zip(cis, vals)],
                   color=pal["text_muted"], thickness=1.4, width=6)
    fig = go.Figure()
    fig.add_bar(x=names, y=vals, marker_color=colors, error_y=err,
                text=[f"{v:.3f}" for v in vals], textposition="outside")
    fig.update_yaxes(title="out-of-time PR-AUC (95% CI)", range=[0, 0.46])
    fig.update_xaxes(tickangle=-15)
    return _base(fig, pal, height=320, legend=False,
                 title="Maxing out the model: effort ladder (CIs overlap at 66 positives)")


def calibration_bakeoff_fig(cb: dict, mode: str | None = None) -> go.Figure:
    """Calibration error (ECE) across the methods that were bench-raced. Isotonic wins
    and is the one served; the alternatives are shown to prove the choice was earned."""
    pal = get_palette(mode)
    bake = cb.get("calibration_bakeoff", {})
    order = [k for k in ("isotonic", "platt", "venn_abers(sample)") if k in bake]
    names = [k.replace("(sample)", " (sample)").title() for k in order]
    vals = [bake[k].get("ece", 0.0) for k in order]
    winner = cb.get("winner", "isotonic")
    colors = [pal["accent"] if k == winner else pal["text_soft"] for k in order]
    fig = go.Figure()
    fig.add_bar(x=names, y=vals, marker_color=colors,
                text=[f"{v:.1e}" for v in vals], textposition="outside")
    fig.update_yaxes(title="expected calibration error (lower is better)")
    return _base(fig, pal, height=300, legend=False,
                 title=f"Calibration bake-off: {winner} wins")
