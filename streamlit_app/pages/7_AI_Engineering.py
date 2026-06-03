# ruff: noqa: E402
"""AI Engineering surface — the ML pillar, mirroring the Data Engineering sections.

Every section exposes the REAL underlying artifact (max visibility, nothing hidden):
metrics from the actual training run, drift from the real Evidently report, the live
feature contract + monotone signs, the registry/serving state, and the governance
docs. In-page st.tabs => no full reload per section. $0, no fabrication.
"""

import json
import sys
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

from streamlit_app.lib.page_shell import AI_PAGE, page_intro, status_ribbon, top_navigation
from streamlit_app.lib.telemetry import record_page_view
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_theme_mode
from streamlit_app.lib.ui_components import inject_styles, section_heading

ART = PROJECT_ROOT / "ml" / "artifacts"

st.set_page_config(
    page_title="FinLens | AI Engineering", layout="wide", initial_sidebar_state="collapsed"
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=False))
top_navigation("ai", AI_PAGE)
record_page_view("ai_engineering", AI_PAGE)


def _metrics() -> dict | None:
    p = ART / "metrics_h4.json"
    return json.loads(p.read_text()) if p.exists() else None


def _drift() -> dict | None:
    p = ART / "drift_report.json"
    return json.loads(p.read_text()) if p.exists() else None


status_ribbon("Machine Learning Engineering surface — every layer visible")
page_intro(
    "AI Engineering",
    "Bank-Distress Model — Under The Hood",
    "The ML pillar, structured to mirror the Data Engineering surface: pipeline, "
    "feature contracts, stack, model quality, decisions, administration, and wiki. "
    "All figures are computed from the real trained model and data.",
)

m = _metrics()
tabs = st.tabs(
    ["AI Pipeline", "Feature Contracts", "AI Stack", "Model Quality",
     "Model Decisions", "Administration", "AI Wiki"]
)

with tabs[0]:  # AI Pipeline (mirror of Live Pipeline)
    section_heading("Training & scoring pipeline", "Discrete-time hazard model on the FDIC bank-quarter panel.")
    st.markdown(
        "- **Ingest** per-CERT FDIC Call Report financials (free API) → DuckDB panel\n"
        "- **Features** 31 CAMELS-aligned ratios + trends + peer z-scores (point-in-time)\n"
        "- **Label** fails-within-4q with merger/end-of-data censoring (leakage-free)\n"
        "- **Train** LightGBM (monotone + class-weighted) → calibrate → MLflow registry\n"
        "- **Serve** FastAPI (lifespan, calibrated prob + SHAP) · **Monitor** Evidently drift"
    )
    if m:
        fm = m.get("final_model", {})
        st.success(
            f"Served model: {fm.get('n_estimators')} trees ({fm.get('tree_count_source')}), "
            f"calibration={fm.get('calibration_method')}, trained on {fm.get('n_train'):,} rows."
        )

with tabs[1]:  # Feature Contracts (mirror of Source Contracts)
    from finlens_ml.features import MONOTONE_CONSTRAINTS

    section_heading("Feature contract (31 features)", "Each feature's economic monotone direction vs. distress risk is enforced in the model.")
    sign = {1: "↑ raises risk", -1: "↓ lowers risk", 0: "unconstrained"}
    fc = pd.DataFrame(
        [{"feature": f, "monotone": sign[v]} for f, v in MONOTONE_CONSTRAINTS.items()]
    )
    st.dataframe(fc, hide_index=True, use_container_width=True, height=420)
    st.caption("Point-in-time: features lag the reporting cycle; labels are strictly forward-looking.")

with tabs[2]:  # AI Stack (mirror of Engineering Stack)
    section_heading("ML stack", "2026 production-grade, all open-source, $0.")
    st.table(pd.DataFrame([
        {"layer": "Model", "tool": "LightGBM (gradient-boosted hazard, monotone)"},
        {"layer": "Calibration", "tool": "scikit-learn CalibratedClassifierCV + FrozenEstimator"},
        {"layer": "Explainability", "tool": "SHAP TreeExplainer"},
        {"layer": "Tracking/registry", "tool": "MLflow 3.x (aliases, sqlite/Postgres)"},
        {"layer": "Serialization", "tool": "skops (safe, allow-listed — no pickle)"},
        {"layer": "Serving", "tool": "FastAPI (lifespan, Pydantic v2)"},
        {"layer": "Monitoring", "tool": "Evidently 0.7.x (data + prediction drift)"},
        {"layer": "Store", "tool": "DuckDB point-in-time panel"},
    ]))

with tabs[3]:  # Model Quality (mirror of Data Quality)
    section_heading("Out-of-time performance", "Real metrics — PR-AUC is the rare-event headline; ROC is comparability-only.")
    if not m:
        st.info("Train the model to populate metrics.")
    else:
        t = m["oot_test"]
        st.dataframe(pd.DataFrame([
            {"model": "Calibrated LGBM", "PR-AUC": round(t["calibrated_lgbm"]["pr_auc"], 4),
             "ROC-AUC": round(t["calibrated_lgbm"]["roc_auc"], 4),
             "recall@200": round(t["calibrated_lgbm"]["recall_at_k"], 3),
             "Brier": round(t["calibrated_lgbm"]["brier"], 5)},
            {"model": "Logit benchmark", "PR-AUC": round(t["logit_benchmark"]["pr_auc"], 4),
             "ROC-AUC": round(t["logit_benchmark"]["roc_auc"], 4),
             "recall@200": round(t["logit_benchmark"]["recall_at_k"], 3),
             "Brier": round(t["logit_benchmark"]["brier"], 5)},
        ]), hide_index=True, use_container_width=True)
        st.caption(
            f"OOT window: {m['eval_window_quarters']} quarters, {m['n_test']:,} bank-quarters, "
            f"{m['test_positives']} real failures. The LGBM beats the regulatory logit "
            f"benchmark on PR-AUC (the metric that matters at a <1% base rate)."
        )
        by_year = m.get("by_year_calibrated", {})
        if by_year:
            section_heading("By year", "Crisis vs calm cohorts — PR-AUC is honestly low when failures are absent.")
            st.dataframe(pd.DataFrame([
                {"year": y, "n": v["n"], "failures": v["n_positive"],
                 "PR-AUC": v["pr_auc"] if isinstance(v["pr_auc"], str) else round(v["pr_auc"], 4),
                 "ROC-AUC": v["roc_auc"] if isinstance(v["roc_auc"], str) else round(v["roc_auc"], 4)}
                for y, v in by_year.items()
            ]), hide_index=True, use_container_width=True)
        cal = m.get("oot_calibration", {})
        if cal:
            st.metric("Calibration ECE", f"{cal.get('ece', float('nan')):.2e}")
            st.caption(
                f"Top-decile predicted {cal.get('top_decile_pred', float('nan')):.4f} vs "
                f"observed {cal.get('top_decile_obs', float('nan')):.4f}."
            )
        d = _drift()
        if d:
            section_heading("Drift monitoring (Evidently)", "Reference 2008-18 vs current 2019-26.")
            st.write(
                f"{d.get('n_drifted_columns')}/{d.get('n_features_analyzed')} features drifted "
                f"(share {d.get('share_of_drifted_columns')}). Prediction-drift score "
                f"{d.get('prediction_drift_score')}."
            )

with tabs[4]:  # Model Decisions (mirror of Architecture Decisions)
    section_heading("Key model decisions", "")
    mc = PROJECT_ROOT / "docs" / "ml" / "MODEL_CARD.md"
    st.markdown(
        "- **Discrete-time hazard** on a bank-quarter panel (not next-quarter logit)\n"
        "- **Monotone constraints** for regulator-defensible, perverse-free relationships\n"
        "- **Calibration** (isotonic) so served probabilities are real, not raw scores\n"
        "- **PR-AUC / recall@k** as headline (accuracy is meaningless at <1% base rate)\n"
        "- **SR 26-2 aligned** (non-binding); honest fairness = cross-segment equity, "
        "no protected class for an institution-level model"
    )
    if mc.exists():
        with st.expander("Full model card"):
            st.markdown(mc.read_text(encoding="utf-8"))

with tabs[5]:  # Administration (mirror of Administration)
    section_heading("Model administration", "Registry, promotion, retraining, rollback.")
    st.markdown(
        "- **Registry**: MLflow champion/challenger via aliases (not deprecated stages)\n"
        "- **Promotion**: manual to champion after shadow + metric gate (CI)\n"
        "- **Retrain**: scheduled quarterly + drift-triggered\n"
        "- **Rollback**: repoint the champion alias to the prior version (instant, auditable)\n"
        "- **$0 guard**: CI fails if ML code imports any billable service"
    )

with tabs[6]:  # AI Wiki (mirror of Wiki) — in-page, no reload
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
