select
    seller_id,
    lpad(cast(seller_zip_code_prefix as {{ dbt.type_string() }}), 5, '0') as zip_code_prefix,
    lower(trim(seller_city))                                              as city,
    upper(trim(seller_state))                                             as state
from {{ source('olist_raw', 'sellers') }}
