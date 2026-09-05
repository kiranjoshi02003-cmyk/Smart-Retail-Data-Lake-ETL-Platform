import os
import pytest
import pandas as pd
from pathlib import Path
from etl.config import SALES_CSV_PATH, INVENTORY_XLSX_PATH, CUSTOMERS_JSON_PATH
from etl.generate_data import generate_sample_data
from etl.validation import DataQualityValidator
from etl.pipeline import run_pipeline
from app import app

@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_01_generate_sample_data():
    """Verify raw multi-format datasets are generated correctly."""
    generate_sample_data(num_sales=100, num_customers=30, num_products=10, num_stores=3)
    assert SALES_CSV_PATH.exists(), "sales_raw.csv should be created"
    assert INVENTORY_XLSX_PATH.exists(), "inventory_raw.xlsx should be created"
    assert CUSTOMERS_JSON_PATH.exists(), "customers_raw.json should be created"

def test_02_validation_rules():
    """Test data quality validator cleansing and anomaly detection."""
    validator = DataQualityValidator()
    
    # Test sales deduplication & anomaly filtering
    mock_sales = pd.DataFrame([
        {"transaction_id": "TXN-1", "quantity": 2, "unit_price": 50.0, "payment_method": "Credit Card"},
        {"transaction_id": "TXN-1", "quantity": 2, "unit_price": 50.0, "payment_method": "Credit Card"},  # Duplicate
        {"transaction_id": "TXN-2", "quantity": -5, "unit_price": 20.0, "payment_method": "Cash"},       # Negative quantity
        {"transaction_id": "TXN-3", "quantity": 1, "unit_price": 10.0, "payment_method": None}            # Null payment
    ])
    
    df_clean, metrics = validator.validate_sales(mock_sales)
    
    assert metrics["duplicates_removed"] == 1, "Should remove 1 duplicate transaction"
    assert metrics["invalid_qty_removed"] == 1, "Should remove 1 transaction with negative quantity"
    assert metrics["imputed_fields"] == 1, "Should impute 1 missing payment method"
    assert len(df_clean) == 2, "Cleaned dataset should contain exactly 2 valid rows"

def test_03_end_to_end_pipeline():
    """Test full Medallion Bronze-Silver-Gold pipeline execution."""
    report = run_pipeline(force_regenerate=True)
    
    assert report["status"] == "SUCCESS"
    assert "batch_id" in report
    assert report["gold_stage"]["total_revenue"] > 0, "Gold total revenue should be positive"
    assert report["gold_stage"]["gold_fact_sales_rows"] > 0, "Fact sales table should have rows"

def test_04_flask_api_routes(client):
    """Test Flask web server API endpoints."""
    # Status Endpoint
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    data_status = res_status.get_json()
    assert data_status["status"] == "ONLINE"

    # Medallion Summary Endpoint
    res_med = client.get("/api/medallion/summary")
    assert res_med.status_code == 200

    # KPIs Endpoint
    res_kpis = client.get("/api/kpis")
    assert res_kpis.status_code == 200
    data_kpis = res_kpis.get_json()
    assert data_kpis["status"] == "SUCCESS"

    # SQL Execution Endpoint
    res_sql = client.post("/api/sql/execute", json={"query": "SELECT COUNT(*) AS cnt FROM dim_customers"})
    assert res_sql.status_code == 200
    data_sql = res_sql.get_json()
    assert data_sql["status"] == "SUCCESS"
    assert data_sql["row_count"] == 1
