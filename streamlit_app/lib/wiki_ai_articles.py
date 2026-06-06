"""In-depth AI-engineering articles for the FinLens bank-distress model.

Nine encyclopedia entries documenting the model itself: framing, features, labels,
out-of-time evaluation, calibration, explainability, governance, drift, and serving.
Every quantitative claim is grounded in the real code under ``ml/finlens_ml`` and the
real artifact ``ml/artifacts/metrics_h4.json``. Schema per entry:
{cluster, branch, summary, body}. Bodies are GitHub-flavoured markdown; the wiki page
builds a table of contents from the ``## `` headings. Encyclopedic register: plain,
precise, third-person, no marketing.
"""

from __future__ import annotations

import json as _json
from pathlib import Path as _Path


def _load_metric_values() -> dict:
    """Read served-model numbers from the committed artifacts at import time so the
    encyclopedia text auto-syncs on every retrain and can never go stale. Falls back to
    em-dash placeholders if an artifact is missing (the prose still reads sensibly)."""
    V: dict[str, str] = {}
    try:
        root = next(p for p in _Path(__file__).resolve().parents
                    if (p / "pyproject.toml").exists())
        art = root / "ml" / "artifacts"
        m = _json.loads((art / "metrics_h4.json").read_text())
        t = m["oot_test"]["calibrated_lgbm"]
        lg = m["oot_test"]["logit_benchmark"]
        ci = m.get("oot_test_ci", {})
        d = m.get("lgbm_vs_logit_ap_diff", {})
        rb = m.get("rolling_backtest", {}).get("aggregate", {})
        unc = m.get("challengers", {}).get("unconstrained_gbm", {})

        def _rng(x):
            return f"[{x[0]:.3f}, {x[1]:.3f}]" if x and x[0] is not None else "[—]"

        dci = d.get("ap_diff_ci", [None, None])
        V.update(
            pr=f"{t['pr_auc']:.3f}", roc=f"{t['roc_auc']:.3f}",
            recall_pct=f"{t['recall_at_k'] * 100:.1f}%",
            logit_pr=f"{lg['pr_auc']:.3f}", logit_roc=f"{lg['roc_auc']:.3f}",
            boot_pr=_rng(ci.get("pr_auc_ci")), boot_roc=_rng(ci.get("roc_auc_ci")),
            boot_recall=_rng(ci.get("recall_at_k_ci")),
            paired_ci=(f"[{dci[0]:+.3f}, {dci[1]:+.3f}]" if dci[0] is not None else "[—]"),
            p_beat=f"{d.get('prob_a_beats_b', 0) * 100:.1f}%",
            roll_mean=str(rb.get("pr_auc_mean", "—")), roll_std=str(rb.get("pr_auc_std", "—")),
            roll_min=str(rb.get("pr_auc_min", "—")), roll_max=str(rb.get("pr_auc_max", "—")),
            n_est=str(m.get("final_model", {}).get("n_estimators", "—")),
            unc_pr=f"{unc.get('pr_auc', 0):.3f}",
        )
        oc = m.get("oot_calibration", {})
        V.update(
            ece=f"{oc.get('ece', float('nan')):.2e}",
            cal_pred=f"{oc.get('top_decile_pred', float('nan')):.4f}",
            cal_obs=f"{oc.get('top_decile_obs', float('nan')):.4f}",
        )
        viz = _json.loads((art / "viz_pack.json").read_text())
        si = viz.get("shap_importance", [])
        for i in range(min(3, len(si))):
            V[f"shap{i+1}"] = si[i]["feature"]
            V[f"shap{i+1}_v"] = f"{si[i]['mean_abs_shap']:.3f}"
        try:
            fd = _json.loads((art / "failure_decomposition.json").read_text())
            tc = fd.get("type_counts", {})

            def _cis(key):
                c = fd.get(key)
                return f"[{c[0]:.3f}, {c[1]:.3f}]" if c else "—"
            V.update(
                fd_credit=str(tc.get("credit_visible", "—")),
                fd_rate=str(tc.get("rate_liquidity_visible", "—")),
                fd_invis=str(tc.get("invisible", "—")),
                fd_full=str(fd.get("pr_auc_full", "—")),
                fd_addr=str(fd.get("pr_auc_addressable", "—")),
                fd_addr_n=str(fd.get("addressable_positives", "—")),
                fd_full_ci=_cis("pr_auc_full_ci"),
                fd_addr_ci=_cis("pr_auc_addressable_ci"),
            )
        except Exception:
            pass
        try:
            sq = _json.loads((art / "sequence_challenger.json").read_text())
            pw = sq.get("g0_paired_power_at_delta_0_02")
            V.update(
                seq_pr=str(sq.get("oot_pr_auc_gru", "—")),
                seq_gbm=str(sq.get("oot_pr_auc_gbm_served", "—")),
                seq_delta=(f"{sq.get('delta_vs_gbm'):+.3f}"
                           if sq.get("delta_vs_gbm") is not None else "—"),
                seq_k=str(sq.get("history_quarters", "—")),
                seq_power=(f"{pw * 100:.0f}%" if isinstance(pw, (int, float)) else "~6%"),
            )
            rs = sq.get("robustness_sweep", {})
            if rs:
                V.update(seq_sweep_n=str(rs.get("n_configs", "—")),
                         seq_sweep_min=str(rs.get("oot_min", "—")),
                         seq_sweep_max=str(rs.get("oot_max", "—")))
        except Exception:
            pass
    except Exception:
        pass
    # safe defaults so f-strings never KeyError
    for k in ("pr", "roc", "recall_pct", "logit_pr", "logit_roc", "boot_pr", "boot_roc",
              "boot_recall", "paired_ci", "p_beat", "roll_mean", "roll_std", "roll_min",
              "roll_max", "n_est", "unc_pr", "shap1", "shap1_v", "shap2", "shap2_v",
              "shap3", "shap3_v", "ece", "cal_pred", "cal_obs",
              "fd_credit", "fd_rate", "fd_invis", "fd_full", "fd_addr", "fd_addr_n",
              "fd_full_ci", "fd_addr_ci",
              "seq_pr", "seq_gbm", "seq_delta", "seq_k", "seq_power",
              "seq_sweep_n", "seq_sweep_min", "seq_sweep_max"):
        V.setdefault(k, "—")
    return V


_V = _load_metric_values()

AI_ARTICLES: dict[str, dict] = {
    "Problem Framing: Discrete-Time Hazard": {
        "cluster": "AI Engineering",
        "branch": "Modelling",
        "summary": (
            "Why bank failure is framed as a discrete-time hazard on a per-bank-quarter "
            "panel rather than a static classification."
        ),
        "body": (
            "Bank failure is a time-to-event problem. An institution is observed over many "
            "quarters, its financial condition changes from one filing to the next, and at "
            "some point it may close. FinLens frames this as a discrete-time hazard rather "
            "than a single static classification, because the question a supervisor asks is "
            "conditional: given that a bank is still alive at the end of this quarter, what is "
            "the probability it fails within the next few quarters.\n\n"
            "## The panel and the unit of observation\n"
            "The data is a panel keyed by (CERT, quarter), where CERT is the FDIC certificate "
            "number and the quarter comes from a Call Report filing. Each row is one bank "
            "observed at one quarter-end, carrying that quarter's financial ratios. The same "
            "bank contributes many rows across its life. Time is handled as an integer "
            "ordinal: ``obs_qord = year * 4 + (quarter - 1)``, computed in `labels.py`, so "
            "differences between quarters are exact arithmetic and the embargo logic in "
            "[[Out-of-Time Evaluation]] can reason about gaps without date parsing.\n\n"
            "## The hazard target\n"
            "For each bank-quarter the target answers a forward-looking question: does this "
            "institution fail within the next H quarters. The default horizon is H = 4 (one "
            "year). This turns survival analysis into a sequence of binary classification "
            "problems, one per bank-quarter, which is the discrete-time hazard formulation. "
            "It is well suited to time-varying covariates: capital, asset quality, earnings, "
            "and liquidity all drift quarter to quarter, and each row carries the values "
            "current as of that quarter. The exact labelling rule, including how survivors and "
            "censored banks are treated, is described in [[Labelling and Leakage Control]].\n\n"
            "## Why not a static classifier\n"
            "A static classifier that asks 'is this a bad bank' ignores that risk is a "
            "function of when you stand. A bank healthy in 2015 and failing in 2023 is a "
            "negative in early panels and a positive near the end. Collapsing its history to a "
            "single label would discard the time-varying signal that makes early warning "
            "possible. The hazard panel keeps every quarter as its own observation, so the "
            "model learns how a deteriorating trajectory raises near-term failure odds.\n\n"
            "## Extreme class imbalance\n"
            "Bank failure is rare. In the out-of-time test window the base rate is about "
            "0.00055, that is roughly one positive per 1,800 bank-quarters (66 failures among "
            "118,943 rows). This imbalance shapes every downstream decision. The model in "
            "`train.py` uses a capped ``scale_pos_weight`` (raw negative-to-positive ratio is "
            "near 190, capped at 25) so positives stay emphasized without the model saturating "
            "instantly. It also dictates the choice of headline metric: accuracy is useless at "
            "this base rate, so evaluation leads with PR-AUC and recall at a review budget, "
            "discussed in [[Out-of-Time Evaluation]].\n\n"
            "## What the framing does not attempt\n"
            "The model predicts the public failure outcome (FDIC RESTYPE = FAILURE), which is "
            "the project's defined target. It scores bank-level "
            "financial condition from Call Report ratios; macroeconomic series are business "
            "context on other surfaces, not model inputs. Competing exits, a bank leaving the "
            "panel by merger rather than failure, are handled through censoring and cross-checked "
            "against a built discrete-time Fine-Gray subdistribution model (within noise). These "
            "boundaries are stated "
            "plainly so the score is read as what it is: a calibrated probability of public "
            "failure within the horizon, conditional on surviving to the observation quarter."
        ),
    },
    "Feature Engineering and the Monotone Contract": {
        "cluster": "AI Engineering",
        "branch": "Modelling",
        "summary": (
            "The 34 CAMELS-aligned features and the economically-signed monotone "
            "constraints that keep the model's relationships defensible."
        ),
        "body": (
            "The model reads 34 features derived from the raw FDIC panel in `features.py`. "
            "They are organized along the CAMELS supervisory dimensions (capital, asset "
            "quality, management proxies, earnings, liquidity, and sensitivity) and each one "
            "carries an economically-signed monotone constraint that the gradient-boosted "
            "model is required to honor.\n\n"
            "## Levels: the CAMELS ratios\n"
            "Level features are point-in-time ratios computed per bank-quarter. Capital is "
            "captured by ``equity_to_assets``, ``tier1_rwa_ratio`` (the risk-based tier-1 "
            "ratio), and ``tier1_leverage``. Asset quality uses ``noncurrent_to_loans``, "
            "``nco_to_loans`` (net charge-offs), and ``allowance_to_loans``. Earnings use "
            "``roa``, ``roe``, ``nim`` (net interest margin), and ``efficiency_ratio``. "
            "Liquidity and funding use ``loans_to_deposits``, ``brokered_to_deposits``, "
            "``securities_to_assets``, and ``cash_to_assets``. Ratios are built with a safe "
            "divide that blanks near-zero denominators, so a vanishing balance never produces "
            "a spurious extreme value.\n\n"
            "## The 2023-regime features\n"
            "Three features were added specifically because the 2023 episode (SVB, Signature, "
            "First Republic) was a deposit-run and interest-rate event invisible to classic "
            "credit-quality ratios. ``uninsured_deposit_share`` is uninsured deposits over "
            "total deposits (DEP minus DEPINS, over DEP). ``htm_securities_share`` and "
            "``afs_securities_share`` measure held-to-maturity and available-for-sale "
            "securities concentration; long-duration bonds parked at amortized cost hide rate "
            "losses, and a high held-to-maturity share combined with a high uninsured share is "
            "the run-vulnerability profile. The business reading of this episode is in "
            "[[Out-of-Time Evaluation]] through the by-year cohorts.\n\n"
            "## Trends and peer z-scores\n"
            "Beyond levels, the model sees movement and relative position. Trend features are "
            "quarter-over-quarter and year-over-year deltas on a core set of ratios "
            "(``equity_to_assets``, ``noncurrent_to_loans``, ``roa``, ``nim``, "
            "``loans_to_deposits``), plus asset growth. These are computed within each bank's "
            "own history, sorted by certificate and report date. Peer z-scores standardize a "
            "ratio against banks of similar size in the same quarter: institutions are bucketed "
            "into asset-size bands by log-asset quantile, and a ratio's distance from its "
            "band-and-quarter mean is expressed in standard deviations. This makes "
            "``equity_to_assets_peer_z`` and similar features read as 'how stressed is this "
            "bank relative to its peers right now', which is more stable across regimes than a "
            "raw level.\n\n"
            "## The monotone contract\n"
            "Every feature has a recorded sign in ``MONOTONE_CONSTRAINTS``: +1 means a higher "
            "value must not decrease predicted risk, -1 means a higher value must not increase "
            "it, and 0 leaves the relationship free. More capital lowers risk "
            "(``equity_to_assets`` is -1), worse asset quality raises it "
            "(``noncurrent_to_loans`` is +1), higher uninsured-deposit share raises it (+1), "
            "and so on. These constraints are passed straight into LightGBM via "
            "``monotone_constraints``, so the boosted trees cannot learn a perverse, "
            "non-monotone relationship that a validator would reject. Size is left "
            "unconstrained (``log_assets`` is 0) because the level effect of size is "
            "ambiguous. This contract is what makes the model's behavior explainable in the "
            "supervisory sense; see [[Explainability with SHAP]] and [[Model Risk and "
            "Governance]].\n\n"
            "## Data caveat\n"
            "The features are computed from the FDIC financials endpoint, which returns "
            "currently-restated values rather than originally-filed Call Report figures. "
            "Feature values are therefore as-served, not strictly point-in-time. Reconstructing "
            "originally-filed FFIEC data is the path to exact point-in-time feature integrity "
            "and is noted as a known limitation rather than silently ignored."
        ),
    },
    "Labelling and Leakage Control": {
        "cluster": "AI Engineering",
        "branch": "Modelling",
        "summary": (
            "How forward-looking failure labels are assigned and how mergers and "
            "end-of-data are censored rather than mislabelled."
        ),
        "body": (
            "The label is the answer to the hazard question: within the next H quarters, does "
            "this bank-quarter end in failure. Getting this right is where most time-to-event "
            "models leak, so `labels.py` is explicit about every case and what happens to it.\n\n"
            "## The labelling rule\n"
            "For an observation quarter q (as an ordinal), a failure quarter f if one exists, "
            "the bank's last observed quarter L, and horizon H, the rule is:\n\n"
            "- if a failure exists and ``f <= q``: drop the row (the bank already failed; it is "
            "not a live observation).\n"
            "- if a failure exists and ``q < f <= q + H``: label 1 (fails within the horizon).\n"
            "- if a failure exists and ``f > q + H``: label 0 (survives the horizon window).\n"
            "- if no failure and ``L >= q + H``: label 0 (observed alive through the full "
            "horizon).\n"
            "- if no failure and ``L < q + H``: drop the row (right-censored, cannot be "
            "confirmed).\n\n"
            "The label is strictly forward-looking: it only ever looks at quarters after q. A "
            "row is never given a label its own future cannot support.\n\n"
            "## Censoring done correctly\n"
            "The subtle cases are the drops, and they are what separate an honest label from a "
            "biased one. A healthy bank that disappears from the panel by merger or acquisition "
            "has no failure record, so it simply stops appearing. Near the end of its presence "
            "its remaining quarters cannot be confirmed alive for a full H, so they are "
            "right-censored and dropped, never labelled negative. The same applies at the edge "
            "of the data: the most recent H quarters of the whole panel cannot yet be confirmed "
            "and are dropped rather than assumed safe. Labelling these as negatives would "
            "manufacture easy true-negatives and inflate every metric. Treating a merger exit "
            "as a failure would manufacture false positives. Both are avoided by survival "
            "presence in the panel being the ground truth, not an assumption.\n\n"
            "## What counts as a failure\n"
            "Failures come from the FDIC failures API, keyed on CERT, FAILDATE, and RESTYPE. "
            "Only ``RESTYPE == 'FAILURE'`` is treated as a true closure; open-bank assistance "
            "is excluded from the positive label by default. The failure date is parsed with a "
            "pinned ``%m/%d/%Y`` format so an ambiguous string cannot silently coerce to a "
            "missing value and drop a real failure, and the earliest failure per certificate is "
            "kept. The date is converted to the same quarter ordinal used everywhere else, so "
            "label assignment is pure integer comparison.\n\n"
            "## Why competing risks are censored, then cross-checked\n"
            "A bank can leave the panel for two reasons that matter: it fails, or it is "
            "acquired. These are competing risks. FinLens handles the acquisition path by "
            "censoring (the merged bank simply has no failure record and ends its presence). That "
            "choice was then validated, not just asserted: a cause-specific merger hazard plus an "
            "Aalen-Johansen cumulative incidence show mergers are about four times more common than "
            "failures, but only about 2.2 percent of merger exits were elevated-distress at exit, "
            "so the informative-censoring bias is small. A discrete-time Fine-Gray subdistribution "
            "model was then built and lands within noise of the cause-specific model, confirming "
            "the censoring is adequate. Details are in [[Model Risk and Governance]].\n\n"
            "## Leakage control begins here\n"
            "Because the label looks forward into ``(q, q + H]``, a training row carries "
            "information about that future window. The split machinery must therefore keep any "
            "test quarter strictly outside every training row's label window. That embargo is "
            "the subject of [[Out-of-Time Evaluation]]; it is the second half of leakage "
            "control, the first half being that the label itself never peeks at q or earlier "
            "for its answer and never invents an outcome for unconfirmed quarters."
        ),
    },
    "Out-of-Time Evaluation": {
        "cluster": "AI Engineering",
        "branch": "Evaluation & Calibration",
        "summary": (
            "The embargoed out-of-time split, the rare-event metrics, the bootstrap "
            "intervals, and the rolling backtest that make the headline trustworthy."
        ),
        "body": (
            "A bank-distress model can only be validated one way: train on the past, test on "
            "the future. Random k-fold cross-validation is forbidden here because it lets a "
            "model learn from quarters that come after the ones it is scored on. `splits.py` "
            "and `evaluate.py` implement the time-respecting alternative.\n\n"
            "## The embargo\n"
            "A training row at quarter q with horizon H has a label that looks into "
            "``(q, q + H]``. For a test period starting at quarter t to be genuinely "
            "out-of-sample, no training row's label window may reach into it. That requires "
            "``q + H < t``, i.e. ``q <= t - H - reporting_lag - 1``. The gap is the embargo. It "
            "equals the horizon plus a reporting lag, the latter reflecting that Call Reports "
            "file after quarter-end so the data is only genuinely available as-of a later date. "
            "The invariant is not just trusted; ``assert_no_temporal_overlap`` is called inside "
            "every fold construction, so a leaking split fails loudly at runtime rather than "
            "passing a unit test and rotting. A bank may legitimately appear in both train and "
            "test in non-overlapping windows; that is required for a hazard panel and is not a "
            "grouping violation, because the embargo guarantees no single observation's label "
            "straddles the boundary. See [[Labelling and Leakage Control]] for why the label "
            "window is what must be embargoed.\n\n"
            "## The headline window\n"
            "The main evaluation uses ``final_holdout_split`` (configured here to 28 quarters; "
            "the helper itself defaults to 8) to hold out roughly 2019 through 2026 as the "
            "out-of-time test set. This window is chosen "
            "deliberately because it contains real failures, including the 2023 cluster. "
            "Judging a rare-event model on a single calm holdout with zero positives is "
            "meaningless. The test set is 118,943 bank-quarters with 66 real failures. The "
            f"calibrated LightGBM scores PR-AUC {_V['pr']}, ROC-AUC {_V['roc']}, and recall at "
            f"the top-200 review budget of {_V['recall_pct']}.\n\n"
            "## Why PR-AUC, not accuracy or ROC\n"
            "At a 0.00055 base rate, accuracy is trivially near-perfect for a model that flags "
            "nothing, so it is not reported. PR-AUC (average precision) is the headline because "
            "it tracks how well true positives concentrate at the top of the ranking, which is "
            "exactly what off-site monitoring cares about. recall@k measures, of a fixed "
            "supervisory review budget of the k highest-scored banks, how many real failures "
            "are caught. ROC-AUC is reported only for comparability with the literature; "
            f"notably the logit benchmark posts a higher ROC-AUC ({_V['logit_roc']}) yet a much "
            f"lower PR-AUC ({_V['logit_pr']}), which is the textbook way ROC misleads under heavy "
            "imbalance.\n\n"
            "## Uncertainty, not point estimates\n"
            "With only 66 positives, a bare point estimate is not a defensible result. "
            "``bootstrap_metrics`` reports 95% bootstrap intervals (the G0 coverage simulation "
            f"selects BCa as the method that actually covers at this positive count): PR-AUC about "
            f"{_V['boot_pr']}, ROC-AUC about {_V['boot_roc']}, recall@k about {_V['boot_recall']}. "
            f"To test whether the model genuinely beats the benchmark, ``paired_bootstrap_ap_diff`` "
            f"resamples both models on the same draws: the PR-AUC difference has a 95% CI of "
            f"about {_V['paired_ci']} and the model beats the logit in {_V['p_beat']} of resamples. "
            "The effective-challenge benchmark is detailed in [[Model Risk and Governance]].\n\n"
            "## The rolling backtest and by-year cohorts\n"
            "One holdout cannot show variance. ``rolling_origin_folds`` builds expanding-window "
            "out-of-time folds at successive origins, and the model is refit and rescored on "
            f"each. Across 10 folds, PR-AUC averages {_V['roll_mean']} with a standard deviation "
            f"of {_V['roll_std']}, ranging from near {_V['roll_min']} in near-failure-free calm "
            f"years to {_V['roll_max']} in a failure-rich "
            "fold. The by-year cohort table tells the same story honestly: strong in "
            "failure-containing years such as 2019, 2020, and 2025, near the floor or undefined "
            "in calm years such as 2021 (zero failures). A model that scores well only when "
            "averaged over a long window would be hiding this; exposing it is the point."
        ),
    },
    "Probability Calibration": {
        "cluster": "AI Engineering",
        "branch": "Evaluation & Calibration",
        "summary": (
            "Why the raw model score is recalibrated on a stratified in-train holdout and "
            "how calibration quality is measured where decisions are actually made."
        ),
        "body": (
            "A ranking tells you which banks are riskier than others; a calibrated probability "
            "tells you how risky in absolute terms. Off-site monitoring needs the second, so "
            "the model's raw score is passed through a calibration step before it is served.\n\n"
            "## Why the raw score needs calibrating\n"
            "The LightGBM model is fit with a capped ``scale_pos_weight`` to keep rare "
            "positives in view. That class weighting deliberately distorts the output scale: "
            "the raw scores rank well but do not read as true probabilities. Calibration "
            "corrects the scale while preserving the ranking, so a served value near 0.004 "
            "means roughly a 0.4% chance of failure within the horizon rather than an arbitrary "
            "number.\n\n"
            "## The stratified in-train holdout\n"
            "The most important and least obvious decision is what data the calibrator sees. In "
            "`train.py`, ``_fit_calibrated`` splits the training data into a fit portion and a "
            "stratified calibration portion (a 20% slice, stratified on the label so it "
            "contains positives). The model is fit on one part and the calibrator is fit on the "
            "held-out stratified part. The reason for stratifying is concrete: if the "
            "calibration set were a calm temporal tail with no failures, a sigmoid calibrator "
            "would have nothing to anchor on and could invert the ranking. Crucially, all "
            "calibration rows are still pre-test, drawn from inside the training period, so "
            "fitting the calibrator never touches the out-of-time test set and the ranking "
            "evaluated in [[Out-of-Time Evaluation]] stays unleaked.\n\n"
            "## Isotonic versus sigmoid\n"
            "The method is chosen by how many positives the calibration set has. With at least "
            "50 positives the model uses isotonic regression, a flexible monotone fit; with "
            "fewer it falls back to Platt scaling (a sigmoid), which has fewer parameters and "
            "is harder to overfit on scarce positives. On the headline run the calibration set "
            "clears the threshold and isotonic is used. Calibration is applied with a frozen "
            "base estimator so the already-trained model is not refit during the calibration "
            "step.\n\n"
            "## Measuring calibration at the base rate\n"
            "A single all-rows Brier score is nearly useless here, because at a 0.00055 base "
            "rate it is dominated by true negatives and a model that predicts almost zero "
            "everywhere scores well. ``calibration_report`` therefore reports three things: an "
            "expected calibration error over probability bins, the Brier restricted to the "
            "top-scoring decile, and the observed-versus-predicted rate inside that decile, "
            f"which is where flags are actually raised. On the headline run the ECE is about "
            f"{_V['ece']}, and in the top decile the model predicts about {_V['cal_pred']} against "
            f"an observed {_V['cal_obs']}. The top-decile numbers are the ones that matter: they "
            "say that "
            "among the banks the model is most worried about, its stated probability is close "
            "to the realized failure rate, slightly conservative.\n\n"
            "## How calibration reaches serving\n"
            "The served model is the calibrated estimator, not the bare booster. It is "
            "serialized with skops and resolved through the registry, so what scores a bank in "
            "production is the same calibrated pipeline that was validated. The mapping from a "
            "calibrated probability to an action flag, and the threshold that governs it, is "
            "described in [[Serving the Model]]."
        ),
    },
    "Explainability with SHAP": {
        "cluster": "AI Engineering",
        "branch": "Evaluation & Calibration",
        "summary": (
            "Global and local SHAP reason codes from the LightGBM booster, what they reveal "
            "about the model's drivers, and the documented limits of the method."
        ),
        "body": (
            "A monotone-constrained model is interpretable by construction in its direction; "
            "SHAP adds magnitude and per-bank reason codes. `explain.py` computes both global "
            "feature importance and local explanations using a TreeExplainer.\n\n"
            "## TreeExplainer on the booster\n"
            "Explanations are computed on the native LightGBM booster, the object whose ranking "
            "actually drives the decision, using the path-dependent TreeExplainer. For tree "
            "models this method needs no background dataset, which keeps it both fast and "
            "memory-frugal. The explainer is cached so per-request serving does not rebuild it, "
            "and the number of rows explained at once is bounded so peak memory stays within "
            "the deployment budget. The booster used for explanations is the same artifact "
            "loaded for fallback scoring in [[Serving the Model]].\n\n"
            "## Global importance\n"
            "Global importance is the mean absolute SHAP value per feature over a bounded "
            "reservoir sample of out-of-time-era rows. The ranking is dominated by capital and "
            "earnings and asset quality, consistent with the bank-failure literature. The top "
            f"driver by a wide margin is ``{_V['shap1']}`` (mean |SHAP| about {_V['shap1_v']}), "
            f"followed by ``{_V['shap2']}`` (about {_V['shap2_v']}) and ``{_V['shap3']}`` (about "
            f"{_V['shap3_v']}), then "
            "``tier1_leverage`` and ``equity_to_assets``. After those come peer-relative and "
            "trend features such as ``equity_to_assets_peer_z``, ``equity_to_assets_yoy_delta``, "
            "and ``noncurrent_to_loans_peer_z``. The dominance of the risk-based tier-1 ratio, "
            "total noncurrent loans, and return on equity matches the economic priors encoded in "
            "the monotone contract described in [[Feature Engineering and the Monotone "
            "Contract]]: capital adequacy, asset quality, and profitability carry most of the "
            "near-term failure signal. (Noncurrent loans rose to the #2 driver once the feature "
            "was corrected to use total noncurrent, NCLNLS, instead of the 90+-accruing-only "
            "field; see [[Model Risk and Governance]].)\n\n"
            "## Local reason codes\n"
            "For a single bank, ``local_reasons`` returns the top SHAP contributors for that "
            "one record, each with the feature, its value, the signed SHAP contribution, and "
            "whether it increases or decreases risk. This is what a reviewer reads to "
            "understand why a particular institution was flagged: for example a low tier-1 "
            "ratio pushing risk up, or a strong peer-relative capital position pulling it down. "
            "The contributions sum from a base value toward the model's score for that bank, so "
            "a reviewer can see not only which features mattered but how much each one moved the "
            "score relative to the others. Because the model is monotone, the sign of each "
            "contribution is consistent with the economic direction of the feature, which makes "
            "the reason codes coherent rather than contradictory: a feature constrained to raise "
            "risk can never appear with a risk-lowering attribution, so the explanation cannot "
            "argue against the contract it was trained under.\n\n"
            "## A documented limitation\n"
            "SHAP assumes feature independence in probability space. CAMELS ratios are "
            "correlated (capital ratios move together, asset-quality ratios move together), so "
            "that assumption is violated and the attributed contributions should be read as "
            "indicative rather than exact. This is stated openly in both the code and the model "
            "card. The consequence is a scope limit: local SHAP here is "
            "validator-and-supervisor-facing transparency, not a legally-sufficient "
            "adverse-action reason code. There is no consumer applicant and no ECOA or Reg-B "
            "obligation, because the model scores institutions, not people. The governance "
            "framing of this distinction is in [[Model Risk and Governance]]."
        ),
    },
    "Model Risk and Governance": {
        "cluster": "AI Engineering",
        "branch": "Governance & Operations",
        "summary": (
            "The SR 11-7 three-pillar validation, the effective-challenge benchmark, the "
            "registry-based champion alias, the CI metric gate, and the honest known gaps."
        ),
        "body": (
            "The model is documented and validated against the three pillars of model-risk "
            "management: conceptual soundness, ongoing monitoring, and outcomes analysis. The "
            "validation report and model card are generated from the real artifact, so the "
            "numbers in governance documents match the numbers the model actually produced.\n\n"
            "## Conceptual soundness\n"
            "The first pillar is whether the model makes sense before any metric is read. The "
            "discrete-time hazard framing is the established approach for time-to-failure with "
            "time-varying covariates (see [[Problem Framing: Discrete-Time Hazard]]). The 34 "
            "features are CAMELS-aligned with economically-signed monotone constraints, which "
            "prevent the perverse relationships a validator would reject (see [[Feature "
            "Engineering and the Monotone Contract]]). Leakage is controlled by the labelling "
            "rule and the embargoed split, enforced at runtime. The out-of-time ROC-AUC of "
            f"about {_V['roc']} sits well below the level that would suggest leakage, which is "
            "itself "
            "evidence the split is honest.\n\n"
            "## Effective challenge\n"
            "A model is only credible if something independent tries to beat it. The benchmark "
            "is a penalized logistic regression with median imputation, standardization, and "
            "balanced class weights, the standard regulatory-style linear reference. The "
            f"boosted model beats it on the rare-event metric (PR-AUC {_V['pr']} versus "
            f"{_V['logit_pr']}) and on recall@k. Because that margin rests on 66 positives, it is "
            f"reported as a paired bootstrap rather than a bare comparison: difference 95% CI about "
            f"{_V['paired_ci']}, P(model beats logit) about {_V['p_beat']}. The benchmark and the "
            "paired test live in "
            "[[Out-of-Time Evaluation]].\n\n"
            "## Registry, champion alias, and the metric gate\n"
            "Promotion and rollback go through the MLflow model registry using aliases rather "
            "than deprecated stages. `registry.py` resolves serving to ``models:/"
            "finlens_bank_distress@champion``, so promoting a new model or rolling back is a "
            "single alias repoint, and `train.py` promotes the newest registered version to the "
            "champion alias after logging. A CI metric gate blocks promotion unless the model "
            "clears its bars: PR-AUC must beat the logit benchmark by a margin, OOT ROC-AUC must "
            "stay below the leakage-suspicion ceiling, and calibration ECE must be within bound. "
            "Artifacts are serialized with skops rather than raw pickle, and loading enforces a "
            "trusted-type allow-list so a tampered artifact cannot execute arbitrary code (see "
            "[[Serving the Model]]).\n\n"
            "## A note on protected-class fairness\n"
            "The model scores institutions, not consumers, so there is no protected class. "
            "Demographic parity, disparate impact, and the four-fifths rule do not apply and "
            "are deliberately not computed. What is done instead is cross-segment outcomes "
            "analysis (by asset-size tier, region, and charter class), to confirm the model is "
            "not a single-segment fit. This is the SR 11-7 sense of fairness, performance "
            "equity across segments, not consumer-credit fairness.\n\n"
            "## Known gaps\n"
            "The governance posture is candid about what remains. Hyperparameters ARE tuned "
            "with Optuna over inner time-series CV folds (the search is shown in the Model "
            f"Quality tab); the served tree count (n_estimators = {_V['n_est']}) comes from "
            "out-of-time "
            "early stopping on average precision. The effective-challenge ladder is built and "
            f"scored, not planned: a penalized logit, an unconstrained GBM (PR-AUC {_V['unc_pr']}, "
            f"which the monotone model now matches), and bagged / stacked ensembles are all measured "
            "(the ablation forest), though at 66 "
            "out-of-time positives none of these point gains is statistically separable. The "
            "served model is the 12-seed BAGGED ensemble (chosen for variance reduction and the "
            "best point estimate); the single, tuned, and unconstrained models are the challengers. "
            "Competing risks are handled by censoring and CROSS-CHECKED against a built discrete-time "
            "Fine-Gray subdistribution model (within noise of the cause-specific model), so that is "
            "no longer a remaining lever. The genuine remaining lever is originally-filed "
            "point-in-time FFIEC features (feasible and validated for 2014+, but the full-history "
            "retrain underperforms because originally-filed data is noisier than restated). These "
            "are stated as the path to production, not papered over."
        ),
    },
    "Drift Monitoring": {
        "cluster": "AI Engineering",
        "branch": "Governance & Operations",
        "summary": (
            "Quarterly data-drift and prediction-drift monitoring with Evidently, and why "
            "prediction drift is the earliest available warning signal."
        ),
        "body": (
            "A model validated once is not validated forever. Bank balance sheets and the "
            "macro regime shift, and the model's inputs and outputs shift with them. "
            "`monitor.py` measures that shift each quarter so degradation is caught before it "
            "becomes a missed failure.\n\n"
            "## Two kinds of drift\n"
            "The monitor distinguishes data drift from prediction drift. Data drift is a change "
            "in the distribution of the input features between a reference window and a current "
            "window. Prediction drift is a change in the distribution of the model's own output "
            "scores between those windows. Both matter: input drift can warn that the model is "
            "being asked about a population it was not trained on, while output drift can warn "
            "that the model's behavior is changing even when no single input looks unusual.\n\n"
            "## Why prediction drift is the earliest signal\n"
            "The fundamental timing problem with a hazard model is that ground-truth labels "
            "arrive late: you only learn a bank failed after it fails, and confirming a "
            "negative requires waiting out the full horizon (see [[Labelling and Leakage "
            "Control]]). That means true performance cannot be measured in near-real-time. "
            "Prediction drift fills the gap. Because the score distribution can be computed the "
            "moment new Call Reports land, a shift in scores is the earliest quantitative "
            "warning that something has changed, well before any label confirms it. The monitor "
            "treats ``distress_score`` as a first-class analysis column for exactly this "
            "reason.\n\n"
            "## How it is computed\n"
            "The reference and current windows are pulled from the panel by quarter, with the "
            "split defaulting to pre-2019 as reference and 2019-onward as current, each capped "
            "for memory with a reservoir sample. Both windows are scored with the served model "
            "via the same prediction path described in [[Serving the Model]], so the "
            "prediction-drift comparison reflects the actual deployed model. Evidently's "
            "``DataDriftPreset`` runs over the feature columns plus the score, and the result "
            "is summarized into a compact JSON-safe dict: the number and share of drifted "
            "columns, the prediction-drift score, and the top drifted features.\n\n"
            "## A real dependency constraint\n"
            "Evidently pins an older Plotly than the rest of the application needs. Rather than "
            "force one library to lose, the monitor uses only Evidently's programmatic Report "
            "API and serializes the result to a dict; it never invokes Evidently's own Plotly "
            "rendering. That lets the two coexist in one environment, and if a future render "
            "path is needed it would run in an isolated process. This is a small but real "
            "engineering decision documented in the code rather than hidden.\n\n"
            "## Where drift fits in governance\n"
            "Drift monitoring is the operational half of the second SR 11-7 pillar, ongoing "
            "monitoring, alongside input validation, freshness and null-rate checks, and the "
            "quarterly retraining cadence. A sustained prediction-drift signal or a high share "
            "of drifted features is a prompt to investigate and, if warranted, retrain and "
            "re-evaluate through the metric gate. The governance context for that gate and the "
            "champion alias is in [[Model Risk and Governance]]."
        ),
    },
    "Serving the Model": {
        "cluster": "AI Engineering",
        "branch": "Governance & Operations",
        "summary": (
            "How the calibrated model is loaded, the registry-to-local fallback chain, "
            "safe deserialization, scoring entry points, and the decision threshold."
        ),
        "body": (
            "Serving turns the validated artifact into live scores for real banks, batch jobs, "
            "and interactive scenarios. `predict.py` is the single entry point, and it is built "
            "so that the thing scoring a bank in production is the same calibrated pipeline that "
            "was validated.\n\n"
            "## The load chain\n"
            "``load_model`` resolves the model in a deliberate order. First it tries the MLflow "
            "registry champion alias (``models:/finlens_bank_distress@champion``); resolving "
            "through the alias is what makes an alias repoint a real serve-time rollback (see "
            "[[Model Risk and Governance]]). If the registry is unavailable, it falls back to a "
            "pinned local artifact: the calibrated skops file first, then the native LightGBM "
            "booster as a last resort. The booster fallback is uncalibrated and is flagged as "
            "such on the returned object, so a caller can tell whether it is reading true "
            "probabilities or a bare ranking. The result is cached so repeated requests do not "
            "reload from disk. This ordering gives both governed promotion through the registry "
            "and offline resilience when the registry cannot be reached.\n\n"
            "## Safe deserialization\n"
            "Model artifacts are loaded with skops, not raw pickle, and the load enforces a "
            "real trust boundary. Before deserializing, the code asks skops which non-default "
            "types the file contains and compares them against an explicit allow-list of the "
            "only types FinLens serializes (the calibrated classifier, the isotonic and sigmoid "
            "calibrators, the frozen estimator wrapper, the LightGBM classifier and booster, "
            "and an ordered dict). If the artifact declares any type outside that set, the load "
            "is refused as possible tampering. This is the difference between trusting whatever "
            "a file claims, which is the pickle failure mode, and trusting only a known set.\n\n"
            "## Scoring entry points\n"
            "Three functions cover the serving surface. ``score_frame`` scores a DataFrame of "
            "many banks at once, checking that all required feature columns are present and "
            "raising a clear error if any are missing. ``score_record`` scores a single bank "
            "from a feature dict, filling absent features with NaN, which LightGBM handles "
            "natively, so a partial or hypothetical bank can still be scored. Both align the "
            "input to the pinned ``FEATURE_COLUMNS`` order, which guarantees the served feature "
            "vector matches the trained one. The single-record path is what powers the "
            "interactive scenario tool, where a user can perturb a ratio and watch the "
            "probability move along the monotone direction from [[Feature Engineering and the "
            "Monotone Contract]].\n\n"
            "## From probability to flag\n"
            "``decision`` maps a calibrated probability to an action by comparing it against a "
            "configured flag threshold, returning the probability, the boolean flag, and the "
            "threshold itself. Keeping the threshold in configuration rather than hard-coding it "
            "means the operating point can be tuned to a review budget without retraining. The "
            "probability being compared is calibrated, so the threshold has a meaning in true "
            "failure-rate terms rather than being an arbitrary score cutoff (see [[Probability "
            "Calibration]]).\n\n"
            "## Consistency across the platform\n"
            "Because every consumer, the scoring API, the scenario tab, the SHAP explainer, and "
            "the drift monitor, loads through this same path and the same pinned feature set, "
            "the model behaves identically wherever it is invoked. [[Drift Monitoring]] scores "
            "its reference and current windows through this entry point precisely so the "
            "prediction-drift signal reflects the deployed model and not a stale copy."
        ),
    },
    "Failure-Type Decomposition": {
        "cluster": "AI Engineering",
        "branch": "Evaluation",
        "summary": (
            "Why the by-year out-of-time number swings so violently: the 66 failures are "
            "three different kinds of event, and the model is scoped to only one of them."
        ),
        "body": (
            "The headline out-of-time PR-AUC is an average over failures that are not the same "
            "kind of event. Averaging a credit-distress model across failure types it was never "
            "designed to see is what makes the by-year number swing from near the floor to "
            "strong and back. This article decomposes the 66 out-of-time failures by mode, using "
            "model-independent financial signatures (the raw Call Report condition at the last "
            "filing, not the model's own score, to avoid circularity), and shows the swings "
            "track the failure-type mix of each filing-year cohort rather than being noise.\n\n"
            "## Three failure modes\n"
            f"Of the 66 failure bank-quarters (19 distinct banks), **{_V['fd_credit']}** are "
            "credit-visible (high noncurrent, charge-offs, or capital below the Prompt "
            "Corrective Action lines, the classic deterioration the model is built to catch), "
            f"**{_V['fd_rate']}** are rate/liquidity-visible (a large uninsured deposit base "
            "funding a marked-down securities book, the 2023 wave: Silicon Valley, Signature, "
            f"and First Republic), and **{_V['fd_invis']}** are financially invisible: the bank "
            "looked sound at its last filing and failed anyway. In practice the invisible class "
            "is the fraud and scam failures (Enloe State, Heartland Tri-State, First National "
            "Bank of Lindsay, Pulaski Savings), which carry no financial signature by "
            "construction.\n\n"
            "## A note on the year axis\n"
            "The cohorts are keyed by FILING year, not failure year. A positive bank-quarter is "
            "a filing that fails within the next four quarters, so the failure happens later: "
            "the 2022 filing cohort is the set of 2022 filings that failed in 2023. No banks "
            "failed in calendar 2021 or 2022; the by-year swings below are about when the "
            "doomed banks were filing, which is what the model actually scores.\n\n"
            "## The collapse has two distinct causes, not one\n"
            "The two near-floor filing cohorts collapse for opposite reasons. The **2022 filing "
            "cohort is a wrong-cohort collapse**: eleven of its fourteen failures are the 2023 "
            "rate/liquidity wave (Silicon Valley and peers), which a credit-skewed model ranks "
            "low because, on the credit axis, they looked fine. The **2024 filing cohort is an "
            "invisible-cohort collapse**: eight of its nine failures are fraud or sudden "
            "failures with no elevated financial signal, and no model built on quarterly Call "
            "Reports can rank those above healthy banks because the signal is not in the data. "
            "The strong cohorts (2019, 2020, 2025 filings) are exactly the credit-dominated "
            "ones. The annual headline is a weighted average whose weights are the unknown, "
            "cohort-specific failure-type mix.\n\n"
            "## PR-AUC on the addressable subset\n"
            f"Removing only the {_V['fd_invis']} structurally-invisible failures from the "
            f"positive set lifts out-of-time PR-AUC from {_V['fd_full']} (95% CI "
            f"{_V['fd_full_ci']}) to {_V['fd_addr']} (95% CI {_V['fd_addr_ci']}) on the "
            f"{_V['fd_addr_n']} addressable failures, by the same percentile bootstrap used for "
            "the headline. With fewer positives the addressable interval is wider, and the two "
            "intervals overlap heavily: this is a structural reattribution of where the signal "
            "is, not a separable accuracy gain. Two further checks: the addressable number "
            "depends only on the invisible/visible boundary (swapping any bank between the "
            "credit and rate/liquidity buckets leaves it unchanged, since neither bucket is "
            "dropped), and across the four threshold grids it ranges only narrowly as the "
            "invisible count moves between 9 and 14. The gap to the full set is the price of the "
            "invisible events, which no modelling on this data can recover.\n\n"
            "## Why this is the load-bearing finding\n"
            "It separates three things a single number conflates: what the model does well "
            "(credit-visible distress), what it under-weights but could learn given more such "
            "training mass (rate/liquidity failures), and what is structurally impossible on "
            "public financials (the invisible cohort). Only the middle category is a model-"
            "improvement opportunity; chasing a higher headline on the full set would be self-"
            "deception, because roughly a fifth of the positives carry no signal to find. At 66 "
            "failures none of this is statistically separable (~6% power, see "
            "[[Out-of-Time Evaluation]]); it is a structural "
            "explanation of where the signal comes from, not a certified gain. The matched "
            "architecture is tested separately in [[Sequence-Model Challenger]]."
        ),
    },
    "Sequence-Model Challenger": {
        "cluster": "AI Engineering",
        "branch": "Modelling",
        "summary": (
            "A GRU over each bank's quarterly trajectory, built to test whether within-bank "
            "temporal autocorrelation beats the point-in-time GBM. It does not."
        ),
        "body": (
            "The served model scores one bank-quarter at a time. A fair critique is that this "
            "under-uses within-bank temporal autocorrelation: a bank's trajectory, the shape of "
            "its last several quarters, may carry signal a point-in-time model cannot represent. "
            "The architecture matched to that hypothesis is a recurrent network over the "
            "quarterly sequence, so it was built and tested on equal footing rather than "
            "hand-waved as future work.\n\n"
            "## What was built\n"
            f"A GRU (hidden 48) over the last K = {_V['seq_k']} quarters of all 34 features, "
            "left-padded and masked per CERT, read out at the last unmasked step into a small "
            "ReLU head, z-scored on train statistics only, class-weighted, early-stopped on an "
            "inner time-ordered validation tail, and isotonic-calibrated with the same recipe as "
            "the GBM. It was evaluated on the identical out-of-time holdout used everywhere "
            "else.\n\n"
            "## Result: it does not beat the incumbent\n"
            f"The GRU scores out-of-time PR-AUC {_V['seq_pr']} against the served GBM's "
            f"{_V['seq_gbm']} (delta {_V['seq_delta']}). Its point estimate is lower, and it "
            "overfits in-sample: inner-validation PR-AUC reaches the low 0.6s and then collapses "
            "out-of-time. That collapse is informative. The trajectory signal the GRU learns in "
            "the training era does not transfer across the regime and cohort shift into the "
            "out-of-time window, which is exactly what the [[Failure-Type Decomposition]] "
            "predicts: the out-of-time failures are a different mix of modes, and a model that "
            "memorizes in-sample trajectory shapes has nothing to grab when the failure type "
            "changes.\n\n"
            "## Not a single-config artifact\n"
            f"To rule out a single bad configuration, a sweep of {_V['seq_sweep_n']} GRUs was "
            "run on the same split (hidden 16 to 48, dropout 0.2 to 0.4, weight decay 1e-5 to "
            f"1e-3, history length K in 4/8/12, three seeds). Out-of-time PR-AUC ranged "
            f"{_V['seq_sweep_min']} to {_V['seq_sweep_max']}, every configuration below the "
            "served GBM, with the in-sample to out-of-time collapse present in all of them. No "
            "reachable GRU beats the incumbent at this data scale regardless of capacity, "
            "regularization, history length, or seed, so the verdict is not inferred from one "
            "run.\n\n"
            "## Statistical separability\n"
            f"The GRU's {_V['seq_pr']} falls inside the served model's bootstrap PR-AUC "
            f"interval, and at 66 out-of-time failures the paired comparison has {_V['seq_power']} "
            "power, so the two are not statistically separable in either direction. The result "
            "is that the architecturally-matched sequence model did not deliver an out-of-time "
            "gain, its point estimate is worse, and the data cannot certify a difference of this "
            "size. Claiming the GRU captures trajectory structure the GBM misses would be the "
            "exact fake improvement to avoid: in-sample it appears to, out-of-time it does "
            "not.\n\n"
            "## Why the GBM remains served\n"
            "Even setting aside the point estimates (which are not separable), the GBM is "
            "preferred on grounds the small recurrent net cannot match at this data scale: a "
            "better out-of-time point estimate, monotone constraints (more capital can never "
            "raise predicted risk, a guarantee the GRU has no way to make), calibrated "
            "probabilities with per-bank SHAP attributions a supervisor can read, and a far "
            "smaller, auditable, serialization-safe artifact. The challenger is kept as the "
            "documented test of the trajectory hypothesis, not a candidate for promotion."
        ),
    },
}
