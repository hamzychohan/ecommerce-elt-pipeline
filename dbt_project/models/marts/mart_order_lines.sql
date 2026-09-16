{{
    config(materialized='table')
}}

-- Granular order-line fact mart. One row per order × item.

with enriched as (
    select * from {{ ref('int_order_lines_enriched') }}
),

final as (
    select
        order_id,
        order_item_id,
        customer_id,
        product_id,
        product_category_name,
        seller_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_customer_date,
        order_estimated_delivery_date,

        -- Pricing
        price_cents,
        freight_value_cents,
        price_dollars,
        freight_value_dollars,
        total_line_dollars,

        -- Physical attributes
        product_weight_g,

        -- Delivery flag
        delivered_on_time,

        -- Date grain
        cast(order_purchase_timestamp as date)          as order_date,
        date_trunc('month', order_purchase_timestamp)   as order_month
    from enriched
)

select * from final
