-- Single-customer order lookup -- the classic access pattern behind any
-- account page or support tool ("show me this customer's order history").
-- Run via scripts/run_analysis.py, parameterized over many customer_ids,
-- once BEFORE and once AFTER sql/02_indexes.sql is applied.
--
-- Without an index on orders.customer_id, SQLite's planner resolves this by
-- scanning all of order_items and joining back to orders row-by-row via the
-- primary key -- meaning EVERY lookup touches the full order_items table.
-- With idx_orders_customer_id + idx_order_items_order in place, it becomes
-- two direct B-tree index searches. See README.md for the measured result.

SELECT
    o.order_id,
    o.order_date,
    o.order_status,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS order_total
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.customer_id = ?
GROUP BY o.order_id, o.order_date, o.order_status
ORDER BY o.order_date;
