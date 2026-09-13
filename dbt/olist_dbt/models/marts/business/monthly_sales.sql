-- Grain: one row per calendar month. Core sales-trend mart.
select
    cast({{ dbt.date_trunc('month', 'purchase_date') }} as date)  as month_start,
    count(distinct order_id)                                      as orders,
    count(distinct customer_unique_id)                            as customers,
    sum(item_count)                                               as items_sold,
    sum(gross_merchandise_value)                                  as gross_merchandise_value,
    sum(freight_value)                                            as freight_value,
    sum(order_total_value)                                        as total_revenue,
    avg(order_total_value)                                        as avg_order_value,
    avg(review_score)                                             as avg_review_score,
    avg(case when is_late then 1.0 else 0.0 end)                  as late_delivery_rate
from {{ ref('fact_orders') }}
where order_status not in ('canceled', 'unavailable')
group by 1
