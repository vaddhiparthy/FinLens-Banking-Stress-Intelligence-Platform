select
  bank_id,
  bank_name,
  city,
  state,
  cert,
  acquirer,
  closing_date,
  year,
  assets_millions
from {{ source('raw', 'fdic_failed_banks_raw') }}
