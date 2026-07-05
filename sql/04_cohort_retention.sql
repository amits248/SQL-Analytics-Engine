-- Monthly cohort retention: for each signup-month cohort, how many customers
-- were still active N months later?
-- Demonstrates: multi-CTE composition, self-referencing date math, DISTINCT counts.

WITH first_purchase AS (
    SELECT customer_id, MIN(strftime('%Y-%m', order_date)) AS cohort_month
    FROM orders
    WHERE order_status = 'completed'
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id, strftime('%Y-%m', order_date) AS active_month
    FROM orders
    WHERE order_status = 'completed'
),
cohort_activity AS (
    SELECT
        fp.cohort_month,
        a.customer_id,
        (
            (CAST(strftime('%Y', a.active_month || '-01') AS INTEGER) * 12
             + CAST(strftime('%m', a.active_month || '-01') AS INTEGER))
            -
            (CAST(strftime('%Y', fp.cohort_month || '-01') AS INTEGER) * 12
             + CAST(strftime('%m', fp.cohort_month || '-01') AS INTEGER))
        ) AS month_number
    FROM first_purchase fp
    JOIN activity a ON a.customer_id = fp.customer_id
)
SELECT
    cohort_month,
    month_number,
    COUNT(DISTINCT customer_id) AS active_customers
FROM cohort_activity
GROUP BY cohort_month, month_number
ORDER BY cohort_month, month_number;
