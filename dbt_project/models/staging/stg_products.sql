{{
    config(materialized='view')
}}

with source as (
    select * from {{ source('raw', 'products') }}
),

renamed as (
    select
        product_id                                      as product_id,
        lower(trim(product_category_name))              as product_category_name,
        cast(product_name_length as smallint)           as product_name_length,
        cast(product_description_length as smallint)    as product_description_length,
        cast(product_photos_qty as smallint)            as product_photos_qty,
        cast(product_weight_g as int)                   as product_weight_g,
        cast(product_length_cm as smallint)             as product_length_cm,
        cast(product_height_cm as smallint)             as product_height_cm,
        cast(product_width_cm as smallint)              as product_width_cm,
        _ingested_at                                    as ingested_at,
        _batch_id                                       as batch_id
    from source
),

deduped as (
    select *,
        row_number() over (
            partition by product_id
            order by ingested_at desc
        ) as _row_num
    from renamed
)

select
    product_id,
    product_category_name,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    ingested_at,
    batch_id
from deduped
where _row_num = 1
