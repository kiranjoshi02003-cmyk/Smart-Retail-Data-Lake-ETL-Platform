import logging
import pandas as pd
import numpy as np
from datetime import datetime
from etl.db import engine, logger
from etl.validation import DataQualityValidator

class MedallionTransformer:
    """Orchestrates Silver cleansing/normalization and Gold star-schema data mart transformations."""

    def __init__(self, validator: DataQualityValidator):
        self.validator = validator

    # -------------------------------------------------------------
    # SILVER LAYER TRANSFORMATIONS
    # -------------------------------------------------------------
    def build_silver_layer(self) -> dict:
        """Cleans, standardizes types, imputes nulls, and builds Silver domain tables."""
        logger.info("--- BUILDING SILVER LAYER ---")
        
        # Load Bronze raw tables
        df_sales_raw = pd.read_sql("SELECT * FROM bronze_sales_raw", con=engine)
        df_cust_raw = pd.read_sql("SELECT * FROM bronze_customers_raw", con=engine)
        df_prod_raw = pd.read_sql("SELECT * FROM bronze_products_raw", con=engine)
        df_inv_raw = pd.read_sql("SELECT * FROM bronze_inventory_raw", con=engine)
        df_store_raw = pd.read_sql("SELECT * FROM bronze_stores_raw", con=engine)

        # 1. Clean & Standardize Sales
        df_sales_clean, sales_val_metrics = self.validator.validate_sales(df_sales_raw)
        df_sales_clean["timestamp"] = pd.to_datetime(df_sales_clean["timestamp"])
        df_sales_clean["transaction_date"] = df_sales_clean["timestamp"].dt.strftime("%Y-%m-%d")
        df_sales_clean["transaction_hour"] = df_sales_clean["timestamp"].dt.hour
        df_sales_clean["gross_amount"] = (df_sales_clean["quantity"] * df_sales_clean["unit_price"]).round(2)
        df_sales_clean.to_sql("silver_sales", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created 'silver_sales' ({len(df_sales_clean)} rows)")

        # 2. Clean & Standardize Customers
        df_cust_clean, cust_val_metrics = self.validator.validate_customers(df_cust_raw)
        df_cust_clean["signup_date"] = pd.to_datetime(df_cust_clean["signup_date"]).dt.strftime("%Y-%m-%d")
        df_cust_clean.to_sql("silver_customers", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created 'silver_customers' ({len(df_cust_clean)} rows)")

        # 3. Clean & Standardize Products
        df_prod_clean = df_prod_raw.drop_duplicates(subset=["product_id"], keep="first").copy()
        df_prod_clean["profit_margin_pct"] = (
            (df_prod_clean["suggested_retail_price"] - df_prod_clean["unit_cost"]) / df_prod_clean["suggested_retail_price"] * 100
        ).round(2)
        df_prod_clean.to_sql("silver_products", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created 'silver_products' ({len(df_prod_clean)} rows)")

        # 4. Clean & Standardize Stores
        df_store_clean = df_store_raw.drop_duplicates(subset=["store_id"], keep="first").copy()
        df_store_clean.to_sql("silver_stores", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created 'silver_stores' ({len(df_store_clean)} rows)")

        # 5. Clean & Standardize Inventory
        df_inv_clean = df_inv_raw.drop_duplicates(subset=["product_id", "store_id"], keep="first").copy()
        df_inv_clean["reorder_status"] = np.where(
            df_inv_clean["stock_on_hand"] <= df_inv_clean["reorder_point"], "REORDER_NEEDED", "HEALTHY"
        )
        df_inv_clean.to_sql("silver_inventory", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created 'silver_inventory' ({len(df_inv_clean)} rows)")

        self.validator.save_audit_log()

        return {
            "silver_sales_count": len(df_sales_clean),
            "silver_customers_count": len(df_cust_clean),
            "silver_products_count": len(df_prod_clean),
            "silver_stores_count": len(df_store_clean),
            "silver_inventory_count": len(df_inv_clean),
            "sales_metrics": sales_val_metrics,
            "cust_metrics": cust_val_metrics
        }

    # -------------------------------------------------------------
    # GOLD LAYER TRANSFORMATIONS (STAR SCHEMA & DATA MARTS)
    # -------------------------------------------------------------
    def build_gold_layer(self) -> dict:
        """Aggregates clean Silver tables into Star Schema Data Marts and analytical business metrics."""
        logger.info("--- BUILDING GOLD LAYER (STAR SCHEMA & DATA MARTS) ---")

        # Load Silver tables
        s_sales = pd.read_sql("SELECT * FROM silver_sales", con=engine)
        s_cust = pd.read_sql("SELECT * FROM silver_customers", con=engine)
        s_prod = pd.read_sql("SELECT * FROM silver_products", con=engine)
        s_store = pd.read_sql("SELECT * FROM silver_stores", con=engine)
        s_inv = pd.read_sql("SELECT * FROM silver_inventory", con=engine)

        # 1. DIMENSION: dim_products
        dim_products = s_prod.copy()
        dim_products.to_sql("dim_products", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold 'dim_products' ({len(dim_products)} rows)")

        # 2. DIMENSION: dim_stores
        dim_stores = s_store.copy()
        dim_stores.to_sql("dim_stores", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold 'dim_stores' ({len(dim_stores)} rows)")

        # 3. DIMENSION: dim_customers with Customer RFM & Lifetime Value Metrics
        cust_agg = s_sales.groupby("customer_id").agg(
            total_orders=("transaction_id", "nunique"),
            total_spend=("gross_amount", "sum"),
            avg_order_value=("gross_amount", "mean"),
            last_purchase_date=("transaction_date", "max")
        ).reset_index()

        dim_cust = s_cust.merge(cust_agg, on="customer_id", how="left")
        dim_cust["total_orders"] = dim_cust["total_orders"].fillna(0).astype(int)
        dim_cust["total_spend"] = dim_cust["total_spend"].fillna(0.0).round(2)
        dim_cust["avg_order_value"] = dim_cust["avg_order_value"].fillna(0.0).round(2)

        # RFM Customer Value Segmentation
        today = pd.to_datetime(s_sales["transaction_date"]).max()
        dim_cust["last_purchase_dt"] = pd.to_datetime(dim_cust["last_purchase_date"])
        dim_cust["days_since_last_purchase"] = (today - dim_cust["last_purchase_dt"]).dt.days.fillna(999)

        def assign_rfm_segment(row):
            if row["total_spend"] > 1000 and row["days_since_last_purchase"] <= 30:
                return "Champions"
            elif row["total_spend"] > 500 and row["days_since_last_purchase"] <= 60:
                return "Loyal Customers"
            elif row["total_spend"] > 200 and row["days_since_last_purchase"] <= 90:
                return "Potential Loyalists"
            elif row["days_since_last_purchase"] > 90 and row["total_spend"] > 100:
                return "At Risk"
            else:
                return "Recent/Standard"

        dim_cust["rfm_segment"] = dim_cust.apply(assign_rfm_segment, axis=1)
        dim_cust = dim_cust.drop(columns=["last_purchase_dt"])
        dim_cust.to_sql("dim_customers", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold 'dim_customers' with RFM metrics ({len(dim_cust)} rows)")

        # 4. FACT TABLE: fact_sales
        fact_sales = s_sales.merge(s_prod[["product_id", "unit_cost"]], on="product_id", how="left")
        fact_sales["cogs"] = (fact_sales["quantity"] * fact_sales["unit_cost"]).round(2)
        fact_sales["net_profit"] = (fact_sales["gross_amount"] - fact_sales["cogs"]).round(2)
        fact_sales["profit_margin_pct"] = np.where(
            fact_sales["gross_amount"] > 0,
            (fact_sales["net_profit"] / fact_sales["gross_amount"] * 100).round(2),
            0.0
        )
        fact_sales.to_sql("fact_sales", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold 'fact_sales' ({len(fact_sales)} rows)")

        # 5. FACT TABLE: fact_inventory_snapshot
        fact_inventory = s_inv.merge(s_prod[["product_id", "unit_cost"]], on="product_id", how="left")
        fact_inventory["inventory_valuation"] = (fact_inventory["stock_on_hand"] * fact_inventory["unit_cost"]).round(2)
        fact_inventory.to_sql("fact_inventory_snapshot", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold 'fact_inventory_snapshot' ({len(fact_inventory)} rows)")

        # 6. DATA MART: gold_daily_sales_summary
        daily_summary = fact_sales.groupby("transaction_date").agg(
            total_revenue=("gross_amount", "sum"),
            total_net_profit=("net_profit", "sum"),
            total_transactions=("transaction_id", "nunique"),
            total_items_sold=("quantity", "sum"),
            avg_order_value=("gross_amount", "mean")
        ).reset_index()
        daily_summary["total_revenue"] = daily_summary["total_revenue"].round(2)
        daily_summary["total_net_profit"] = daily_summary["total_net_profit"].round(2)
        daily_summary["avg_order_value"] = daily_summary["avg_order_value"].round(2)
        daily_summary.to_sql("gold_daily_sales_summary", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold Data Mart 'gold_daily_sales_summary' ({len(daily_summary)} rows)")

        # 7. DATA MART: gold_category_performance
        category_summary = fact_sales.merge(s_prod[["product_id", "category"]], on="product_id", how="left").groupby("category").agg(
            total_revenue=("gross_amount", "sum"),
            total_profit=("net_profit", "sum"),
            total_units_sold=("quantity", "sum"),
            transaction_count=("transaction_id", "count")
        ).reset_index()
        category_summary["profit_margin_pct"] = (category_summary["total_profit"] / category_summary["total_revenue"] * 100).round(2)
        category_summary.to_sql("gold_category_performance", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Created Gold Data Mart 'gold_category_performance' ({len(category_summary)} rows)")

        total_rev = round(float(fact_sales["gross_amount"].sum()), 2)
        total_prof = round(float(fact_sales["net_profit"].sum()), 2)
        total_txns = int(fact_sales["transaction_id"].nunique())
        reorder_items = int((fact_inventory["reorder_status"] == "REORDER_NEEDED").sum())

        return {
            "total_revenue": total_rev,
            "total_profit": total_prof,
            "total_transactions": total_txns,
            "items_requiring_reorder": reorder_items,
            "gold_fact_sales_rows": len(fact_sales),
            "gold_fact_inventory_rows": len(fact_inventory),
            "gold_dim_customers_rows": len(dim_cust),
            "gold_dim_products_rows": len(dim_products),
            "gold_dim_stores_rows": len(dim_stores)
        }
