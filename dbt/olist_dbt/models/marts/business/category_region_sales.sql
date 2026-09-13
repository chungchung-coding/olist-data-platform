-- Grain: month x category x customer state. Answers "which categories and region".
select
    cast({{ dbt.date_trunc('month', 'f.purchase_date') }} as date) as month_start,
    p.category,
    c.state                                                        as customer_state,
    count(*)                                                       as units_sold,
    count(distinct f.order_id)                                     as orders,
    sum(f.price)                                                   as revenue
from {{ ref('fact_order_items') }} f
left join {{ ref('dim_products') }}  p on f.product_id  = p.product_id
left join {{ ref('dim_customers') }} c on f.customer_id = c.customer_id
where f.order_status not in ('canceled', 'unavailable')
group by 1, 2, 3
