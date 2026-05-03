SELECT
  date_id,
  extract(year from date_id) as year,
  extract(month from date_id) as month,
  extract(day from date_id) as day
from (
  select cast('1990-01-01' as date) + cast(range as integer) as date_id
  from range(0, 14976)
)
