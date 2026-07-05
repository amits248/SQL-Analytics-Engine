-- Customer Acquisition Cost (CAC) vs Lifetime Value (LTV) by acquisition channel.
-- Demonstrates: multi-CTE pipeline, aggregation across 3 tables, derived ratio metrics.

WITH customer_ltv AS (
    SELECT
        o.customer_id,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS ltv
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'completed'
    GROUP BY o.customer_id
),
channel_new_customers AS (
    SELECT
        acquisition_channel,
        strftime('%Y-%m', signup_date) AS signup_month,
        COUNT(*) AS new_customers
    FROM customers
    GROUP BY acquisition_channel, signup_month
),
channel_spend_monthly AS (
    SELECT channel, strftime('%Y-%m', month) AS month, SUM(spend_amount) AS spend
    FROM marketing_spend
    GROUP BY channel, month
),
channel_summary AS (
    SELECT
        cnc.acquisition_channel AS channel,
        SUM(csm.spend)          AS total_spend,
        SUM(cnc.new_customers)  AS customers_acquired
    FROM channel_new_customers cnc
    JOIN channel_spend_monthly csm
        ON csm.channel = cnc.acquisition_channel
        AND csm.month = cnc.signup_month
    GROUP BY cnc.acquisition_channel
)
SELECT
    cs.channel,
    cs.customers_acquired,
    ROUND(cs.total_spend, 2)                                   AS total_spend,
    ROUND(cs.total_spend * 1.0 / cs.customers_acquired, 2)      AS cac,
    ROUND(AVG(cl.ltv), 2)                                       AS avg_ltv,
    ROUND(AVG(cl.ltv) / (cs.total_spend * 1.0 / cs.customers_acquired), 2) AS ltv_cac_ratio
FROM channel_summary cs
JOIN customers c ON c.acquisition_channel = cs.channel
LEFT JOIN customer_ltv cl ON cl.customer_id = c.customer_id
GROUP BY cs.channel, cs.total_spend, cs.customers_acquired
ORDER BY ltv_cac_ratio DESC;
