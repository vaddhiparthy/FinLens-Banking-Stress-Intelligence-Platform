SELECT
  f.bank_id,
  f.bank_name,
  f.state,
  f.year,
  f.assets_millions,
  f.acquirer
FROM {{ ref('fct_bank_failures') }} f
