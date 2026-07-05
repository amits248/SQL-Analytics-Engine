-- ============================================================
-- Indexes added AFTER the "before" benchmark is captured, so
-- scripts/run_analysis.py can measure their real impact.
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_orders_customer_id  ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date   ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status       ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_order_items_order   ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_customers_region    ON customers(region);
CREATE INDEX IF NOT EXISTS idx_customers_channel   ON customers(acquisition_channel);
