import os
from pathlib import Path

# Base Directory Setup
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
BRONZE_DATA_DIR = DATA_DIR / "bronze"
SILVER_DATA_DIR = DATA_DIR / "silver"
GOLD_DATA_DIR = DATA_DIR / "gold"

# Ensure directories exist
for folder in [DATA_DIR, RAW_DATA_DIR, BRONZE_DATA_DIR, SILVER_DATA_DIR, GOLD_DATA_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Database Configuration (PostgreSQL with SQLite fallback)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "smart_retail_db")

# Default SQLite fallback path
SQLITE_DB_PATH = DATA_DIR / "smart_retail_datalake.db"

# Use PostgreSQL if explicitly set via env var, otherwise default to fast local SQLite database
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() in ("true", "1", "yes")

if USE_POSTGRES:
    DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
else:
    DATABASE_URI = f"sqlite:///{SQLITE_DB_PATH}"

# Source File Paths
SALES_CSV_PATH = RAW_DATA_DIR / "sales_raw.csv"
INVENTORY_XLSX_PATH = RAW_DATA_DIR / "inventory_raw.xlsx"
CUSTOMERS_JSON_PATH = RAW_DATA_DIR / "customers_raw.json"
ONLINE_RETAIL_CSV_PATH = DATA_DIR / "online_retail.csv"
SAMPLE_DIRTY_CSV_PATH = DATA_DIR / "sample_dirty_data.csv"

# Quality & Validation Rules
VALIDATION_RULES = {
    "sales": {
        "required_columns": ["transaction_id", "timestamp", "customer_id", "product_id", "store_id", "quantity", "unit_price", "payment_method"],
        "min_unit_price": 0.01,
        "max_unit_price": 10000.0,
        "min_quantity": 1
    },
    "inventory": {
        "required_columns": ["product_id", "store_id", "stock_on_hand", "reorder_point", "safety_stock"],
        "min_stock": 0
    },
    "customers": {
        "required_columns": ["customer_id", "first_name", "last_name", "email", "signup_date", "loyalty_tier"],
        "valid_tiers": ["Bronze", "Silver", "Gold", "Platinum", "VIP"]
    }
}

# Machine Learning Anomaly Detection Configuration
ML_MODEL_CONFIG = {
    "default_contamination": 0.05,
    "default_n_estimators": 100,
    "default_random_state": 42,
    "numerical_features": [
        "TotalAmount",
        "Quantity",
        "UnitPrice",
        "CustomerPurchaseFrequency",
        "CustomerTotalSpend",
        "AverageTransactionValue",
        "CountryTransactionCount"
    ]
}

