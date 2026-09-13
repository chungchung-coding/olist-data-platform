-- Grain: one row per customer_unique_id (the real person). Lifetime value and
-- an RFM-style segment, which feeds the "customer segment" and
-- "gold members" questions in the sales-readiness case.
with delivered as (
    select *
    from {{ ref('fact_orders') }}
    where order_status not in ('canceled', 'unavailable')
),
per_customer as (
    select
        customer_unique_id,
        min(customer_state)                 as state,
        count(distinct order_id)            as order_count,
        sum(order_total_value)              as lifetime_value,
        sum(gross_merchandise_value)        as lifetime_merchandise_value,
        avg(order_total_value)              as avg_order_value,
        min(purchase_date)                  as first_purchase_date,
        max(purchase_date)                  as last_purchase_date,
        avg(review_score)                   as avg_review_score
    from delivered
    group by customer_unique_id
),
dataset_end as (
    select max(purchase_date) as max_date from delivered
),
scored as (
    select
        pc.*,
        {{ dbt.datediff('pc.last_purchase_date', 'd.max_date', 'day') }} as recency_days,
        ntile(4) over (order by {{ dbt.datediff('pc.last_purchase_date', 'd.max_date', 'day') }} desc) as r_score,
        ntile(4) over (order by pc.order_count)                          as f_score,
        ntile(4) over (order by pc.lifetime_value)                       as m_score
    from per_customer pc
    cross join dataset_end d
)
select
    *,
    case
        when m_score = 4 and r_score >= 3                    then 'gold'
        when m_score >= 3 and r_score >= 2                   then 'silver'
        when order_count > 1                                 then 'repeat'
        when r_score = 1                                     then 'lapsed'
        else 'standard'
    end as customer_segment
from scored
