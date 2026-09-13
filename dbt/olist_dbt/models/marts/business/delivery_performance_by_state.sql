-- Grain: customer state. The delivery-readiness case: where are deliveries
-- slow or late, and which leg (seller handling vs carrier) drives it.
select
    customer_state,
    count(*)                                              as delivered_orders,
    avg(actual_delivery_days)                             as avg_delivery_days,
    avg(estimated_delivery_days)                          as avg_estimated_days,
    avg(case when is_late then 1.0 else 0.0 end)          as late_rate,
    avg(case when is_late then delivery_delay_days end)   as avg_days_late_when_late,
    avg(seller_handling_days)                             as avg_seller_handling_days,
    avg(carrier_transit_days)                             as avg_carrier_transit_days,
    avg(freight_value)                                    as avg_freight_value,
    avg(review_score)                                     as avg_review_score
from {{ ref('fact_orders') }}
where order_status = 'delivered'
  and delivered_to_customer_at is not null
group by customer_state
