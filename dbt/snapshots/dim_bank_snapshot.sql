{% snapshot dim_bank_snapshot %}
{{
  config(
    target_schema='snapshots',
    unique_key='bank_id',
    strategy='check',
    check_cols=['bank_name', 'state']
  )
}}

SELECT * FROM {{ ref('fct_bank_failures') }}

{% endsnapshot %}
