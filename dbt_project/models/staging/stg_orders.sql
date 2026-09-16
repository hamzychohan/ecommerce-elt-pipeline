{{
    config(materialized='view')
}}

with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        order_id                                                        as order_id,
        customer_id                                                     as customer_id,
        lower(trim(order_status))                                       as order_status,
        cast(order_purchase_timestamp as timestamp)                     as order_purchase_timestamp,
        cast(order_approved_at as timestamp)                            as order_approved_at,
        cast(order_delivered_carrier_date as timestamp)                 as order_delivered_carrier_date,
        cast(order_delivered_customer_date as timestamp)                as order_delivered_customer_date,
        cast(order_estimated_delivery_date as timestamp)                as order_estimated_delivery_date,
        cast(price_cents as bigint)                                     as price_cents,
        cast(freight_value_cents as bigint)                             as freight_value_cents,
        product_id                                                      as product_id,
        cast(order_item_id as smallint)                                 as order_item_id,
        seller_id                                                       as seller_id,
        _ingested_at                                                    as ingested_at,
        _batch_id                                                       as batch_id
    from source
),

deduped as (
    select *,
        row_number() over (
            partition by order_id, order_item_id
            order by ingested_at desc
        ) as _row_num
    from renamed
)

select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    price_cents,
    freight_value_cents,
    product_id,
    order_item_id,
    seller_id,
    ingested_at,
    batch_id
from deduped
where _row_num = 1
