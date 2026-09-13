select
    order_id,
    cast(payment_sequential   as {{ dbt.type_int() }})   as payment_sequential,
    lower(trim(payment_type))                            as payment_type,
    cast(payment_installments as {{ dbt.type_int() }})   as payment_installments,
    cast(payment_value        as {{ dbt.type_float() }}) as payment_value
from {{ source('olist_raw', 'order_payments') }}
