select
  quarter,
  net_income,
  roa,
  nim,
  problem_banks,
  asset_yield,
  funding_cost,
  noncurrent_rate,
  nco_rate,
  afs_losses,
  htm_losses
from {{ source('raw', 'fdic_qbp_raw') }}
