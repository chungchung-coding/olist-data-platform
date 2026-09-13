select
    s.seller_id,
    s.zip_code_prefix,
    s.city,
    s.state,
    g.lat,
    g.lng
from {{ ref('stg_sellers') }} s
left join {{ ref('stg_geolocation') }} g on s.zip_code_prefix = g.zip_code_prefix
