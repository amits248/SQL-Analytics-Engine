-- ============================================================
-- Schema: retail-sql-analytics
-- 5 tables modeling a normalized e-commerce transaction system
-- ============================================================

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS marketing_spend;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    first_name          TEXT NOT NULL,
    last_name           TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    signup_date         DATE NOT NULL,
    region              TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL
);

CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    unit_price      REAL NOT NULL,
    unit_cost       REAL NOT NULL
);

CREATE TABLE orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date      DATE NOT NULL,
    order_status    TEXT NOT NULL CHECK (order_status IN ('completed', 'cancelled', 'returned')),
    payment_method  TEXT NOT NULL
);

CREATE TABLE order_items (
    order_item_id   INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      REAL NOT NULL,
    discount_pct    REAL NOT NULL DEFAULT 0
);

CREATE TABLE marketing_spend (
    spend_id        INTEGER PRIMARY KEY,
    channel         TEXT NOT NULL,
    month           DATE NOT NULL,
    spend_amount    REAL NOT NULL
);
