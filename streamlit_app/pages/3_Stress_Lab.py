# ruff: noqa: E402

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finlens.stress_lab import FEATURE_COLUMNS, run_demo_stress_lab, score_manual_scenario
from streamlit_app.lib.page_shell import (
    BUSINESS_PAGE,
    STRESS_LAB_ENABLED,
    page_intro,
    status_ribbon,
    top_navigation,
)
from streamlit_app.lib.theme import app_css, ensure_theme_state, get_palette, get_theme_mode
from streamlit_app.lib.ui_components import (
    inject_styles,
    metric_card,
    section_heading,
)


@st.cache_data(show_spinner=False)
def get_stress_lab_result():
    return run_demo_stress_lab()


def confusion_heatmap(confusion: list[list[int]]):
    palette = get_palette()
    figure = go.Figure(
        data=go.Heatmap(
            z=confusion,
            x=["Predicted healthy", "Predicted failure-like"],
            y=["Actually healthy", "Actually failed"],
            colorscale=[
                [0.0, palette["sand"]],
                [0.35, palette["teal_soft"]],
                [1.0, palette["accent"]],
            ],
            text=confusion,
            texttemplate="%{text}",
            hoverinfo="skip",
        )
    )
    figure.update_layout(
        title="Held-out Confusion Matrix",
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
    )
    return figure


def importance_chart(frame: pd.DataFrame):
    palette = get_palette()
    top_features = frame.head(6).sort_values("importance", ascending=True)
    figure = px.bar(
        top_features,
        x="importance",
        y="feature",
        orientation="h",
        color_discrete_sequence=[palette["link"]],
    )
    figure.update_layout(
        title="Strongest Model Signals",
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        xaxis_title="Relative importance",
        yaxis_title="",
        showlegend=False,
    )
    return figure


st.set_page_config(
    page_title="FinLens | Stress Lab",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ensure_theme_state()
inject_styles(app_css(get_theme_mode(), sidebar_open=st.session_state.get("sidebar_open", False)))
top_navigation("stress", BUSINESS_PAGE)

if not STRESS_LAB_ENABLED:
    status_ribbon("Dormant feature")
    page_intro(
        "Dormant",
        "Stress Lab",
        "This modeling surface remains in the repo for later reuse, but it is intentionally "
        "disabled in the current low-risk FinLens scope.",
    )
    st.info(
        "Stress Lab is dormant. Re-enable `STRESS_LAB_ENABLED` in "
        "`streamlit_app/lib/page_shell.py` when you want to bring it back."
    )
    st.stop()

status_ribbon("Retrospective model lab")
page_intro(
    "Model Lab",
    "Stress Lab",
    "A retrospective classifier that learns failure-like patterns from demo bank records. "
    "It is intentionally framed as an educational lab, not a live solvency prediction tool.",
)

result = get_stress_lab_result()
best_model = result.model_results[0]
top_feature = result.feature_importance.iloc[0]["feature"].replace("_", " ").title()
heldout_count = len(result.heldout_predictions)

leaderboard = pd.DataFrame([item.__dict__ for item in result.model_results]).rename(
    columns={
        "model_name": "Model",
        "cv_roc_auc": "CV ROC-AUC",
        "test_roc_auc": "Held-out ROC-AUC",
        "accuracy": "Accuracy",
        "precision": "Precision",
        "recall": "Recall",
    }
)

heldout = result.heldout_predictions.copy()
heldout["scenario_label"] = heldout.apply(
    lambda row: f"{row['bank_name']} ({row['snapshot_year']}, {row['state']})",
    axis=1,
)
replay_tab, diagnostics_tab = st.tabs(["Analyst Replay", "Model Diagnostics"])

with replay_tab:
    section_heading(
        "Analyst Replay",
        "Select a held-out bank the model never saw during training, then override the inputs to "
        "see how the stress-pattern score changes.",
    )
    selection_col, fact_col = st.columns([1.25, 0.75], vertical_alignment="top")
    with selection_col:
        selected_label = st.selectbox(
            "Held-out bank",
            heldout["scenario_label"].tolist(),
        )
        selected_row = heldout.loc[heldout["scenario_label"] == selected_label].iloc[0]

        input_left, input_right = st.columns(2)
        with input_left:
            total_assets = st.number_input(
                "Total assets (billions)",
                min_value=0.1,
                value=float(selected_row["total_assets_billion"]),
                step=1.0,
            )
            tier1 = st.number_input(
                "Tier 1 capital ratio",
                min_value=0.0,
                max_value=25.0,
                value=float(selected_row["tier1_capital_ratio"]),
                step=0.1,
            )
            roa = st.number_input(
                "Return on assets",
                min_value=-5.0,
                max_value=5.0,
                value=float(selected_row["return_on_assets"]),
                step=0.1,
            )
            deposit_growth = st.number_input(
                "Deposit growth %",
                min_value=-30.0,
                max_value=20.0,
                value=float(selected_row["deposit_growth_pct"]),
                step=0.5,
            )
            uninsured_share = st.number_input(
                "Uninsured deposit share %",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_row["uninsured_deposit_share"]),
                step=1.0,
            )
        with input_right:
            securities_assets = st.number_input(
                "Securities / assets %",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_row["securities_to_assets_pct"]),
                step=1.0,
            )
            cre_share = st.number_input(
                "CRE loan share %",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_row["cre_loan_share_pct"]),
                step=1.0,
            )
            nonperforming = st.number_input(
                "Nonperforming assets %",
                min_value=0.0,
                max_value=20.0,
                value=float(selected_row["nonperforming_assets_pct"]),
                step=0.1,
            )
            efficiency = st.number_input(
                "Efficiency ratio",
                min_value=20.0,
                max_value=120.0,
                value=float(selected_row["efficiency_ratio"]),
                step=1.0,
            )
            fed_funds = st.number_input(
                "Fed funds rate",
                min_value=0.0,
                max_value=10.0,
                value=float(selected_row["fed_funds_rate"]),
                step=0.1,
            )

        manual_features = {
            FEATURE_COLUMNS[0]: total_assets,
            FEATURE_COLUMNS[1]: tier1,
            FEATURE_COLUMNS[2]: roa,
            FEATURE_COLUMNS[3]: deposit_growth,
            FEATURE_COLUMNS[4]: uninsured_share,
            FEATURE_COLUMNS[5]: securities_assets,
            FEATURE_COLUMNS[6]: cre_share,
            FEATURE_COLUMNS[7]: nonperforming,
            FEATURE_COLUMNS[8]: efficiency,
            FEATURE_COLUMNS[9]: fed_funds,
        }
        manual_score = score_manual_scenario(manual_features)
        st.metric("Failure-like pattern score", f"{manual_score:.0%}")

    with fact_col:
        st.markdown("##### Historical Fact Check")
        st.markdown(f"**Bank:** {selected_row['bank_name']}")
        st.markdown(f"**State:** {selected_row['state']}")
        st.markdown(f"**Snapshot year:** {int(selected_row['snapshot_year'])}")
        if int(selected_row["actual_failed"]) == 1:
            st.error(f"Historical outcome: this bank failed on {selected_row['failure_date']}.")
        else:
            st.success("Historical outcome: this demo record did not fail in the sample.")
        st.info(
            "This panel keeps the model grounded by comparing the scenario score against the "
            "known historical outcome."
        )

with diagnostics_tab:
    section_heading(
        "Model Diagnostics",
        "The lab compares classical models first. Deep learning stays out unless the feature set "
        "gets materially richer and the baseline models stop being competitive.",
    )
    metric1, metric2, metric3, metric4 = st.columns(4)
    with metric1:
        metric_card("Winning Model", best_model.model_name, "Selected by CV ROC-AUC")
    with metric2:
        metric_card("CV ROC-AUC", f"{best_model.cv_roc_auc:.2f}", "Cross-validated ranking score")
    with metric3:
        metric_card("Held-out Recall", f"{best_model.recall:.2f}", "Unseen sample sensitivity")
    with metric4:
        metric_card("Top Signal", top_feature, f"{heldout_count} held-out banks available")
    st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
    st.dataframe(leaderboard, width="stretch", hide_index=True)
    left, right = st.columns([1.1, 0.9])
    with left:
        st.plotly_chart(importance_chart(result.feature_importance), width="stretch")
    with right:
        st.plotly_chart(confusion_heatmap(result.confusion), width="stretch")

section_heading(
    "Why this exists",
    "The point is to demonstrate a disciplined retrospective modeling workflow, not to pretend we "
    "can issue live bank-failure calls from a demo dashboard.",
)
st.warning(
    "By using this lab, you agree not to treat it as financial, regulatory, supervisory, or "
    "investment guidance and not to assign liability to the project author for model output. This "
    "enthusiast-built retrospective classifier can and will make mistakes. It does not decide "
    "the fate of any bank and must not be used for real-world judgments. For authoritative "
    "information, "
    "rely on official U.S. government sources such as the FDIC failed-bank list "
    "(https://www.fdic.gov/resources/resolutions/bank-failures/failed-bank-list/) and FRED "
    "(https://fred.stlouisfed.org/)."
)
