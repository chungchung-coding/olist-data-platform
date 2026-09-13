-- Money can never be negative in the fact table
select order_id from {{ ref('fact_orders') }}
where order_total_value < 0 or gross_merchandise_value < 0 or freight_value < 0
