# Data Flow

FinLens treats each source as a contract, not as an ad hoc file scrape.

## Source Intake

Approved active sources:

- FDIC BankFind
- FDIC QBP
- FRED / ALFRED
- NIC current parent metadata

Each source client is responsible for request construction, response handling, and conversion into a stable project-owned shape.

## Layering

| Layer | Role |
| --- | --- |
| Bronze | Preserve source payloads and raw extracts for traceability |
| Silver | Normalize names, dates, identifiers, codes, and source-specific structures |
| Gold | Publish dashboard-ready facts, metrics, and marts |

## Serving

The Streamlit dashboard reads curated analytical structures. It should not depend on raw source quirks. This keeps the user interface stable when source contracts change.

## Failure Mode

If a connector is missing credentials or a source contract is unavailable, FinLens reports the readiness gap instead of faking a successful pipeline run.
