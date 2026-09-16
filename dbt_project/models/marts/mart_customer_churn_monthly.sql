{{
    config(materialized='table')
}}

-- Monthly customer churn rate.
-- Churn = customers active in month N-1 who did NOT place an order in month N.

with activity as (
    select * from {{ ref('int_customer_activity') }}
),

-- Build monthly active customer sets from order history
monthly_active as (
    select distinct
        customer_id,
        date_trunc('month', last_order_at) as active_month
    from activity
),

-- For each month, identify customers active in the prior month
prior_month_active as (
    select
        customer_id,
        active_month                                                        as prior_month,
        date_add(active_month, interval 1 month)                           as current_month
    from monthly_active
),

-- Customers who churned: were active last month but not this month
churned as (
    select
        p.current_month                                 as cohort_month,
        count(distinct p.customer_id)                   as churned_customers
    from prior_month_active p
    left join monthly_active m
        on  p.customer_id   = m.customer_id
        and p.current_month = m.active_month
    where m.customer_id is null
    group by p.current_month
),

-- Total active customers in the prior month (denominator for churn rate)
prior_active_counts as (
    select
        date_add(active_month, interval 1 month)   as cohort_month,
        count(distinct customer_id)          as active_customers_prior
    from monthly_active
    group by date_add(active_month, interval 1 month)
),

final as (
    select
        pac.cohort_month,
        pac.active_customers_prior,
        coalesce(c.churned_customers, 0)                as churned_customers,

        -- Churn rate as a decimal between 0 and 1
        case
            when pac.active_customers_prior = 0 then 0.0
            else round(
                cast(coalesce(c.churned_customers, 0) as double)
                / pac.active_customers_prior,
                4
            )
        end as churn_rate

    from prior_active_counts pac
    left join churned c on pac.cohort_month = c.cohort_month
)

select
    cohort_month,
    active_customers_prior,
    churned_customers,
    churn_rate
from final
order by cohort_month
