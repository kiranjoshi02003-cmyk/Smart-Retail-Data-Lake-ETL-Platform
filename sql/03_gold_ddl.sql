-- ============================================================
-- GOLD DATA MART & STAR SCHEMA DIMENSIONAL MODEL DDL
-- ============================================================

-- Dimension: Customers (With RFM & Spending Metrics)
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    loyalty_tier VARCHAR(50),
    city VARCHAR(100),
    total_orders INTEGER,
    total_spend DECIMAL(10,2),
    avg_order_value DECIMAL(10,2),
    last_purchase_date DATE,
    days_since_last_purchase INTEGER,
    rfm_segment VARCHAR(50)
);

-- Dimension: Products
CREATE TABLE IF NOT EXISTS dim_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(100),
    unit_cost DECIMAL(10,2),
    suggested_retail_price DECIMAL(10,2),
    profit_margin_pct DECIMAL(5,2),
    supplier VARCHAR(100)
);

-- Dimension: Stores
CREATE TABLE IF NOT EXISTS dim_stores (
    store_id VARCHAR(50) PRIMARY KEY,
    store_name VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(50),
    region VARCHAR(50),
    square_feet INTEGER,
    opened_year INTEGER
);

-- Fact: Sales Transactions
CREATE TABLE IF NOT EXISTS fact_sales (
    transaction_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP,
    transaction_date DATE,
    customer_id VARCHAR(50) REFERENCES dim_customers(customer_id),
    product_id VARCHAR(50) REFERENCES dim_products(product_id),
    store_id VARCHAR(50) REFERENCES dim_stores(store_id),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    unit_cost DECIMAL(10,2),
    gross_amount DECIMAL(10,2),
    cogs DECIMAL(10,2),
    net_profit DECIMAL(10,2),
    profit_margin_pct DECIMAL(5,2),
    payment_method VARCHAR(50),
    channel VARCHAR(50)
);

-- Fact: Inventory Snapshots & Health
CREATE TABLE IF NOT EXISTS fact_inventory_snapshot (
    product_id VARCHAR(50) REFERENCES dim_products(product_id),
    store_id VARCHAR(50) REFERENCES dim_stores(store_id),
    stock_on_hand INTEGER,
    reorder_point INTEGER,
    safety_stock INTEGER,
    reorder_status VARCHAR(50),
    unit_cost DECIMAL(10,2),
    inventory_valuation DECIMAL(12,2),
    PRIMARY KEY (product_id, store_id)
);
