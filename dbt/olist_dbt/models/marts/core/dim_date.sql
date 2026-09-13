-- Calendar dimension covering the dataset window with a buffer either side.
with spine as (
    {{ dbt.date_spine(datepart='day', start_date="cast('2016-01-01' as date)", end_date="cast('2019-01-01' as date)") }}
)
select
    cast(date_day as date)                                       as date_day,
    cast(extract(year    from date_day) as {{ dbt.type_int() }}) as year,
    cast(extract(quarter from date_day) as {{ dbt.type_int() }}) as quarter,
    cast(extract(month   from date_day) as {{ dbt.type_int() }}) as month,
    cast({{ dbt.date_trunc('month', 'date_day') }} as date)      as month_start,
    cast(extract(day     from date_day) as {{ dbt.type_int() }}) as day_of_month,
    cast({{ dbt.date_trunc('week', 'date_day') }} as date)       as week_start
from spine
