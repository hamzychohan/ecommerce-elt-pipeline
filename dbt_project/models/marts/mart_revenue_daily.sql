{{
    config(materialized='table')
}}

-- Daily revenue aggregation. Filters to revenue-generating order statuses only.

with order_lines as (
    select * from {{ ref('int_order_lines_enriched') }}
),

revenue_orders as (
    select *
    from order_lines
    where order_status in (
        {%- for status in var('revenue_statuses') %}
        '{{ status }}'{% if not loop.last %},{% endif %}
        {%- endfor %}
    )
),

daily as (
    select
        cast(order_purchase_timestamp as date)          as order_date,
        count(distinct order_id)                        as total_orders,
        count(order_item_id)                            as total_items,
        sum(price_dollars)                              as gross_revenue_dollars,
        sum(freight_value_dollars)                      as total_freight_dollars,
        sum(total_line_dollars)                         as total_revenue_with_freight_dollars,
        avg(price_dollars)                              as avg_order_value_dollars,
        count(distinct customer_id)                     as unique_customers

    from revenue_orders
    group by cast(order_purchase_timestamp as date)
)

select
    order_date,
    total_orders,
    total_items,
    gross_revenue_dollars,
    total_freight_dollars,
    total_revenue_with_freight_dollars,
    avg_order_value_dollars,
    unique_customers
from daily
order by order_date
