with products as (
    select
        product_id,
        product_category_name,
        cast(product_name_lenght        as {{ dbt.type_int() }})   as product_name_length,
        cast(product_description_lenght as {{ dbt.type_int() }})   as product_description_length,
        cast(product_photos_qty         as {{ dbt.type_int() }})   as product_photos_qty,
        cast(product_weight_g           as {{ dbt.type_float() }}) as product_weight_g,
        cast(product_length_cm          as {{ dbt.type_float() }}) as product_length_cm,
        cast(product_height_cm          as {{ dbt.type_float() }}) as product_height_cm,
        cast(product_width_cm           as {{ dbt.type_float() }}) as product_width_cm
    from {{ source('olist_raw', 'products') }}
),
translation as (
    select product_category_name, product_category_name_english
    from {{ source('olist_raw', 'product_category_translation') }}
)
select
    p.product_id,
    p.product_category_name                                                   as category_pt,
    coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    p.product_length_cm * p.product_height_cm * p.product_width_cm            as product_volume_cm3
from products p
left join translation t on p.product_category_name = t.product_category_name
