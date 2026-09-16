{{
    config(materialized='view')
}}

-- Joins order line items with their product details and applies unit-price conversions.

with orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

enriched as (
    select
        o.order_id,
        o.order_item_id,
        o.customer_id,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        o.seller_id,
        o.price_cents,
        o.freight_value_cents,

        -- Convert cents → dollars using the cents_to_dollars macro
        {{ cents_to_dollars('o.price_cents') }}         as price_dollars,
        {{ cents_to_dollars('o.freight_value_cents') }} as freight_value_dollars,

        -- Derived total line value
        {{ cents_to_dollars('o.price_cents') }}
            + {{ cents_to_dollars('o.freight_value_cents') }} as total_line_dollars,

        -- Product dimension
        p.product_id,
        p.product_category_name,
        p.product_weight_g,

        -- Delivery performance flag
        case
            when o.order_delivered_customer_date is not null
                 and o.order_delivered_customer_date <= o.order_estimated_delivery_date
            then true
            else false
        end as delivered_on_time

    from orders o
    left join products p
        on o.product_id = p.product_id
)

select * from enriched
