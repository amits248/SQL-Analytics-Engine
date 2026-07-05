-- RFM (Recency, Frequency, Monetary) segmentation.
-- Demonstrates: NTILE() quartile scoring, CASE-based rule bucketing, CTE chaining.

WITH rfm_base AS (
    SELECT
        o.customer_id,
        CAST(
            JULIANDAY((SELECT MAX(order_date) FROM orders WHERE order_status = 'completed'))
            - JULIANDAY(MAX(o.order_date))
            AS INTEGER
        ) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY o.customer_id
),
rfm_scored AS (
    SELECT
        customer_id, recency_days, frequency, monetary,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,   -- 4 = most recent
        NTILE(4) OVER (ORDER BY frequency ASC)      AS f_score,  -- 4 = most frequent
        NTILE(4) OVER (ORDER BY monetary ASC)       AS m_score   -- 4 = highest spend
    FROM rfm_base
)
SELECT
    customer_id, recency_days, frequency, monetary, r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 2                  THEN 'Loyal'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
        ELSE 'Potential'
    END AS segment
FROM rfm_scored;
