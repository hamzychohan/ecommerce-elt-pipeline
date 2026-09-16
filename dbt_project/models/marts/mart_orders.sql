{{
    config(materialized='table')
}}

-- Final orders fact mart with denormalized product category and customer state.

with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select
        customer_id,
        customer_state,
        customer_city
    from {{ ref('stg_customers') }}
),

products as (
    select
        product_id,
        product_category_name
    from {{ ref('stg_products') }}
),

final as (
    select
        o.order_id,
        o.customer_id,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_approved_at,
        o.order_delivered_carrier_date,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,

        -- Denormalized dims for BI convenience
        c.customer_state,
        c.customer_city,
        p.product_category_name,

        -- Pricing
        {{ cents_to_dollars('o.price_cents') }}         as price_dollars,
        {{ cents_to_dollars('o.freight_value_cents') }} as freight_value_dollars,

        -- Derived
        {{ cents_to_dollars('o.price_cents') }}
            + {{ cents_to_dollars('o.freight_value_cents') }} as total_order_dollars,

        -- Delivery performance
        case
            when o.order_delivered_customer_date is not null
                 and o.order_delivered_customer_date <= o.order_estimated_delivery_date
            then true
            else false
        end as delivered_on_time,

        -- Date grain fields for partitioning/slicing
        cast(o.order_purchase_timestamp as date) as order_date,
        date_trunc('month', o.order_purchase_timestamp) as order_month

    from orders o
    left join customers c on o.customer_id = c.customer_id
    left join products p on o.product_id = p.product_id
)

select * from final
