-- The raw file has ~1M rows (one per lat/lng sample). We collapse it to one
-- centroid per zip prefix, which is the grain customers and sellers join on.
with typed as (
    select
        lpad(cast(geolocation_zip_code_prefix as {{ dbt.type_string() }}), 5, '0') as zip_code_prefix,
        cast(geolocation_lat as {{ dbt.type_float() }})                         as lat,
        cast(geolocation_lng as {{ dbt.type_float() }})                         as lng,
        upper(trim(geolocation_state))                                          as state
    from {{ source('olist_raw', 'geolocation') }}
    -- keep only coordinates inside Brazil's bounding box (removes typos)
    where cast(geolocation_lat as {{ dbt.type_float() }}) between -34 and 6
      and cast(geolocation_lng as {{ dbt.type_float() }}) between -74 and -34
)
select
    zip_code_prefix,
    avg(lat)      as lat,
    avg(lng)      as lng,
    min(state)    as state,
    count(*)      as sample_count
from typed
group by zip_code_prefix
