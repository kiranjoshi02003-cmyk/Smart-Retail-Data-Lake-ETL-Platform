import json
import hashlib
from datetime import datetime
import pandas as pd
from sqlalchemy import text
from etl.config import (
    SALES_CSV_PATH, INVENTORY_XLSX_PATH, CUSTOMERS_JSON_PATH
)
from etl.db import engine, logger

def generate_row_hash(row_series):
    """Generate SHA256 string hash for row deduplication and change data capture."""
    row_str = "|".join([str(val) for val in row_series.values])
    return hashlib.sha256(row_str.encode('utf-8')).hexdigest()[:16]

class BronzeIngestionEngine:
    """Ingests raw multi-format source data into Bronze Staging tables with audit metadata."""

    def __init__(self, batch_id=None):
        self.batch_id = batch_id or f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.ingested_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _add_bronze_metadata(self, df: pd.DataFrame, source_filename: str) -> pd.DataFrame:
        """Appends audit columns required for data lake lineage."""
        df_bronze = df.copy()
        df_bronze["ingested_at"] = self.ingested_timestamp
        df_bronze["source_file"] = source_filename
        df_bronze["batch_id"] = self.batch_id
        df_bronze["row_hash"] = df_bronze.apply(generate_row_hash, axis=1)
        return df_bronze

    def ingest_sales_csv(self) -> pd.DataFrame:
        """Reads raw Sales CSV into Bronze layer."""
        logger.info(f"Ingesting raw Sales CSV from {SALES_CSV_PATH}")
        df = pd.read_csv(SALES_CSV_PATH)
        df_bronze = self._add_bronze_metadata(df, SALES_CSV_PATH.name)
        df_bronze.to_sql("bronze_sales_raw", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Loaded {len(df_bronze)} records into 'bronze_sales_raw'")
        return df_bronze

    def ingest_inventory_excel(self) -> dict:
        """Reads multi-sheet Excel file into Bronze staging tables."""
        logger.info(f"Ingesting raw Inventory Excel workbook from {INVENTORY_XLSX_PATH}")
        excel_file = pd.ExcelFile(INVENTORY_XLSX_PATH)
        bronze_dfs = {}

        sheet_mapping = {
            "Inventory_Levels": "bronze_inventory_raw",
            "Products_Master": "bronze_products_raw",
            "Stores_Master": "bronze_stores_raw"
        }

        for sheet_name, table_name in sheet_mapping.items():
            if sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                df_bronze = self._add_bronze_metadata(df, f"{INVENTORY_XLSX_PATH.name}::{sheet_name}")
                df_bronze.to_sql(table_name, con=engine, if_exists="replace", index=False)
                logger.info(f"  [OK] Loaded {len(df_bronze)} records into '{table_name}'")
                bronze_dfs[table_name] = df_bronze
        return bronze_dfs

    def ingest_customers_json(self) -> pd.DataFrame:
        """Reads Customers JSON array into Bronze layer."""
        logger.info(f"Ingesting raw Customers JSON from {CUSTOMERS_JSON_PATH}")
        with open(CUSTOMERS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df_bronze = self._add_bronze_metadata(df, CUSTOMERS_JSON_PATH.name)
        df_bronze.to_sql("bronze_customers_raw", con=engine, if_exists="replace", index=False)
        logger.info(f"  [OK] Loaded {len(df_bronze)} records into 'bronze_customers_raw'")
        return df_bronze

    def run_all(self):
        """Runs end-to-end Bronze ingestion for all raw formats."""
        logger.info(f"--- STARTING BRONZE INGESTION (Batch: {self.batch_id}) ---")
        sales_df = self.ingest_sales_csv()
        inv_dfs = self.ingest_inventory_excel()
        cust_df = self.ingest_customers_json()
        
        summary = {
            "batch_id": self.batch_id,
            "bronze_sales_count": len(sales_df),
            "bronze_inventory_count": len(inv_dfs.get("bronze_inventory_raw", [])),
            "bronze_products_count": len(inv_dfs.get("bronze_products_raw", [])),
            "bronze_stores_count": len(inv_dfs.get("bronze_stores_raw", [])),
            "bronze_customers_count": len(cust_df),
            "status": "COMPLETED"
        }
        return summary
