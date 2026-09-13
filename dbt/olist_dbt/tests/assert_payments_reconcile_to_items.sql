-- Payment total should approximately equal items + freight for delivered orders.
-- Vouchers/rounding create small gaps; anything over R$1 on >1% of orders is a problem.
{{ config(severity='warn', warn_if='>0', error_if='>1000') }}
select order_id, order_total_value, payment_value
from {{ ref('fact_orders') }}
where order_status = 'delivered'
  and payment_value is not null
  and abs(payment_value - order_total_value) > 1.0
