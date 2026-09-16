{{
    config(materialized='view')
}}

-- Aggregates order-level metrics per customer for use in the customers mart.

with order_lines as (
    select * from {{ ref('int_order_lines_enriched') }}
),

customer_agg as (
    select
        customer_id,

        count(distinct order_id)                        as total_orders,
        count(order_item_id)                            as total_items,

        sum(price_dollars)                              as lifetime_revenue_dollars,
        sum(freight_value_dollars)                      as lifetime_freight_dollars,
        sum(total_line_dollars)                         as lifetime_total_dollars,

        avg(price_dollars)                              as avg_order_value_dollars,

        min(order_purchase_timestamp)                   as first_order_at,
        max(order_purchase_timestamp)                   as last_order_at,

        -- Days between first and last order (0 for single-order customers)
        datediff(
            'day',
            min(order_purchase_timestamp),
            max(order_purchase_timestamp)
        )                                               as customer_tenure_days,

        sum(case when order_status = 'delivered' then 1 else 0 end)   as delivered_orders,
        sum(case when order_status = 'cancelled' then 1 else 0 end)   as cancelled_orders,
        sum(case when delivered_on_time then 1 else 0 end)            as on_time_deliveries

    from order_lines
    group by customer_id
)

select * from customer_agg
