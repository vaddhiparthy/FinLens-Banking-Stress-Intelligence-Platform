-- Dependency-free composite-uniqueness test for the (cert, quarter) grain of the gold mart.
-- Passes when zero rows are returned (no duplicate bank-quarter).
select cert, quarter, count(*) as n
from {{ ref('bank_quarterly_risk_facts') }}
group by cert, quarter
having count(*) > 1
