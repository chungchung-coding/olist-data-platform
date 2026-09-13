-- Logic check: an order marked delivered must carry a customer-delivery timestamp.
-- The public dataset has 8 known offenders, so we tolerate a handful (warn) rather than fail.
{{ config(severity='warn', warn_if='>0', error_if='>20') }}
select order_id from {{ ref('fact_orders') }}
where order_status = 'delivered' and delivered_to_customer_at is null
