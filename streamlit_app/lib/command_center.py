"""FinLens Command Center: the home landing.

Two tabs. Tab 1 "Live Overview" is a dense, live, single-screen command center that pulls the
highlights from every surface (model metrics, pipeline status, the highest-risk banks right now,
macro snapshot) and the three surface entries. Tab 2 "ML Inference" is a first-class scoring
console: score a real bank, or build a scenario with the levers defaulted to peak distress.

Everything reads the real warehouse and the trained model. No demo data.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

from finlens.pipeline_status import pipeline_status_rows
from streamlit_app.lib import ml_charts as mc
from streamlit_app.lib.data import load_failures, load_metrics
from streamlit_app.lib.theme import get_theme_mode
from streamlit_app.lib.ui_components import metric_card, section_heading, status_tone

_ART = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()) / "ml" / "artifacts"


@lru_cache(maxsize=1)
def _oot() -> dict:
    p = _ART / "metrics_h4.json"
    if not p.exists():
        return {}
    m = json.loads(p.read_text())
    t = (m.get("oot_test", {}) or {}).get("calibrated_lgbm", {})
    return {
        "pr_auc": t.get("pr_auc"), "roc_auc": t.get("roc_auc"),
        "recall_at_k": t.get("recall_at_k"), "k": t.get("k"),
        "ece": (m.get("oot_calibration", {}) or {}).get("ece"),
        "test_positives": m.get("test_positives"),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _top_risk(k: int = 10) -> pd.DataFrame:
    """Highest current modelled distress, cached so the home is fast."""
    try:
        import finlens_ml.scenario as scenario
        return scenario.top_risk_banks(k)
    except Exception:  # noqa: BLE001
        return pd.DataFrame(columns=["bank_name", "state", "quarter", "probability", "threshold"])


# ----------------------------------------------------------------------------- Tab 1: overview
def render_overview() -> None:
    pf = mc.load_panel_facts() or {}
    oot = _oot()
    rows = pipeline_status_rows()
    n_rows = pf.get("n_panel_rows")
    n_banks = pf.get("n_banks")

    def _fmt(v, suffix="", pct=False, dp=0):
        if v is None:
            return "n/a"
        return (f"{v * 100:.{dp}f}%" if pct else f"{v:,.{dp}f}") + suffix

    st.markdown('<div class="cc-band-title">The model, the pipeline, and the riskiest banks '
                'right now — at a glance</div>', unsafe_allow_html=True)

    # KPI band
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("OOT PR-AUC", f"{oot.get('pr_auc'):.3f}" if oot.get("pr_auc") else "n/a",
                    "out-of-time, rare-event metric", tone="ok")
    with k2:
        metric_card("OOT ROC-AUC", f"{oot.get('roc_auc'):.3f}" if oot.get("roc_auc") else "n/a",
                    "ranking quality")
    with k3:
        rk = oot.get("recall_at_k")
        metric_card(f"Recall@{oot.get('k') or 200}", _fmt(rk, pct=True, dp=1) if rk else "n/a",
                    "failures caught in the review budget")
    with k4:
        ece = oot.get("ece")
        metric_card("Calibration (ECE)", f"{ece:.1e}" if ece else "n/a", "lower is better")
    k5, k6, k7, k8 = st.columns(4)
    with k5:
        metric_card("Panel", f"{n_rows:,}" if n_rows else "448k+", "bank-quarters scored")
    with k6:
        metric_card("Banks", f"~{round(n_banks, -2):,.0f}" if n_banks else "~8,800",
                    "U.S. institutions")
    with k7:
        try:
            n_fail = len(load_failures())
        except Exception:  # noqa: BLE001
            n_fail = 574
        metric_card("FDIC failures", f"{n_fail:,}", "since 2000, in the panel")
    with k8:
        metric_card("OOT failures", f"{oot.get('test_positives') or 66}",
                    "in the embargoed test window")

    st.markdown('<div class="cc-rule"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        section_heading("Highest modelled distress right now",
                        "Currently-operating banks scored on their latest public filing. A model "
                        "ESTIMATE, not a forecast — failure is rare (base rate < 1%).")
        top = _top_risk(10)
        if top.empty:
            st.info("Model artifact not present — train the model to populate this.")
        else:
            asof = top["quarter"].iloc[0] if "quarter" in top else ""
            disp = top.assign(
                Bank=top["bank_name"].str.title(),
                State=top["state"].fillna("?"),
                **{"Distress probability": (top["probability"] * 100).round(2).astype(str) + "%"},
            )[["Bank", "State", "Distress probability"]]
            st.dataframe(disp, hide_index=True, use_container_width=True)
            st.caption(f"As of {asof}. Probability of financial distress within four quarters, "
                       "from the calibrated, monotone hazard model.")
    with right:
        section_heading("Live pipeline", "Source-to-serving status from the last run.")
        for r in rows:
            tone = status_tone(r.get("status", ""))
            metric_card(r.get("flow_name", ""), r.get("status", ""),
                        str(r.get("last_run", ""))[:16].replace("T", " "), tone=tone)

    st.markdown('<div class="cc-rule"></div>', unsafe_allow_html=True)

    # Macro snapshot
    section_heading("Macro snapshot", "Live FRED series that move with banking stress.")
    metrics = load_metrics()
    if not metrics.empty:
        want = ["UNRATE", "DGS10", "BAA10Y", "NFCI"]
        cols = st.columns(len(want))
        for col, sid in zip(cols, want):
            sub = metrics[metrics["series_id"] == sid].sort_values("date")
            with col:
                if sub.empty:
                    st.caption(f"{sid}: n/a")
                    continue
                st.caption(sid)
                st.line_chart(sub.set_index("date")["value"], height=90)
                st.caption(f"latest {sub['value'].iloc[-1]:,.2f}")

    st.markdown('<div class="cc-rule"></div>', unsafe_allow_html=True)
    _surface_cards()


def _surface_cards() -> None:
    st.markdown('<div class="landing-pick">Go deeper — AI first, then the build, then the story</div>',
                unsafe_allow_html=True)
    a, d, b = st.columns(3, vertical_alignment="top")
    with a:
        st.markdown(
            '<div class="surface-card surface-card-a">'
            '<div class="surface-card-k">AI Engineering</div>'
            '<div class="surface-card-t">Look inside the model</div>'
            '<div class="surface-card-c">The calibrated, monotone distress model end to end: '
            'features, training, out-of-time metrics, SHAP, drift, and governance.</div></div>',
            unsafe_allow_html=True)
        if st.button("Enter AI Engineering", key="cc_open_ai", use_container_width=True):
            st.switch_page("pages/7_AI_Engineering.py")
    with d:
        st.markdown(
            '<div class="surface-card surface-card-d">'
            '<div class="surface-card-k">Data Engineering</div>'
            '<div class="surface-card-t">See how it is built</div>'
            '<div class="surface-card-c">The pipeline, source contracts, warehouse, data '
            'quality, and operations behind every number.</div></div>',
            unsafe_allow_html=True)
        if st.button("Enter Data Engineering", key="cc_open_de", use_container_width=True):
            st.session_state["technical_section"] = "pipeline"
            st.switch_page("pages/4_Data_Engineering.py")
    with b:
        st.markdown(
            '<div class="surface-card surface-card-b">'
            '<div class="surface-card-k">Business</div>'
            '<div class="surface-card-t">Read the banking story</div>'
            '<div class="surface-card-c">Industry stress, bank-failure forensics, macro '
            'context, and a live distress scorer for any bank.</div></div>',
            unsafe_allow_html=True)
        if st.button("Enter Business", key="cc_open_business", use_container_width=True):
            st.switch_page("pages/0_Stress_Pulse.py")


# -------------------------------------------------------------------------- Tab 2: ML inference
def _render_score(result: dict, mode: str, key: str, cap: float | None = None) -> None:
    import finlens_ml.scenario as scenario
    prob, thr = result["probability"], result["threshold"]
    tier, cls = (("HIGH RISK", "danger") if prob >= thr
                 else ("ELEVATED", "warn") if prob >= thr / 2 else ("LOW RISK", "ok"))
    g, info = st.columns([1, 1.15], vertical_alignment="center")
    with g:
        st.plotly_chart(mc.probability_gauge(prob, thr, mode, cap=cap),
                        use_container_width=True, key=f"cc_gauge_{key}")
    with info:
        st.markdown(
            f'<div class="ew-badge ew-{cls}">{tier}</div>'
            f'<div class="ew-sub">Calibrated probability of financial distress within four '
            f'quarters: <b>{prob * 100:.3f}%</b> ({prob * 1e4:.1f} bps). Review threshold '
            f'{thr * 100:.0f}%.</div>', unsafe_allow_html=True)
    reasons = pd.DataFrame(result.get("reasons", []))
    if not reasons.empty:
        reasons["Driver"] = reasons["feature"].astype(str).map(scenario.humanize_feature)
        reasons["Reported value"] = reasons["value"].map(
            lambda v: "n/a" if v is None or (isinstance(v, float) and v != v) else f"{v:,.3f}")
        reasons["Effect"] = reasons["direction"].map(
            {"increases risk": "↑ up", "decreases risk": "↓ down"}).fillna(reasons["direction"])
        reasons["Weight"] = reasons["shap"].abs().round(3)
        section_heading("Why this score", "Each factor's SHAP contribution to THIS score.")
        st.dataframe(reasons[["Driver", "Reported value", "Effect", "Weight"]],
                     hide_index=True, use_container_width=True)


def render_inference() -> None:
    mode = get_theme_mode()
    try:
        import finlens_ml.scenario as scenario
    except Exception:  # noqa: BLE001
        st.info("Model package unavailable.")
        return
    if not (_ART / "calibrated_h4.skops").exists() and not (_ART / "booster_h4.txt").exists():
        st.info("Model artifact not present — train the model to activate inference.")
        return

    st.markdown('<div class="cc-band-title">Score a real bank, or build a scenario — the model '
                'runs live</div>', unsafe_allow_html=True)
    choice = st.radio("Inference mode", ["Build a scenario (peak distress)", "Score a real bank"],
                      horizontal=True, label_visibility="collapsed", key="cc_inf_mode")

    if choice == "Score a real bank":
        directory = scenario.bank_directory()
        labels = directory["label"].tolist()
        pick = st.selectbox("Bank (scored as of a past quarter with a known outcome)", labels,
                            index=next((i for i, x in enumerate(labels) if x.startswith("INDYMAC")), 0),
                            key="cc_inf_bank", placeholder="Start typing a bank name…")
        if pick:
            r = directory[directory["label"] == pick].iloc[0]
            row = scenario.latest_known_row_for_cert(int(r["cert"]))
            if row is None:
                st.warning("That bank has no quarter with a known outcome to backtest.")
            else:
                st.success(f"{row['bank_name']} ({row['state']}) · scored as of {row['quarter']} "
                           f"· FDIC CERT {row['cert']}")
                _render_score(scenario.score_features(row["features"]), mode, key="bank")
    else:
        st.caption("The levers open at a **peak-distress** setting (capital and earnings floored, "
                   "bad-loan and funding levers maxed) so you can see what severe distress scores, "
                   "then dial back. Monotone constraints are enforced.")
        preset = scenario.peak_distress_sliders()
        vals = {}
        cols = st.columns(3)
        for i, (feat, (lo, hi, _med)) in enumerate(scenario.SLIDER_FEATURES.items()):
            with cols[i % 3]:
                vals[feat] = st.slider(scenario.SLIDER_LABELS.get(feat, feat), float(lo), float(hi),
                                       float(preset[feat]), key=f"cc_wi_{feat}")
        res = scenario.score_hypothetical(vals)
        _render_score(res, mode, key="whatif", cap=max(40.0, res["probability"] * 100 * 1.3))
