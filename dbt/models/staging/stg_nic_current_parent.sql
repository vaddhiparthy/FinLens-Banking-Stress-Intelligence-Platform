select
  rssd_id,
  fdic_certificate_number,
  institution_name,
  current_parent_rssd_id,
  current_parent_name
from {{ source('raw', 'nic_current_parent_raw') }}
