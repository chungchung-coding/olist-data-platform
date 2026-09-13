-- Grain: one row per customer_id (Olist issues a new customer_id per order;
-- customer_unique_id is the stable person key and is carried for segmentation).
select
    c.customer_id,
    c.customer_unique_id,
    c.zip_code_prefix,
    c.city,
    c.state,
    g.lat,
    g.lng
from {{ ref('stg_customers') }} c
left join {{ ref('stg_geolocation') }} g on c.zip_code_prefix = g.zip_code_prefix
