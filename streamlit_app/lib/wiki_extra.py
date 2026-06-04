"""New and deepened FinLens wiki articles.

These override or extend the base corpus (wiki_content.ARTICLES). Schema per entry:
{cluster, branch, summary, body}. Bodies are GitHub-flavoured markdown; the wiki page
builds a table of contents from the ## headings. Written in a clean, encyclopedic
register (plain, third-person-where-natural, no marketing, no self-congratulation).
"""

from __future__ import annotations

EXTRA_ARTICLES: dict[str, dict] = {
    "What FinLens Is": {
        "cluster": "Introduction",
        "branch": "",
        "summary": "An overview of the platform, what it does, and what it deliberately is not.",
        "body": (
            "FinLens is a banking-stress intelligence platform built on public United States "
            "banking data. It ingests FDIC Call Report financials, the FDIC failed-bank list, "
            "and Federal Reserve (FRED) macroeconomic series, turns them into a governed "
            "warehouse, and presents three views of the result: a business view for reading "
            "banking stress, a data-engineering view for inspecting how the data is produced, "
            "and an AI view for a calibrated bank financial-distress early-warning model.\n\n"
            "## What it does\n"
            "The platform answers a single question from public data: which U.S. banks look "
            "financially stressed, and how confident can we be in that read. It does this by "
            "scoring each bank-quarter with a probability of failure within four quarters, "
            "alongside the historical and macroeconomic context a reviewer needs to interpret "
            "that score.\n\n"
            "## What it is not\n"
            "FinLens is not a regulator, a bank, an investment adviser, or a deposit-safety "
            "service. The distress score ranks observable public-data stress; it is not "
            "supervisory action, and it is not a recommendation to move money. Confidential "
            "supervisory information (examiner CAMELS ratings, the Problem Bank List) is not "
            "public and is therefore out of scope; the public proxy for distress used here is "
            "the failed-bank outcome, not the examiner flag.\n\n"
            "## How it is built\n"
            "Everything runs on free, stable public sources and an open-source stack at no "
            "infrastructure cost. The data flows through a medallion warehouse (bronze, silver, "
            "intermediate, gold), the model is a monotone-constrained gradient-boosted hazard "
            "model with calibrated probabilities, and the whole pipeline is reproducible. The "
            "[[Platform Architecture]] article gives the end-to-end picture; "
            "[[The Three Surfaces]] explains the three views."
        ),
    },
    "The Problem: Bank Financial Distress": {
        "cluster": "Introduction",
        "branch": "",
        "summary": "Why predicting bank distress is hard, and the shape of the data problem.",
        "body": (
            "Bank failure is a rare, heavy-tailed event. In a typical quarter almost no banks "
            "fail; in a crisis quarter many do. That imbalance, not the modelling, is the "
            "central difficulty, and it shapes every methodological choice in the platform.\n\n"
            "## A rare-event, time-dependent problem\n"
            "Across the modelling panel the base rate of failure-within-four-quarters is well "
            "under one percent. At that rate a model that predicts 'no bank ever fails' is "
            "right more than 99% of the time, so accuracy is meaningless. The honest metrics "
            "are precision-recall area, recall at a fixed review budget, and calibration, all "
            "of which expose real rare-event performance. See "
            "[[Out-of-Time Evaluation]].\n\n"
            "## Why it is time-structured\n"
            "A bank is observed every quarter until it either fails or leaves the panel. That "
            "is a survival problem, not a snapshot classification: the same institution "
            "contributes many correlated rows over time, distress builds gradually, and the "
            "label depends on what happens in the future relative to each observation. Treating "
            "it as plain cross-sectional classification invites leakage and overstates "
            "performance. The framing used here is a discrete-time hazard model; see "
            "[[Problem Framing: Discrete-Time Hazard]].\n\n"
            "## Two distinct failure mechanisms\n"
            "Banks fail for credit reasons (loans go bad, capital erodes) and for "
            "liquidity/rate reasons (a deposit run against unrealised securities losses, as in "
            "2023). A model trained mostly on credit-driven failures will under-weight a "
            "rate-driven run. This limitation is stated openly rather than hidden; the rate-risk "
            "features (held-to-maturity and uninsured-deposit shares) are included precisely so "
            "the vulnerability is visible. See "
            "[[Capital, Unrealised Losses, and the 2023 Episode]]."
        ),
    },
    "How This Wiki Is Organized": {
        "cluster": "Introduction",
        "branch": "",
        "summary": "The structure of this encyclopedia and how to navigate it.",
        "body": (
            "This wiki is the reference documentation for FinLens. It is organised as a "
            "read-through, from concept to implementation, and every section in the left rail "
            "is a parent heading with its own articles.\n\n"
            "## The sections\n"
            "- **Introduction** orients a new reader: what the platform is and the problem it "
            "addresses.\n"
            "- **Business** covers the banking domain: the metrics, what failure records show, "
            "and the macroeconomic backdrop, plus honest statements of what the data cannot "
            "prove.\n"
            "- **Architecture** is the platform blueprint: the end-to-end design, the three "
            "surfaces, the medallion layers, and the tooling rationale.\n"
            "- **Data Engineering** is the build: sources, the warehouse, orchestration, "
            "quality and reconciliation, and serving/operations.\n"
            "- **AI Engineering** is the model: framing, features, labelling, evaluation, "
            "calibration, explainability, governance, drift, and serving.\n"
            "- **Reference** holds the glossary and external sources.\n\n"
            "## How to read it\n"
            "Each article is self-contained and cross-links to related ones. The data-engineering "
            "and AI-engineering articles document what is actually implemented, with the same "
            "facts the corresponding surface displays, so the wiki and the running product never "
            "disagree."
        ),
    },
    "Platform Architecture": {
        "cluster": "Architecture",
        "branch": "",
        "summary": "The end-to-end design: sources, warehouse, model, serving, and the contracts between them.",
        "body": (
            "FinLens is a layered data product. Public sources are landed verbatim, normalised "
            "into canonical tables, modelled into dashboard-ready marts, and served to three "
            "surfaces and a model. Each layer has a single responsibility and a contract with "
            "the next, so a change in one place has a bounded, traceable effect.\n\n"
            "## The end-to-end flow\n"
            "1. **Ingestion** pulls FDIC institution financials, the FDIC failed-bank list, and "
            "FRED macro series through free public APIs, and writes the raw responses to a "
            "bronze landing zone partitioned by source and ingestion date. Nothing is "
            "transformed at this stage; the landed artifact is the audit trail.\n"
            "2. **Transformation** runs as dbt models over the warehouse: bronze is shaped into "
            "silver canonical tables, silver into intermediate reusable logic, and intermediate "
            "into gold marts. Tests guard the boundaries.\n"
            "3. **Feature & label construction** builds the per-bank-quarter modelling panel "
            "(point-in-time features, leakage-safe labels) from the gold layer.\n"
            "4. **Model** trains a calibrated, monotone-constrained gradient-boosted hazard "
            "model, evaluates it strictly out-of-time, and registers it.\n"
            "5. **Serving** exposes the marts to the Streamlit surfaces and the model to a "
            "FastAPI endpoint; monitoring watches drift.\n\n"
            "## The contracts between layers\n"
            "Dashboards read **only** the gold layer, never raw or intermediate tables, so the "
            "presentation can never depend on an un-validated artifact (see "
            "[[Why Dashboards Read Gold Only]]). The model reads a frozen feature contract, so "
            "training and serving compute identical inputs. The warehouse layering follows the "
            "medallion pattern described in [[Bronze, Silver, Intermediate, Gold]].\n\n"
            "## Cost and reproducibility posture\n"
            "The entire system is designed to run at zero marginal infrastructure cost on free "
            "public data and an open-source stack, and to be reproducible from fixed seeds and "
            "pinned feature definitions. The tool choices and the reasons for them are in "
            "[[Tooling Choices and Their Rationale]]. The model side of this architecture is "
            "documented in the AI Engineering section, beginning with "
            "[[Problem Framing: Discrete-Time Hazard]]."
        ),
    },
    "The Three Surfaces": {
        "cluster": "Architecture",
        "branch": "",
        "summary": "Why the product is split into Business, Data Engineering, and AI Engineering views.",
        "body": (
            "The same underlying data and model serve three audiences with very different "
            "questions. Rather than force one dashboard to satisfy all of them, FinLens presents "
            "three surfaces over a shared warehouse.\n\n"
            "## Business\n"
            "The business surface reads the banking story for a risk, banking, or executive "
            "audience: industry stress over time, bank-failure forensics, the macroeconomic "
            "backdrop, and a live distress score for any bank. It answers 'what is happening and "
            "what does it mean', and it deliberately avoids engineering jargon.\n\n"
            "## Data Engineering\n"
            "The data-engineering surface exposes how every number is produced: source "
            "contracts, the warehouse and its layers, the orchestration, data-quality controls "
            "and reconciliation, and the serving/operations state. It answers 'can I trust this, "
            "and how is it built', and it is aimed at data-engineering and architecture "
            "reviewers.\n\n"
            "## AI Engineering\n"
            "The AI surface opens the model end to end: framing, the feature contract, "
            "out-of-time metrics with the supporting charts, explainability, drift, and "
            "governance, plus the analysis notebook. It answers 'is the model sound and "
            "defensible', and it is aimed at machine-learning and model-risk reviewers.\n\n"
            "## Why split, not segregate\n"
            "The split is by audience and question, not by walling off the data. All three "
            "surfaces draw from the same gold marts and the same model, so they cannot tell "
            "inconsistent stories. A reader who wants the full picture reads across all three; a "
            "reader with one role gets exactly the depth they need without wading through the "
            "rest. The platform blueprint that ties them together is "
            "[[Platform Architecture]]."
        ),
    },
    "Predictive Analytics on Currently Operating Banks": {
        "cluster": "AI Engineering",
        "branch": "Predictive Analytics",
        "summary": "How the live distress score is produced for any bank in the panel.",
        "body": (
            "The predictive surface scores a bank's most recent quarter in the panel with a "
            "calibrated probability of financial distress within four quarters, and explains the "
            "drivers behind that score.\n\n"
            "## What the score is\n"
            "The number is a calibrated probability, not a raw model output: a reported 5% means "
            "that, historically, bank-quarters scored near 5% failed within four quarters about "
            "5% of the time. Calibration is what makes the figure interpretable rather than just "
            "a ranking; see [[Probability Calibration]].\n\n"
            "## How to use it\n"
            "A user searches for a bank by name (no identifiers required), and the surface "
            "scores its latest available quarter from real Call Report features. The result "
            "shows the probability, the flag decision against a review threshold, and the top "
            "SHAP drivers with their direction. For defunct banks the most recent quarter in the "
            "panel is scored, which is useful for back-testing against a known outcome.\n\n"
            "## Honest scope\n"
            "The score reflects observable public financial ratios only. It does not see "
            "confidential supervisory information, deposit-flow data, or intraday liquidity, so "
            "it is context for a human reviewer, not an automated verdict. The way to read a "
            "single score responsibly is covered in [[How to Read a Stress Score]], and the "
            "machinery behind it in [[Engineering of the Predictive Pipeline]]."
        ),
    },
    "Engineering of the Predictive Pipeline": {
        "cluster": "AI Engineering",
        "branch": "Predictive Analytics",
        "summary": "The path from a bank's Call Report row to a calibrated, explained score.",
        "body": (
            "Scoring a bank reuses the exact training-time feature and model code, so the live "
            "score and the evaluated model are the same object.\n\n"
            "## The path of a request\n"
            "1. The bank's most recent panel row is retrieved by certificate number.\n"
            "2. The frozen feature contract computes the model inputs, identically to training, "
            "so there is no training/serving skew.\n"
            "3. The calibrated model produces a probability; the decision rule flags it against "
            "a review threshold.\n"
            "4. A SHAP explainer attributes the score to individual features for a "
            "validator-facing reason list.\n\n"
            "## Why it stays consistent\n"
            "Training and serving import the same feature module and the same monotone contract, "
            "and the served model is loaded from the registry, so what is scored in production is "
            "what was evaluated out-of-time. The hypothetical 'what-if' tool fills any unset "
            "feature with the panel median, so a slider experiment is always a complete, "
            "realistic bank rather than a mostly-empty vector. (Direct scoring of a real "
            "bank instead passes missing features through as NaN, which LightGBM handles "
            "natively; only the what-if path imputes.) The serving design is detailed in "
            "[[Serving the Model]]."
        ),
    },
    "How to Read a Stress Score": {
        "cluster": "AI Engineering",
        "branch": "Predictive Analytics",
        "summary": "Interpreting a single probability without over- or under-reading it.",
        "body": (
            "A stress score is a calibrated probability with real uncertainty around it. Reading "
            "it well means respecting both the number and its limits.\n\n"
            "## Read the probability, not a verdict\n"
            "A 12% score does not mean a bank will fail; it means that, among banks that have "
            "looked like this historically, roughly twelve in a hundred failed within four "
            "quarters. Most flagged banks do not fail. The score's job is triage: rank where a "
            "human reviewer should look first.\n\n"
            "## Read the drivers\n"
            "The reason list shows which features moved this particular score and in which "
            "direction. A low capital ratio pushing the score up is consistent with the model's "
            "rule that more capital lowers risk; the contribution is specific to this bank's "
            "values, not a contradiction of the contract. See "
            "[[Explainability with SHAP]].\n\n"
            "## Read the blind spots\n"
            "The model is strongest on credit-driven distress and weakest on a sudden "
            "liquidity/rate run, because such events are rare in the training history. A low "
            "score is not a clean bill of health on rate risk. Pair the score with the "
            "rate-risk features and the macroeconomic context before drawing a conclusion."
        ),
    },
}
