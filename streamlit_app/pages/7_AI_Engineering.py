# ruff: noqa: E402
"""AI Engineering surface, the ML pillar, mirroring the Data Engineering sections.

Every section shows the REAL artifact: charts baked from the trained model + panel
(ml/artifacts/viz_pack.json), the live feature contract, and the actual running
source code (pulled via inspect.getsource, so it can never drift from what runs).
"""

import inspect
import json
import sys
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
for sub in ("", "src", "ml"):
    p = str(PROJECT_ROOT / sub) if sub else str(PROJECT_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)

from streamlit_app.lib import ml_charts as mc
from streamlit_app.lib.page_shell import (
    AI_PAGE,
    get_ai_section,
    page_intro,
    status_ribbon,
    top_navigation,
)
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, metric_card, section_heading

ART = PROJECT_ROOT / "ml" / "artifacts"

st.set_page_config(
    page_title="FinLens | AI Engineering", layout="wide", initial_sidebar_state="collapsed"
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=True))
top_navigation("ai", AI_PAGE)
record_page_view("ai_engineering", AI_PAGE)

MODE = get_theme_mode()


def _metrics() -> dict | None:
    p = ART / "metrics_h4.json"
    return json.loads(p.read_text()) if p.exists() else None


def _code(obj) -> str | None:
    """Real source of a live function/class, so excerpts never drift from what runs."""
    try:
        return textwrap.dedent(inspect.getsource(obj))
    except Exception:
        return None


def _show_code(obj, label: str, expanded: bool = False) -> None:
    src = _code(obj)
    if src:
        with st.expander(label, expanded=expanded):
            st.code(src, language="python")


from finlens_ml.features import FEATURE_COLUMNS

N_FEATURES = len(FEATURE_COLUMNS)

m = _metrics()
viz = mc.load_viz_pack()
section = get_ai_section()

_AI_INTRO = {
    "pipeline": ("Bank-Distress Model: Pipeline",
                 "How the discrete-time hazard model is trained and scored on the FDIC "
                 "bank-quarter panel, end to end, with the real code at each step."),
    "notebook": ("Bank-Distress Model: Analysis Notebook",
                 "The actual Jupyter notebook I built this with, executed on the real "
                 "panel: EDA, the out-of-time evaluation, calibration, and SHAP."),
    "contracts": ("Bank-Distress Model: Feature Contracts",
                  "The model's input contract: every feature, its enforced monotone "
                  "direction, its measured importance, and how the features correlate."),
    "stack": ("Bank-Distress Model: ML Stack",
              "The open-source, $0 production stack behind training, calibration, "
              "serving, and monitoring."),
    "quality": ("Bank-Distress Model: Model Quality",
                "Out-of-time performance, calibration, score separation, and drift, "
                "drawn live from the held-out evaluation."),
    "decisions": ("Bank-Distress Model: Model Decisions",
                  "The key modeling choices and the governance posture behind them."),
    "administration": ("Bank-Distress Model: Administration",
                       "Registry, promotion, retraining, rollback, and the $0 guard."),
    "wiki": ("Bank-Distress Model: Wiki",
             "Quick reference for the modeling concepts used across this surface."),
}
_title, _copy = _AI_INTRO.get(section, _AI_INTRO["pipeline"])

status_ribbon("Machine Learning Engineering")
page_intro("AI Engineering", _title, _copy)


if section == "pipeline":
    section_heading("Training & scoring pipeline", "Discrete-time hazard model on the FDIC bank-quarter panel.")
    st.markdown(
        "- **Ingest** per-CERT FDIC Call Report financials (free API) into a DuckDB panel\n"
        f"- **Features** {N_FEATURES} CAMELS-aligned ratios, trends, and peer z-scores "
        "(point-in-time)\n"
        "- **Label** fails-within-4q with merger / end-of-data censoring (leakage-free)\n"
        "- **Split** rolling-origin out-of-time with a reporting-lag embargo\n"
        "- **Train** LightGBM (monotone, class-weighted), then calibrate the probabilities\n"
        "- **Serve** FastAPI (calibrated probability + SHAP), **monitor** drift with Evidently"
    )
    if m:
        fm = m.get("final_model", {})
        st.success(
            f"Served model: {fm.get('n_estimators')} trees ({fm.get('tree_count_source')}), "
            f"calibration={fm.get('calibration_method')}, trained on {fm.get('n_train'):,} rows."
        )
    section_heading("The real code behind each step", "Pulled live from the source, not retyped.")
    from finlens_ml import labels, splits, train
    _show_code(labels.attach_labels, "Leakage-safe labelling (labels.attach_labels)", expanded=True)
    _show_code(splits.final_holdout_split, "Out-of-time split with embargo (splits.final_holdout_split)")
    _show_code(train._fit_calibrated, "Model + probability calibration (train._fit_calibrated)")

elif section == "notebook":
    import streamlit.components.v1 as components

    nb_html = PROJECT_ROOT / "ml" / "notebooks" / "bank_distress_analysis.html"
    nb_src = PROJECT_ROOT / "ml" / "notebooks" / "bank_distress_analysis.py"
    section_heading(
        "Analysis notebook",
        "Executed on the real FDIC panel. Same protocol as the shipped metrics.",
    )
    if nb_html.exists():
        components.html(nb_html.read_text(encoding="utf-8"), height=900, scrolling=True)
        st.caption(
            "Rendered from the executed notebook "
            "(ml/notebooks/bank_distress_analysis.ipynb). Re-run with jupytext + nbconvert."
        )
        if nb_src.exists():
            with st.expander("Notebook source (jupytext)"):
                st.code(nb_src.read_text(encoding="utf-8"), language="python")
    else:
        st.info("Run ml/notebooks build (jupytext + nbconvert) to render the notebook.")

elif section == "contracts":
    from finlens_ml import features
    from finlens_ml.features import MONOTONE_CONSTRAINTS

    section_heading(
        f"Feature contract ({len(MONOTONE_CONSTRAINTS)} features)",
        "Each feature's economic monotone direction vs. distress risk is enforced in the model.",
    )
    if viz:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(mc.shap_importance_fig(viz, MODE), use_container_width=True)
        with c2:
            st.plotly_chart(mc.correlation_fig(viz, MODE), use_container_width=True)
        st.caption(
            "Importance is mean |SHAP| over a real sample of the panel; the heatmap is the "
            "Pearson correlation among the most important features."
        )
    sign = {1: "↑ raises risk", -1: "↓ lowers risk", 0: "unconstrained"}
    fc = pd.DataFrame(
        [{"feature": f, "monotone": sign[v]} for f, v in MONOTONE_CONSTRAINTS.items()]
    )
    st.dataframe(fc, hide_index=True, use_container_width=True, height=360)
    st.caption("Point-in-time: features lag the reporting cycle; labels are strictly forward-looking.")
    _show_code(features.add_level_features, "How the ratio features are built (features.add_level_features)")
    _show_code(features.add_peer_zscores, "Peer z-scores (features.add_peer_zscores)")

elif section == "stack":
    section_heading("ML stack", "2026 production-grade, all open-source, $0.")
    st.table(pd.DataFrame([
        {"layer": "Model", "tool": "LightGBM (gradient-boosted hazard, monotone)"},
        {"layer": "Calibration", "tool": "scikit-learn CalibratedClassifierCV + FrozenEstimator"},
        {"layer": "Explainability", "tool": "SHAP TreeExplainer"},
        {"layer": "Tracking/registry", "tool": "MLflow 3.x (aliases, sqlite/Postgres)"},
        {"layer": "Serialization", "tool": "skops (safe, allow-listed, no pickle)"},
        {"layer": "Serving", "tool": "FastAPI (lifespan, Pydantic v2)"},
        {"layer": "Monitoring", "tool": "Evidently 0.7.x (data + prediction drift)"},
        {"layer": "Store", "tool": "DuckDB point-in-time panel"},
    ]))

elif section == "quality":
    if not m or not viz:
        st.info("Train the model and run ml/scripts/export_viz_pack.py to populate this surface.")
    else:
        t = m["oot_test"]["calibrated_lgbm"]
        cal = m.get("oot_calibration", {})
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card("PR-AUC (OOT)", f"{t['pr_auc']:.3f}", "vs logit 0.109")
        with k2:
            metric_card("ROC-AUC (OOT)", f"{t['roc_auc']:.3f}", "rank quality")
        with k3:
            metric_card("Recall@200", f"{t['recall_at_k']:.0%}", "of failures caught")
        with k4:
            metric_card("Calibration ECE", f"{cal.get('ece', float('nan')):.1e}", "lower is better")
        st.caption(
            f"Out-of-time window: {m['eval_window_quarters']} quarters, "
            f"{viz['n_oot']:,} bank-quarters, {viz['n_oot_failures']} real failures "
            f"(base rate {viz['curves']['base_rate']:.3%}). Every chart below is computed "
            "from these held-out predictions."
        )
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(mc.pr_curve_fig(viz, MODE), use_container_width=True)
        with c2:
            st.plotly_chart(mc.roc_curve_fig(viz, MODE), use_container_width=True)
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(mc.calibration_fig(viz, MODE), use_container_width=True)
        with c4:
            st.plotly_chart(mc.score_dist_fig(viz, MODE), use_container_width=True)
        st.plotly_chart(mc.threshold_fig(viz, MODE), use_container_width=True)
        by_year = m.get("by_year_calibrated", {})
        if by_year:
            section_heading("By year", "PR-AUC holds up in the failure-containing cohorts.")
            rows = [
                {"year": y, "n": v["n"], "failures": v["n_positive"],
                 "pr_auc": None if isinstance(v["pr_auc"], str) or v["pr_auc"] != v["pr_auc"]
                 else round(v["pr_auc"], 4)}
                for y, v in by_year.items()
            ]
            st.plotly_chart(mc.by_year_fig(rows, MODE), use_container_width=True)
        if viz.get("drift_top_features"):
            section_heading("Drift monitoring (Evidently)", "Reference 2008-18 vs current 2019-26.")
            ds = viz.get("drift_summary", {})
            st.write(
                f"{ds.get('n_drifted_columns')}/{ds.get('n_features_analyzed')} features drifted "
                f"(share {ds.get('share_of_drifted_columns')}); prediction-drift score "
                f"{ds.get('prediction_drift_score')}."
            )
            dfig = mc.drift_fig(viz, MODE)
            if dfig:
                st.plotly_chart(dfig, use_container_width=True)

elif section == "decisions":
    section_heading("Key model decisions", "")
    mcard = PROJECT_ROOT / "docs" / "ml" / "MODEL_CARD.md"
    st.markdown(
        "- **Discrete-time hazard** on a bank-quarter panel (not a next-quarter logit)\n"
        "- **Monotone constraints** for regulator-defensible, perverse-free relationships\n"
        "- **Calibration** so served probabilities are real, not raw scores\n"
        "- **PR-AUC / recall@k** as the headline (accuracy is meaningless at <1% base rate)\n"
        "- **Aligned with SR 11-7 model-risk principles** (non-binding here); fairness "
        "scoped as cross-segment equity, no protected class for an institution-level model"
    )
    if mcard.exists():
        with st.expander("Full model card"):
            st.markdown(mcard.read_text(encoding="utf-8"))

elif section == "administration":
    from finlens_ml import registry

    section_heading("Model administration", "Registry, promotion, retraining, rollback.")
    st.markdown(
        "- **Registry**: MLflow champion/challenger via aliases (not deprecated stages)\n"
        "- **Promotion**: manual to champion after shadow + a CI metric gate\n"
        "- **Retrain**: scheduled quarterly + drift-triggered\n"
        "- **Rollback**: repoint the champion alias to the prior version (instant, auditable)\n"
        "- **$0 guard**: CI fails if ML code imports any billable service"
    )
    _show_code(registry.set_champion, "Champion promotion via alias (registry.set_champion)")
    _show_code(registry.promote_latest_to_champion, "Promote latest (registry.promote_latest_to_champion)")

elif section == "wiki":
    section_heading("AI concepts", "Quick reference for the modeling choices.")
    for term, body in {
        "Discrete-time hazard": "Predict P(fail within H quarters) on a bank-quarter panel; "
        "uses time-varying covariates and reduces to binary classification a GBM can fit.",
        "Calibration": "Map raw model scores to true probabilities (isotonic/Platt) on a "
        "held-out set, so a 5% score really means ~5% failure rate.",
        "PR-AUC vs ROC-AUC": "At <1% base rate, ROC looks great while the model is useless; "
        "PR-AUC (precision-recall) exposes real rare-event performance.",
        "SHAP": "Per-prediction attribution of each feature's contribution; used here for "
        "validator-facing transparency (not consumer adverse-action).",
        "Drift": "Distribution shift in inputs (data drift) or scores (prediction drift); "
        "the earliest warning since true failure labels arrive late.",
    }.items():
        with st.expander(term):
            st.write(body)


from streamlit_app.lib.page_shell import page_footer  # noqa: E402

page_footer()
