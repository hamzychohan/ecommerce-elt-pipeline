{{
    config(materialized='view')
}}

with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        customer_id                                     as customer_id,
        customer_unique_id                              as customer_unique_id,
        cast(customer_zip_code_prefix as varchar(10))   as customer_zip_code_prefix,
        trim(lower(customer_city))                      as customer_city,
        upper(trim(customer_state))                     as customer_state,
        _ingested_at                                    as ingested_at,
        _batch_id                                       as batch_id
    from source
),

deduped as (
    select *,
        row_number() over (
            partition by customer_id
            order by ingested_at desc
        ) as _row_num
    from renamed
)

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    ingested_at,
    batch_id
from deduped
where _row_num = 1
