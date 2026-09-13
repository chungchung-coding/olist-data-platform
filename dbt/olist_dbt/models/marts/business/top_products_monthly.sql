-- Grain: product x month, restricted to the top 50 products of each month by
-- revenue. Directly answers "top 50 products for each month".
with product_month as (
    select
        cast({{ dbt.date_trunc('month', 'f.purchase_date') }} as date) as month_start,
        f.product_id,
        p.category,
        count(*)                as units_sold,
        count(distinct order_id) as orders,
        sum(f.price)            as revenue,
        sum(f.freight_value)    as freight
    from {{ ref('fact_order_items') }} f
    left join {{ ref('dim_products') }} p on f.product_id = p.product_id
    where f.order_status not in ('canceled', 'unavailable')
    group by 1, 2, 3
),
ranked as (
    select *,
        row_number() over (partition by month_start order by revenue desc, units_sold desc) as revenue_rank
    from product_month
)
select * from ranked where revenue_rank <= 50
