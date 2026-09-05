-- ============================================================
-- SMART RETAIL BUSINESS KPI & ANALYTICAL SQL QUERIES
-- ============================================================

-- 1. Monthly Revenue, Profit & Margin Performance (MoM)
SELECT 
    STRFTIME('%Y-%m', transaction_date) AS sales_month,
    COUNT(DISTINCT transaction_id) AS total_orders,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(gross_amount), 2) AS gross_revenue,
    ROUND(SUM(net_profit), 2) AS net_profit,
    ROUND(SUM(net_profit) / SUM(gross_amount) * 100, 2) AS overall_margin_pct,
    ROUND(AVG(gross_amount), 2) AS avg_order_value
FROM fact_sales
GROUP BY sales_month
ORDER BY sales_month ASC;

-- 2. Customer RFM Segmentation Summary
SELECT 
    rfm_segment,
    COUNT(customer_id) AS customer_count,
    ROUND(AVG(total_spend), 2) AS avg_lifetime_spend,
    ROUND(SUM(total_spend), 2) AS segment_total_spend,
    ROUND(AVG(days_since_last_purchase), 1) AS avg_recency_days
FROM dim_customers
GROUP BY rfm_segment
ORDER BY segment_total_spend DESC;

-- 3. Inventory Stock-Out & Reorder Warning Matrix
SELECT 
    p.category,
    p.product_name,
    s.store_name,
    s.region,
    i.stock_on_hand,
    i.reorder_point,
    i.safety_stock,
    (i.reorder_point - i.stock_on_hand) AS deficit_quantity,
    i.inventory_valuation
FROM fact_inventory_snapshot i
JOIN dim_products p ON i.product_id = p.product_id
JOIN dim_stores s ON i.store_id = s.store_id
WHERE i.reorder_status = 'REORDER_NEEDED'
ORDER BY deficit_quantity DESC;

-- 4. Top 10 High Profit Margin Products
SELECT 
    p.product_id,
    p.product_name,
    p.category,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.gross_amount), 2) AS total_revenue,
    ROUND(SUM(f.net_profit), 2) AS total_profit,
    p.profit_margin_pct AS catalog_margin_pct
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category, p.profit_margin_pct
ORDER BY total_profit DESC
LIMIT 10;

-- 5. Store & Regional Profitability Matrix
SELECT 
    st.region,
    st.store_name,
    st.city,
    COUNT(DISTINCT f.transaction_id) AS transaction_count,
    ROUND(SUM(f.gross_amount), 2) AS store_revenue,
    ROUND(SUM(f.net_profit), 2) AS store_profit,
    ROUND(SUM(f.net_profit) / SUM(f.gross_amount) * 100, 2) AS store_margin_pct
FROM fact_sales f
JOIN dim_stores st ON f.store_id = st.store_id
GROUP BY st.region, st.store_name, st.city
ORDER BY store_revenue DESC;
