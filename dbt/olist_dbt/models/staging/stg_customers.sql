-- One row per customer_id (an order-level id). customer_unique_id identifies the person.
select
    customer_id,
    customer_unique_id,
    lpad(cast(customer_zip_code_prefix as {{ dbt.type_string() }}), 5, '0') as zip_code_prefix,
    lower(trim(customer_city))                                              as city,
    upper(trim(customer_state))                                             as state
from {{ source('olist_raw', 'customers') }}
