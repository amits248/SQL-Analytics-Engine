-- Monthly revenue, month-over-month growth %, and a 3-month rolling average.
-- Demonstrates: CTE, LAG() window function, framed window (ROWS BETWEEN).

WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY month
)
SELECT
    month,
    revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0),
        2
    ) AS mom_growth_pct,
    ROUND(
        AVG(revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
        2
    ) AS rolling_3mo_avg_revenue
FROM monthly_revenue
ORDER BY month;
