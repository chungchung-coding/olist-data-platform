-- Grain: seller. Used to identify sellers to prepare for stronger demand.
with items as (
    select
        f.seller_id,
        count(*)                       as units_sold,
        count(distinct f.order_id)     as orders,
        sum(f.price)                   as revenue,
        count(distinct f.product_id)   as distinct_products
    from {{ ref('fact_order_items') }} f
    where f.order_status not in ('canceled', 'unavailable')
    group by f.seller_id
),
handling as (
    select
        f.seller_id,
        avg(o.seller_handling_days)                       as avg_seller_handling_days,
        avg(case when o.is_late then 1.0 else 0.0 end)    as late_rate,
        avg(o.review_score)                               as avg_review_score
    from {{ ref('fact_order_items') }} f
    join {{ ref('fact_orders') }} o on f.order_id = o.order_id
    where o.order_status = 'delivered'
    group by f.seller_id
)
select
    s.seller_id,
    s.state as seller_state,
    s.city  as seller_city,
    i.units_sold, i.orders, i.revenue, i.distinct_products,
    h.avg_seller_handling_days, h.late_rate, h.avg_review_score
from {{ ref('dim_sellers') }} s
left join items    i on s.seller_id = i.seller_id
left join handling h on s.seller_id = h.seller_id
