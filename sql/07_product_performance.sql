-- Top 3 products by revenue within each category.
-- Demonstrates: RANK() partitioned window function, filtering on window output via CTE.

WITH product_revenue AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue,
        SUM(oi.quantity) AS units_sold
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.order_status = 'completed'
    GROUP BY p.product_id, p.product_name, p.category
),
ranked AS (
    SELECT
        *,
        RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_rank
    FROM product_revenue
)
SELECT category, product_name, revenue, units_sold, category_rank
FROM ranked
WHERE category_rank <= 3
ORDER BY category, category_rank;
