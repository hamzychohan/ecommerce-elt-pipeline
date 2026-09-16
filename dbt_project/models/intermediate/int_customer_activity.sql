{{
    config(materialized='view')
}}

-- Computes per-customer activity windows used to detect churn.
-- A customer is "active" if they placed an order within the last `churn_inactive_days` days.

with order_lines as (
    select * from {{ ref('int_order_lines_enriched') }}
),

latest_order_per_customer as (
    select
        customer_id,
        max(order_purchase_timestamp) as last_order_at
    from order_lines
    group by customer_id
),

activity as (
    select
        customer_id,
        last_order_at,

        -- Days since the customer's most recent order (relative to current date at run time)
        datediff('day', last_order_at, current_date) as days_since_last_order,

        -- Active flag: within the inactivity threshold defined in dbt_project.yml
        case
            when datediff('day', last_order_at, current_date) <= {{ var('churn_inactive_days') }}
            then true
            else false
        end as is_active,

        -- Month of most recent order (for monthly cohort slicing)
        date_trunc('month', last_order_at) as last_active_month

    from latest_order_per_customer
)

select * from activity
