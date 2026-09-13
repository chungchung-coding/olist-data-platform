-- Grain: one row per order line (order_id, order_item_id). This is the
-- lowest-grain sales fact and the source for product / seller revenue.
select
    oi.order_id,
    oi.order_item_id,
    o.customer_id,
    oi.product_id,
    oi.seller_id,
    cast(o.purchased_at as date)               as purchase_date,
    o.order_status,
    oi.shipping_limit_at,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value                as total_item_value
from {{ ref('stg_order_items') }} oi
inner join {{ ref('stg_orders') }} o on oi.order_id = o.order_id
