SELECT
  bank_id,
  bank_name,
  city,
  state,
  cert,
  closing_date,
  year,
  assets_millions,
  acquirer
FROM {{ ref('stg_fdic_failed_banks') }}
