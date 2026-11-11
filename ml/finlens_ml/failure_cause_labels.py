"""Externally-sourced failure-cause labels for the out-of-time failed banks.

This replaces the author-defined threshold taxonomy as the GROUND TRUTH for failure cause.
Each label is the PRIMARY cause of failure as stated by an authoritative regulator source
(FDIC OIG Material Loss Review / Failed Bank Review / In-Depth Review, Treasury OIG, Federal
Reserve OIG, OCC, or FDIC press release), with the source URL and a one-line quote so every
classification is auditable and citable. This is the single change that converts the
decomposition from "my opinion" into an externally-grounded labelling.

Cause categories (mapped to financial-visibility for the decomposition):
  - fundamental_credit  -> credit_visible      (slow insolvency: asset quality / capital)
  - rate_liquidity      -> rate_liquidity_visible (uninsured-deposit run + securities losses)
  - fraud               -> invisible             (fraud / embezzlement / falsified records)

IMPORTANT nuance, preserved deliberately: cause != financial visibility. Some fraud failures
were financially VISIBLE in the accounting (e.g. insider bad loans show up as noncurrent),
while others left no signal (off-book deposits, wired-out funds). The label here is the
regulator-stated CAUSE; the decomposition and the label-source sensitivity test (C5) quantify
where cause-based labels and threshold-based visibility labels agree and diverge.

Provenance: compiled from the cited regulator documents below (18 of 19 banks have a primary
regulator source, counting the FDIC FAQ for Metropolitan Capital; Community Bank & Trust - West
Georgia is the one news-only case, no OIG report yet). The __main__ counter (source_type !=
"news") reports the same 18/19.
"""

from __future__ import annotations

import pandas as pd

# cert -> record. cause in {fundamental_credit, rate_liquidity, fraud}.
FAILURE_CAUSES: dict[int, dict] = {
    21111: {"name": "City National Bank of New Jersey", "failure_year": 2019,
            "cause": "fundamental_credit", "confidence": "high", "source_type": "oig_mlr",
            "source_url": "https://oig.treasury.gov/system/files/2020-12/OIG-20-039.pdf",
            "quote": "Severe BSA/AML deficiencies and high noninterest expense produced "
                     "operating losses that depleted capital."},
    58112: {"name": "Louisa Community Bank", "failure_year": 2019,
            "cause": "fundamental_credit", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://www.fdicoig.gov/sites/default/files/reports/2022-08/FBR-20-001.pdf",
            "quote": "Dysfunctional board/management, weak controls, operational and credit "
                     "losses eroded capital and stressed liquidity."},
    58317: {"name": "Resolute Bank", "failure_year": 2019,
            "cause": "fundamental_credit", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://oig.treasury.gov/system/files/2020-12/OIG-20-038.pdf",
            "quote": "Mortgage-banking pivot without a valid capital plan; operating losses, "
                     "critically deficient earnings/asset-quality/capital."},
    10716: {"name": "The Enloe State Bank", "failure_year": 2019,
            "cause": "fraud", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://www.fdicoig.gov/sites/default/files/reports/2022-08/FBR-19-001.pdf",
            "quote": "Closed due to insider abuse and fraud by former officers; large number of "
                     "irregular/fraudulent loans depleted capital."},
    15426: {"name": "Almena State Bank", "failure_year": 2020,
            "cause": "fundamental_credit", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://www.fdicoig.gov/sites/default/files/reports/2022-08/FBR-21-003.pdf",
            "quote": "Capital/asset-quality issues from aggressive growth, hazardous lending, "
                     "inadequate oversight; no fraud significantly contributed."},
    18265: {"name": "Ericson State Bank", "failure_year": 2020,
            "cause": "fraud", "confidence": "medium",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://fdicoig.gov/sites/default/files/reports/2022-08/FBR_20_002.pdf",
            "quote": "Dominant CEO did undocumented related-entity lending over the legal limit; "
                     "former president pleaded guilty to bank fraud (DOJ)."},
    16748: {"name": "First City Bank of Florida", "failure_year": 2020,
            "cause": "fundamental_credit", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://www.fdicoig.gov/sites/default/files/reports/2022-08/FBR-21-002.pdf",
            "quote": "Longstanding capital/asset-quality problems since 2009; weak lending plus "
                     "local CRE deterioration left it critically undercapitalized."},
    14361: {"name": "The First State Bank", "failure_year": 2020,
            "cause": "fundamental_credit", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://www.fdicoig.gov/reports/bank-failures/failed-bank-review-first-state-bank-barboursville-west-virginia",
            "quote": "Capital and asset-quality issues since 2015 left capital too low to "
                     "continue operating; no fraud cited."},
    8758: {"name": "Citizens Bank (Sac City)", "failure_year": 2023,
           "cause": "fundamental_credit", "confidence": "high",
           "source_type": "oig_failed_bank_review",
           "source_url": "https://www.fdicoig.gov/sites/default/files/reports/2024-03/Citizens%20Bank%20Failed%20Bank%20Review%20Memorandum_0.pdf",
           "quote": "'Lax lending practices'; trucking loans 43% of the portfolio without risk "
                    "management or board oversight, overdrafts beyond the legal lending limit."},
    59017: {"name": "First Republic Bank", "failure_year": 2023,
            "cause": "rate_liquidity", "confidence": "high", "source_type": "fdic_pr",
            "source_url": "https://www.fdic.gov/news/press-releases/2023/pr23073a.pdf",
            "quote": "Post-SVB run; overreliance on uninsured deposits plus rate-driven "
                     "fair-value declines on long-duration assets, liquidity loss."},
    25851: {"name": "Heartland Tri-State Bank", "failure_year": 2023,
            "cause": "fraud", "confidence": "high", "source_type": "fed",
            "source_url": "https://oig.federalreserve.gov/reports/board-material-loss-review-heartland-tri-state-bank-feb2024.pdf",
            "quote": "CEO wired ~$47.1M to crypto wallets in a 'pig-butchering' scam; control "
                     "breakdowns enabled the fraudulent transfers."},
    57053: {"name": "Signature Bank", "failure_year": 2023,
            "cause": "rate_liquidity", "confidence": "high", "source_type": "fdic_pr",
            "source_url": "https://www.fdic.gov/news/press-releases/2023/pr23030.html",
            "quote": "Heavy reliance on uninsured deposits and weak liquidity risk management; "
                     "deposit run from SVB/Silvergate contagion."},
    24735: {"name": "Silicon Valley Bank", "failure_year": 2023,
            "cause": "rate_liquidity", "confidence": "high", "source_type": "fed",
            "source_url": "https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf",
            "quote": "Mismanaged interest-rate and liquidity risk; rate-driven unrealized "
                     "securities losses plus ~94% uninsured deposits triggered a run."},
    27332: {"name": "Republic First Bank", "failure_year": 2024,
            "cause": "fundamental_credit", "confidence": "high", "source_type": "oig_mlr",
            "source_url": "https://www.fdicoig.gov/sites/default/files/reports/2024-11/EVAL-2025-01%20Material%20Loss%20Review%20of%20Republic%20First%20Bank.pdf",
            "quote": "Dysfunctional board/management and related-party transactions prevented "
                     "capital planning; slow capital/earnings erosion, not a run or theft."},
    4134: {"name": "The First National Bank of Lindsay", "failure_year": 2024,
           "cause": "fraud", "confidence": "high", "source_type": "occ",
           "source_url": "https://www.occ.treas.gov/news-issuances/news-releases/2024/nr-occ-2024-119.html",
           "quote": "'False and deceptive bank records and other information suggesting fraud' "
                    "revealed capital depletion; former president indicted (DOJ)."},
    28611: {"name": "Pulaski Savings Bank", "failure_year": 2025,
            "cause": "fraud", "confidence": "high",
            "source_type": "oig_failed_bank_review",
            "source_url": "https://www.fdicoig.gov/news/summary-announcements/failed-bank-review-pulaski-savings-bank-chicago-il",
            "quote": "Impaired capital; >=$20.7M deposits off the core system with no matching "
                     "assets; suspected fraud drove the 62% loss rate."},
    5520: {"name": "The Santa Anna National Bank", "failure_year": 2025,
           "cause": "fraud", "confidence": "high", "source_type": "occ",
           "source_url": "https://www.occ.gov/news-issuances/news-releases/2025/nr-occ-2025-62.html",
           "quote": "Substantial dissipation of assets from unsafe practices; FDIC stated "
                    "suspected fraud contributed to the failure and elevated loss."},
    25796: {"name": "Community Bank and Trust - West Georgia", "failure_year": 2026,
            "cause": "fundamental_credit", "confidence": "low", "source_type": "news",
            "source_url": "https://bankingjournal.aba.com/2026/05/community-bank-and-trust-west-georgia-closed-by-regulators/",
            "quote": "Fed Atlanta inspection + enforcement cited growth strategy, board "
                     "oversight, capital, and affiliate-transaction deficiencies; no OIG yet."},
    57488: {"name": "Metropolitan Capital Bank & Trust", "failure_year": 2026,
            "cause": "fundamental_credit", "confidence": "medium", "source_type": "fdic_pr",
            "source_url": "https://www.fdic.gov/bank-failures/frequently-asked-questions-metropolitan-capital-bank-trust-chicago-il",
            "quote": "Unsafe/unsound conditions and impaired capital tied to a long-troubled CRE "
                     "loan and a prior consent order over substandard lending."},
}

# cause -> the financial-visibility class used by the decomposition
CAUSE_TO_VISIBILITY = {
    "fundamental_credit": "credit_visible",
    "rate_liquidity": "rate_liquidity_visible",
    "fraud": "invisible",
}


def load_failure_causes() -> pd.DataFrame:
    """Return the externally-sourced cause table, one row per CERT, with the mapped
    visibility class. This is the ground-truth labelling for the decomposition."""
    rows = []
    for cert, r in FAILURE_CAUSES.items():
        rows.append({"cert": int(cert), **r,
                     "visibility": CAUSE_TO_VISIBILITY[r["cause"]]})
    return pd.DataFrame(rows).sort_values(["failure_year", "name"]).reset_index(drop=True)


def cause_for_cert(cert: int) -> str | None:
    r = FAILURE_CAUSES.get(int(cert))
    return r["cause"] if r else None


def visibility_for_cert(cert: int) -> str | None:
    r = FAILURE_CAUSES.get(int(cert))
    return CAUSE_TO_VISIBILITY[r["cause"]] if r else None


if __name__ == "__main__":
    df = load_failure_causes()
    print(df[["cert", "name", "failure_year", "cause", "visibility", "confidence",
              "source_type"]].to_string(index=False))
    print("\ncause counts:", df["cause"].value_counts().to_dict())
    print("primary-regulator sourced:",
          int((df["source_type"] != "news").sum()), "/", len(df))
