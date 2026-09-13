-- The raw file contains duplicated (review_id, order_id) pairs and reviews
-- that span several orders. We keep the most recently answered review per order.
with typed as (
    select
        review_id,
        order_id,
        cast(review_score            as {{ dbt.type_int() }}) as review_score,
        review_comment_title,
        review_comment_message,
        cast(review_creation_date    as timestamp)            as review_created_at,
        cast(review_answer_timestamp as timestamp)            as review_answered_at
    from {{ source('olist_raw', 'order_reviews') }}
),
ranked as (
    select *,
        row_number() over (partition by order_id order by review_answered_at desc, review_id) as rn
    from typed
)
select
    review_id, order_id, review_score, review_comment_title, review_comment_message,
    review_created_at, review_answered_at
from ranked
where rn = 1
