import time
import logging
from datetime import datetime
from etl.config import SALES_CSV_PATH, INVENTORY_XLSX_PATH, CUSTOMERS_JSON_PATH
from etl.generate_data import generate_sample_data
from etl.db import init_db, logger
from etl.ingestion import BronzeIngestionEngine
from etl.validation import DataQualityValidator
from etl.transformations import MedallionTransformer

def run_pipeline(force_regenerate=False) -> dict:
    """Executes the complete Bronze-Silver-Gold Medallion ETL pipeline."""
    start_time = time.time()
    batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    logger.info(f"==================================================")
    logger.info(f"[START] SMART RETAIL ETL PIPELINE (Batch: {batch_id})")
    logger.info(f"==================================================")

    # Step 0: Ensure raw data exists or generate fresh
    if force_regenerate or not (SALES_CSV_PATH.exists() and INVENTORY_XLSX_PATH.exists() and CUSTOMERS_JSON_PATH.exists()):
        logger.info("Raw source datasets missing or force regenerate requested. Triggering Data Generator...")
        generate_sample_data()

    # Step 1: Initialize Database Schemas
    init_db()

    # Step 2: Bronze Ingestion Layer
    ingestion = BronzeIngestionEngine(batch_id=batch_id)
    bronze_summary = ingestion.run_all()

    # Step 3: Silver Validation & Cleansing Layer
    validator = DataQualityValidator()
    transformer = MedallionTransformer(validator=validator)
    silver_summary = transformer.build_silver_layer()

    # Step 4: Gold Star Schema & Data Mart Aggregations
    gold_summary = transformer.build_gold_layer()

    elapsed_time = round(time.time() - start_time, 3)
    logger.info(f"==================================================")
    logger.info(f"[SUCCESS] ETL PIPELINE COMPLETED IN {elapsed_time} SECONDS")
    logger.info(f"==================================================")

    pipeline_report = {
        "status": "SUCCESS",
        "batch_id": batch_id,
        "execution_time_seconds": elapsed_time,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bronze_stage": bronze_summary,
        "silver_stage": silver_summary,
        "gold_stage": gold_summary
    }
    return pipeline_report

if __name__ == "__main__":
    report = run_pipeline()
    print("\n--- ETL PIPELINE EXECUTION SUMMARY ---")
    print(f"Batch ID        : {report['batch_id']}")
    print(f"Execution Time  : {report['execution_time_seconds']}s")
    print(f"Total Revenue   : ${report['gold_stage']['total_revenue']:,.2f}")
    print(f"Total Profit    : ${report['gold_stage']['total_profit']:,.2f}")
    print(f"Total Sales Txns: {report['gold_stage']['total_transactions']}")
    print(f"Reorder Alerts  : {report['gold_stage']['items_requiring_reorder']} items")
