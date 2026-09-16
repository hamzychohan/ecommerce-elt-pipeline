{{
    config(materialized='table')
}}

-- Final customers dimension mart combining profile and behavioral data.

with customers as (
    select * from {{ ref('stg_customers') }}
),

customer_orders as (
    select * from {{ ref('int_customer_orders') }}
),

customer_activity as (
    select * from {{ ref('int_customer_activity') }}
),

final as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.customer_zip_code_prefix,
        c.customer_city,
        c.customer_state,

        -- Order behavioral metrics
        coalesce(co.total_orders, 0)                as total_orders,
        coalesce(co.total_items, 0)                 as total_items,
        coalesce(co.lifetime_revenue_dollars, 0)    as lifetime_revenue_dollars,
        coalesce(co.lifetime_total_dollars, 0)      as lifetime_total_dollars,
        coalesce(co.avg_order_value_dollars, 0)     as avg_order_value_dollars,
        co.first_order_at,
        co.last_order_at,
        coalesce(co.customer_tenure_days, 0)        as customer_tenure_days,
        coalesce(co.delivered_orders, 0)            as delivered_orders,
        coalesce(co.cancelled_orders, 0)            as cancelled_orders,

        -- Activity / churn signals
        ca.last_order_at                            as last_active_at,
        coalesce(ca.days_since_last_order, null)    as days_since_last_order,
        coalesce(ca.is_active, false)               as is_active

    from customers c
    left join customer_orders co
        on c.customer_id = co.customer_id
    left join customer_activity ca
        on c.customer_id = ca.customer_id
)

select * from final
