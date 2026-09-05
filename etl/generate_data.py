import os
import json
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from etl.config import (
    SALES_CSV_PATH, INVENTORY_XLSX_PATH, CUSTOMERS_JSON_PATH, RAW_DATA_DIR
)

def generate_sample_data(num_sales=1200, num_customers=250, num_products=40, num_stores=8):
    """Generates realistic multi-format raw retail dataset with intentional data quality issues for silver validation."""
    print("[INFO] Generating realistic Multi-Format Raw Data (CSV, Excel, JSON)...")
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    np.random.seed(42)

    # 1. GENERATE MASTER PRODUCTS
    categories = ["Electronics", "Apparel", "Home & Kitchen", "Beauty & Care", "Sports & Outdoors"]
    products = []
    for i in range(1, num_products + 1):
        cat = random.choice(categories)
        cost = round(random.uniform(5.0, 300.0), 2)
        margin_pct = random.uniform(0.25, 0.60)
        retail_price = round(cost * (1 + margin_pct), 2)
        products.append({
            "product_id": f"PRD-{1000 + i}",
            "product_name": f"{cat[:3].upper()}-{cat.split()[0]} Item #{i}",
            "category": cat,
            "unit_cost": cost,
            "suggested_retail_price": retail_price,
            "supplier": f"Supplier-{random.randint(1, 10)}"
        })
    df_products = pd.DataFrame(products)

    # 2. GENERATE MASTER STORES
    cities = [("New York", "NY", "East"), ("Los Angeles", "CA", "West"), ("Chicago", "IL", "Midwest"), 
              ("Houston", "TX", "South"), ("Phoenix", "AZ", "West"), ("Philadelphia", "PA", "East"),
              ("San Antonio", "TX", "South"), ("San Diego", "CA", "West")]
    stores = []
    for i in range(1, num_stores + 1):
        city, state, region = cities[(i - 1) % len(cities)]
        stores.append({
            "store_id": f"STR-{100 + i}",
            "store_name": f"Smart Retail {city} #{i}",
            "city": city,
            "state": state,
            "region": region,
            "square_feet": random.randint(15000, 50000),
            "opened_year": random.randint(2015, 2023)
        })
    df_stores = pd.DataFrame(stores)

    # 3. GENERATE CUSTOMERS (JSON Format)
    loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum", "VIP"]
    first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth", "Alex", "Sophia", "Daniel", "Emma", "Chris", "Olivia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Lee", "Taylor", "Anderson", "Thomas"]

    customers = []
    start_date = datetime(2023, 1, 1)
    for i in range(1, num_customers + 1):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        c_id = f"CUST-{5000 + i}"
        signup = start_date + timedelta(days=random.randint(0, 550))
        
        # Inject intentional dirty email in ~5% of customers
        email = f"{fname.lower()}.{lname.lower()}{random.randint(1,999)}@example.com" if random.random() > 0.05 else None
        
        customers.append({
            "customer_id": c_id,
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "phone": f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            "signup_date": signup.strftime("%Y-%m-%d"),
            "loyalty_tier": random.choice(loyalty_tiers),
            "city": random.choice(cities)[0],
            "web_sessions_count": random.randint(2, 120),
            "opt_in_marketing": random.choice([True, False])
        })

    with open(CUSTOMERS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=2)
    print(f"  [OK] Saved Customers JSON: {CUSTOMERS_JSON_PATH} ({len(customers)} records)")

    # 4. GENERATE INVENTORY LEVELS (Excel Workbook)
    inventory_rows = []
    for store in stores:
        for prd in products:
            stock = random.randint(0, 250)
            reorder = random.randint(15, 40)
            safety = random.randint(10, 25)
            inventory_rows.append({
                "product_id": prd["product_id"],
                "store_id": store["store_id"],
                "stock_on_hand": stock,
                "reorder_point": reorder,
                "safety_stock": safety,
                "last_restock_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
            })
    df_inventory = pd.DataFrame(inventory_rows)

    with pd.ExcelWriter(INVENTORY_XLSX_PATH, engine="openpyxl") as writer:
        df_inventory.to_excel(writer, sheet_name="Inventory_Levels", index=False)
        df_products.to_excel(writer, sheet_name="Products_Master", index=False)
        df_stores.to_excel(writer, sheet_name="Stores_Master", index=False)
    print(f"  [OK] Saved Inventory Excel: {INVENTORY_XLSX_PATH} ({len(inventory_rows)} inventory records across 3 sheets)")

    # 5. GENERATE SALES TRANSACTIONS (CSV Format)
    sales = []
    tx_date = datetime(2024, 1, 1)
    payment_methods = ["Credit Card", "Debit Card", "Apple Pay", "PayPal", "Cash"]
    channels = ["In-Store", "Online", "Mobile App"]

    for i in range(1, num_sales + 1):
        t_id = f"TXN-{100000 + i}"
        t_time = tx_date + timedelta(days=random.randint(0, 240), hours=random.randint(8, 21), minutes=random.randint(0, 59))
        c_id = f"CUST-{5000 + random.randint(1, num_customers)}"
        p_obj = random.choice(products)
        p_id = p_obj["product_id"]
        s_id = f"STR-{100 + random.randint(1, num_stores)}"
        qty = random.choices([1, 2, 3, 4, 5, 8], weights=[50, 25, 12, 8, 3, 2])[0]
        
        unit_p = p_obj["suggested_retail_price"]
        pay_m = random.choice(payment_methods)
        
        # Edge cases
        if i % 100 == 0:  # duplicate transaction
            t_id = f"TXN-{100000 + i - 1}"
        if i % 150 == 0:  # negative quantity anomaly
            qty = -2
        if i % 120 == 0:  # null payment method
            pay_m = None

        sales.append({
            "transaction_id": t_id,
            "timestamp": t_time.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_id": c_id,
            "product_id": p_id,
            "store_id": s_id,
            "quantity": qty,
            "unit_price": unit_p,
            "payment_method": pay_m,
            "channel": random.choice(channels)
        })

    df_sales = pd.DataFrame(sales)
    df_sales.to_csv(SALES_CSV_PATH, index=False)
    print(f"  [OK] Saved Sales CSV: {SALES_CSV_PATH} ({len(sales)} transactions)")
    print("[SUCCESS] Sample raw dataset generation completed successfully!")

if __name__ == "__main__":
    generate_sample_data()
