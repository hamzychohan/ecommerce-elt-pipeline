-- Custom dbt test: fails (returns rows) if any day has negative gross revenue.
-- dbt test framework: a passing test returns 0 rows.

select
    order_date,
    gross_revenue_dollars
from {{ ref('mart_revenue_daily') }}
where gross_revenue_dollars < 0
