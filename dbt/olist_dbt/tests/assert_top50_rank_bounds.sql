select * from {{ ref('top_products_monthly') }} where revenue_rank < 1 or revenue_rank > 50
