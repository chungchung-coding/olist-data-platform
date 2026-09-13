select
    order_id,
    cast(order_item_id       as {{ dbt.type_int() }})   as order_item_id,
    product_id,
    seller_id,
    cast(shipping_limit_date as timestamp)              as shipping_limit_at,
    cast(price               as {{ dbt.type_float() }}) as price,
    cast(freight_value       as {{ dbt.type_float() }}) as freight_value
from {{ source('olist_raw', 'order_items') }}
