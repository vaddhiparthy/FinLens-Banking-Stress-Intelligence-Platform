select
  series_id,
  date,
  value,
  metric_name
from {{ source('raw', 'fred_observations_raw') }}
