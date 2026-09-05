import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from etl.config import ONLINE_RETAIL_CSV_PATH, SAMPLE_DIRTY_CSV_PATH, DATA_DIR

def generate_uci_online_retail(num_records=25000, seed=42):
    """
    Generates high-fidelity dataset matching UCI Machine Learning Repository Online Retail characteristics.
    
    Columns:
    - InvoiceNo: 6-digit invoice identifier (e.g. 536365) or cancellation starting with 'C'
    - StockCode: 5-digit alphanumeric item code (e.g. 85123A, 71053, 84406B)
    - Description: Product description (e.g. WHITE HANGING HEART T-LIGHT HOLDER)
    - Quantity: Transaction item count (positive for sales, negative for returns/cancellations)
    - InvoiceDate: Timestamp string (YYYY-MM-DD HH:MM:SS)
    - UnitPrice: Product unit price in GBP (£)
    - CustomerID: 5-digit customer account ID (float/str) or missing/NaN for guest checkout
    - Country: Customer location country (e.g. United Kingdom, France, Germany, EIRE)
    """
    random.seed(seed)
    np.random.seed(seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Generating UCI Online Retail dataset ({num_records} records)...")
    
    # Real Online Retail catalogue samples
    products = [
        ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
        ("71053", "WHITE METAL LANTERN", 3.39),
        ("84406B", "CREAM CUPID HEARTS COAT HANGER", 2.75),
        ("84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 3.75),
        ("84029E", "RED WOOLLY HOTTIE WHITE HEART.", 3.75),
        ("22752", "SET 7 BABUSHKA NESTING BOXES", 7.65),
        ("21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 4.25),
        ("22633", "HAND WARMER UNION JACK", 1.85),
        ("22632", "HAND WARMER RED RETROSPOT", 1.85),
        ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
        ("22745", "POPPY'S PLAYHOUSE BEDROOM", 2.10),
        ("22748", "POPPY'S PLAYHOUSE KITCHEN", 2.10),
        ("22749", "FELTCRAFT PRINCESS CHARLOTTE DOLL", 3.75),
        ("22310", "IVORY KNITTED MUG COSY", 1.65),
        ("84969", "BOX OF 6 ASSORTED PINK TEACUPS", 4.25),
        ("22386", "JUMBO BAG PINK POLKADOT", 1.95),
        ("21915", "RED RETROSPOT MINI CASES", 7.95),
        ("22423", "REGENCY CAKESTAND 3 TIER", 12.75),
        ("22720", "SET OF 3 CAKE TINS PANTRY DESIGN", 4.95),
        ("D", "Discount", 13.00),
        ("POST", "POSTAGE", 18.00),
        ("23209", "LUNCH BAG VINTAGE DOILY", 1.65),
        ("22961", "JAM MAKING SET PRINTED", 1.45),
        ("22326", "ROUND SNACK BOXES SET OF 4 WOODLAND", 2.95),
        ("21212", "PACK OF 72 RETROSPOT TINY TINS", 0.55),
    ]

    countries_weights = [
        ("United Kingdom", 0.88),
        ("Germany", 0.03),
        ("France", 0.03),
        ("EIRE", 0.02),
        ("Spain", 0.01),
        ("Netherlands", 0.01),
        ("Belgium", 0.008),
        ("Switzerland", 0.006),
        ("Portugal", 0.003),
        ("Australia", 0.003)
    ]
    countries, weights = zip(*countries_weights)

    start_date = datetime(2010, 12, 1, 8, 26, 0)
    
    rows = []
    inv_counter = 536365
    cust_ids = [random.randint(12346, 18287) for _ in range(3500)]
    
    record_idx = 0
    while record_idx < num_records:
        inv_no = str(inv_counter)
        inv_counter += 1
        
        # Decide if cancellation
        is_cancel = random.random() < 0.02
        if is_cancel:
            inv_no = f"C{inv_no}"

        c_id = float(random.choice(cust_ids)) if random.random() > 0.14 else np.nan
        country = random.choices(countries, weights=weights)[0]
        tx_dt = start_date + timedelta(days=random.randint(0, 373), hours=random.randint(8, 19), minutes=random.randint(0, 59))
        
        # Number of items in this invoice (1 to 6)
        items_count = min(random.randint(1, 6), num_records - record_idx)
        
        for _ in range(items_count):
            stock, desc, base_price = random.choice(products)
            
            # Base quantity
            if is_cancel:
                qty = -random.randint(1, 12)
            else:
                qty = random.choices([1, 2, 3, 4, 6, 12, 24, 48], weights=[45, 20, 15, 10, 5, 3, 1, 1])[0]
            
            # Minor price noise
            price = round(max(0.10, base_price * random.uniform(0.9, 1.1)), 2)
            
            # Substantial ML Anomaly injections (0.5% extreme high values / abnormal bulk orders)
            rand_val = random.random()
            if rand_val < 0.003: # Extreme unit price anomaly
                price = round(float(random.choice([4500.0, 9500.0, 15000.0, 38970.0])), 2)
            elif rand_val < 0.006: # Extreme quantity anomaly
                qty = random.randint(800, 3500)
            
            rows.append({
                "InvoiceNo": inv_no,
                "StockCode": stock,
                "Description": desc,
                "Quantity": qty,
                "InvoiceDate": tx_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "UnitPrice": price,
                "CustomerID": c_id,
                "Country": country
            })
            record_idx += 1

    df = pd.DataFrame(rows)
    df.to_csv(ONLINE_RETAIL_CSV_PATH, index=False)
    print(f"[SUCCESS] Saved UCI Online Retail dataset to '{ONLINE_RETAIL_CSV_PATH}' ({len(df)} records).")
    return df

def generate_sample_dirty_data(num_records=1500, seed=123):
    """
    Generates smaller sample_dirty_data.csv based on Online Retail with intentional realistic Data Quality bugs.
    
    Data-quality bugs injected:
    1. Missing CustomerID values (NaN)
    2. Duplicate transaction rows
    3. Negative quantities where inappropriate (e.g. sales with qty < 0 without 'C' prefix)
    4. Extreme UnitPrice values (e.g. 95000.00 or -50.00)
    5. Missing descriptions (None/NaN)
    6. Invalid dates (e.g. "2024-99-99", "invalid-date-format")
    7. Inconsistent country names (e.g. "uk", "U.K.", "UNITED KINGDOM", "UNKNOWN_COUNTRY")
    """
    random.seed(seed)
    np.random.seed(seed)
    
    print(f"[INFO] Generating sample_dirty_data.csv dataset with intentional Data Quality bugs ({num_records} records)...")
    
    # Load or generate clean base
    if not ONLINE_RETAIL_CSV_PATH.exists():
        df_base = generate_uci_online_retail(num_records=5000)
    else:
        df_base = pd.read_csv(ONLINE_RETAIL_CSV_PATH, nrows=5000)
    
    df_sample = df_base.sample(n=min(num_records, len(df_base)), random_state=seed).copy()
    
    # Convert types to object to allow injecting bad strings
    df_sample["InvoiceDate"] = df_sample["InvoiceDate"].astype(str)
    df_sample["Country"] = df_sample["Country"].astype(str)
    
    rows = df_sample.to_dict("records")
    dirty_log = []
    
    for i, r in enumerate(rows):
        # 1. Missing CustomerID (~8%)
        if i % 12 == 0:
            r["CustomerID"] = np.nan
            dirty_log.append((i, "Missing CustomerID"))

        # 2. Duplicate row (~4%)
        if i > 10 and i % 25 == 0:
            r["InvoiceNo"] = rows[i-1]["InvoiceNo"]
            r["StockCode"] = rows[i-1]["StockCode"]
            dirty_log.append((i, "Duplicate Transaction"))

        # 3. Negative quantity on non-cancellation invoice (~5%)
        if i % 20 == 0 and not str(r["InvoiceNo"]).startswith("C"):
            r["Quantity"] = -abs(int(r["Quantity"])) if int(r["Quantity"]) != 0 else -5
            dirty_log.append((i, "Negative Quantity"))

        # 4. Extreme or negative UnitPrice (~3%)
        if i % 35 == 0:
            r["UnitPrice"] = 95000.00 if i % 70 == 0 else -15.50
            dirty_log.append((i, "Invalid UnitPrice"))

        # 5. Missing Description (~6%)
        if i % 16 == 0:
            r["Description"] = np.nan
            dirty_log.append((i, "Missing Description"))

        # 6. Invalid dates (~3%)
        if i % 30 == 0:
            r["InvoiceDate"] = "2024-99-99 25:99:99" if i % 60 == 0 else "INVALID_TIMESTAMP"
            dirty_log.append((i, "Invalid Date"))

        # 7. Inconsistent Country casing / values (~6%)
        if i % 18 == 0:
            inconsistent_countries = ["uk", "U.K.", "UNITED KINGDOM", "united kingdom", "UNKNOWN_COUNTRY", "  Germany  "]
            r["Country"] = random.choice(inconsistent_countries)
            dirty_log.append((i, "Inconsistent Country"))

    df_dirty = pd.DataFrame(rows)
    df_dirty.to_csv(SAMPLE_DIRTY_CSV_PATH, index=False)
    print(f"[SUCCESS] Saved sample_dirty_data.csv to '{SAMPLE_DIRTY_CSV_PATH}' ({len(df_dirty)} records).")
    print(f"[INFO] Total intentional Data Quality bugs injected: {len(dirty_log)}")
    return df_dirty

def ensure_datasets_exist():
    """Checks for existence of datasets, generating them if not present."""
    if not ONLINE_RETAIL_CSV_PATH.exists():
        generate_uci_online_retail()
    if not SAMPLE_DIRTY_CSV_PATH.exists():
        generate_sample_dirty_data()

if __name__ == "__main__":
    ensure_datasets_exist()
