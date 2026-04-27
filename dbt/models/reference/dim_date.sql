WITH dates AS (
  {{ dbt_date.get_base_dates(start_date="1990-01-01", end_date="2030-12-31") }}
)
SELECT
  date_day AS date_id,
  EXTRACT(YEAR FROM date_day) AS year,
  EXTRACT(MONTH FROM date_day) AS month,
  EXTRACT(DAY FROM date_day) AS day
FROM dates
