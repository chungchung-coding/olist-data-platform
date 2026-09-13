-- Grain: one row per order. Aggregates items, payments and the review, and
-- derives the delivery-performance measures used by the delivery-readiness case.
with items as (
    select
        order_id,
        count(*)            as item_count,
        sum(price)          as gross_merchandise_value,
        sum(freight_value)  as freight_value,
        sum(price + freight_value) as order_total_value
    from {{ ref('stg_order_items') }}
    group by order_id
),
payments as (
    select
        order_id,
        sum(payment_value)          as payment_value,
        max(payment_installments)   as max_installments,
        min(payment_type)           as primary_payment_type
    from {{ ref('stg_order_payments') }}
    group by order_id
)
select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.state                                                      as customer_state,
    o.order_status,
    o.purchased_at,
    cast(o.purchased_at as date)                                 as purchase_date,
    o.approved_at,
    o.delivered_to_carrier_at,
    o.delivered_to_customer_at,
    o.estimated_delivery_at,
    coalesce(i.item_count, 0)                                    as item_count,
    coalesce(i.gross_merchandise_value, 0)                       as gross_merchandise_value,
    coalesce(i.freight_value, 0)                                 as freight_value,
    coalesce(i.order_total_value, 0)                             as order_total_value,
    p.payment_value,
    p.max_installments,
    p.primary_payment_type,
    r.review_score,
    {{ dbt.datediff('o.purchased_at', 'o.delivered_to_customer_at', 'day') }}   as actual_delivery_days,
    {{ dbt.datediff('o.purchased_at', 'o.estimated_delivery_at', 'day') }}      as estimated_delivery_days,
    {{ dbt.datediff('o.estimated_delivery_at', 'o.delivered_to_customer_at', 'day') }} as delivery_delay_days,
    case
        when o.delivered_to_customer_at is null then null
        when o.delivered_to_customer_at > o.estimated_delivery_at then true
        else false
    end                                                          as is_late,
    {{ dbt.datediff('o.purchased_at', 'o.approved_at', 'day') }}                as approval_days,
    {{ dbt.datediff('o.approved_at', 'o.delivered_to_carrier_at', 'day') }}     as seller_handling_days,
    {{ dbt.datediff('o.delivered_to_carrier_at', 'o.delivered_to_customer_at', 'day') }} as carrier_transit_days
from {{ ref('stg_orders') }} o
left join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
left join items    i on o.order_id = i.order_id
left join payments p on o.order_id = p.order_id
left join {{ ref('stg_order_reviews') }} r on o.order_id = r.order_id
