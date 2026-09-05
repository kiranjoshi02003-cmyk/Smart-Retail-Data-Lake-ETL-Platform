-- ============================================================
-- SILVER CLEANED & DOMAIN NORMALIZED LAYER DDL
-- ============================================================

CREATE TABLE IF NOT EXISTS silver_sales (
    transaction_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP,
    transaction_date DATE,
    transaction_hour INTEGER,
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    store_id VARCHAR(50),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    gross_amount DECIMAL(10,2),
    payment_method VARCHAR(50),
    channel VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS silver_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    signup_date DATE,
    loyalty_tier VARCHAR(50),
    city VARCHAR(100),
    web_sessions_count INTEGER,
    opt_in_marketing BOOLEAN
);

CREATE TABLE IF NOT EXISTS silver_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(100),
    unit_cost DECIMAL(10,2),
    suggested_retail_price DECIMAL(10,2),
    profit_margin_pct DECIMAL(5,2),
    supplier VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS silver_inventory (
    product_id VARCHAR(50),
    store_id VARCHAR(50),
    stock_on_hand INTEGER,
    reorder_point INTEGER,
    safety_stock INTEGER,
    reorder_status VARCHAR(50),
    PRIMARY KEY (product_id, store_id)
);

CREATE TABLE IF NOT EXISTS silver_validation_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    layer VARCHAR(50),
    dataset VARCHAR(100),
    rule VARCHAR(100),
    severity VARCHAR(20),
    affected_records INTEGER,
    details TEXT
);
