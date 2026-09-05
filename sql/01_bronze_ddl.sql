-- ============================================================
-- BRONZE STAGING LAYER DDL (RAW MULTI-FORMAT INGESTION)
-- ============================================================

-- Raw Sales CSV Ingestion Table
CREATE TABLE IF NOT EXISTS bronze_sales_raw (
    transaction_id VARCHAR(50),
    timestamp VARCHAR(50),
    customer_id VARCHAR(50),
    product_id VARCHAR(50),
    store_id VARCHAR(50),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    payment_method VARCHAR(50),
    channel VARCHAR(50),
    ingested_at TIMESTAMP,
    source_file VARCHAR(255),
    batch_id VARCHAR(50),
    row_hash VARCHAR(32)
);

-- Raw Customers JSON Ingestion Table
CREATE TABLE IF NOT EXISTS bronze_customers_raw (
    customer_id VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    signup_date VARCHAR(50),
    loyalty_tier VARCHAR(50),
    city VARCHAR(100),
    web_sessions_count INTEGER,
    opt_in_marketing BOOLEAN,
    ingested_at TIMESTAMP,
    source_file VARCHAR(255),
    batch_id VARCHAR(50),
    row_hash VARCHAR(32)
);

-- Raw Inventory Excel Ingestion Table
CREATE TABLE IF NOT EXISTS bronze_inventory_raw (
    product_id VARCHAR(50),
    store_id VARCHAR(50),
    stock_on_hand INTEGER,
    reorder_point INTEGER,
    safety_stock INTEGER,
    last_restock_date VARCHAR(50),
    ingested_at TIMESTAMP,
    source_file VARCHAR(255),
    batch_id VARCHAR(50),
    row_hash VARCHAR(32)
);
