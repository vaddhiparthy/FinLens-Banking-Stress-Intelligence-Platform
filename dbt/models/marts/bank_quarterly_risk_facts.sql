-- Capstone-1 gold mart: per-bank-quarter risk facts. Grain: (cert, quarter).
-- Sourced from the ML feature panel (same DuckDB), exposing the CAMELS-aligned risk ratios
-- the downstream model and dashboards consume. tier1_rwa_ratio is intentionally nullable
-- post-2020Q1 (Community Bank Leverage Ratio election; see docs/ml/CEILING_BACKLOG.md / C4),
-- so it is NOT asserted not_null; the Great Expectations suite tracks its null-rate instead.
select
    cast(cert as bigint)            as cert,
    quarter                         as quarter,
    noncurrent_to_loans             as noncurrent_to_loans,
    nco_to_loans                    as nco_to_loans,
    tier1_rwa_ratio                 as tier1_rwa_ratio,
    tier1_leverage                  as tier1_leverage,
    equity_to_assets                as equity_to_assets,
    roa                             as roa
from {{ source('ml', 'training_dataset') }}
where cert is not null
  and quarter is not null
