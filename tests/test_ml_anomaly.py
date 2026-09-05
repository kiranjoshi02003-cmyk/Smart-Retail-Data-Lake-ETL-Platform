import pytest
import pandas as pd
import numpy as np

from etl.generate_retail_dataset import generate_uci_online_retail, generate_sample_dirty_data, ensure_datasets_exist
from etl.ml_preprocessing import PreprocessingPipeline
from etl.ml_anomaly import AnomalyDetectionEngine
from etl.config import ONLINE_RETAIL_CSV_PATH, SAMPLE_DIRTY_CSV_PATH
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_dataset_generation():
    """Verifies that Online Retail and sample dirty datasets can be created with correct columns."""
    df_clean = generate_uci_online_retail(num_records=500, seed=99)
    assert len(df_clean) == 500
    expected_cols = {"InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"}
    assert expected_cols.issubset(set(df_clean.columns))

    df_dirty = generate_sample_dirty_data(num_records=300, seed=99)
    assert len(df_dirty) == 300
    assert expected_cols.issubset(set(df_dirty.columns))

def test_feature_preprocessing():
    """Verifies that derived features are correctly extracted and scaled."""
    raw_data = {
        "InvoiceNo": ["10001", "10002", "10003"],
        "StockCode": ["85123A", "71053", "84406B"],
        "Description": ["TEST ITEM 1", "TEST ITEM 2", "TEST ITEM 3"],
        "Quantity": [2, 10, 1],
        "UnitPrice": [15.0, 50.0, 5.0],
        "CustomerID": [12345, 12345, 67890],
        "Country": ["United Kingdom", "United Kingdom", "France"]
    }
    df_raw = pd.DataFrame(raw_data)
    pipeline = PreprocessingPipeline()
    df_proc, X_scaled = pipeline.extract_features(df_raw)

    assert "TotalAmount" in df_proc.columns
    assert "CustomerPurchaseFrequency" in df_proc.columns
    assert "CustomerTotalSpend" in df_proc.columns
    assert "AverageTransactionValue" in df_proc.columns
    assert "CountryTransactionCount" in df_proc.columns

    assert df_proc.loc[0, "TotalAmount"] == 30.0
    assert df_proc.loc[1, "TotalAmount"] == 500.0
    assert X_scaled.shape[0] == 3
    assert X_scaled.shape[1] == 7

def test_isolation_forest_model():
    """Verifies dynamic Isolation Forest model training and DQ vs ML anomaly separation."""
    engine = AnomalyDetectionEngine(contamination=0.1, n_estimators=50, random_state=42)
    report = engine.train_and_predict(dataset_name="sample_dirty_data.csv")

    assert report["status"] == "SUCCESS"
    assert "kpi_summary" in report
    assert report["kpi_summary"]["total_transactions"] > 0
    assert "score_distribution" in report
    assert len(report["score_distribution"]) == 10
    assert "top_suspicious_transactions" in report
    assert len(report["top_suspicious_transactions"]) > 0

    # Ensure rule-based DQ issues and ML anomalies are classified
    sample_tx = report["top_suspicious_transactions"][0]
    assert "system_status" in sample_tx
    assert sample_tx["system_status"] in ["DATA QUALITY ISSUE", "ML-DETECTED ANOMALY", "NORMAL"]

def test_api_endpoints(client):
    """Verifies Flask API routes /api/ml/datasets and /api/ml/anomaly-detect."""
    res_datasets = client.get("/api/ml/datasets")
    assert res_datasets.status_code == 200
    data_ds = res_datasets.get_json()
    assert data_ds["status"] == "SUCCESS"
    assert len(data_ds["datasets"]) == 2

    res_ml = client.post("/api/ml/anomaly-detect", json={
        "dataset_name": "sample_dirty_data.csv",
        "contamination": 0.05,
        "n_estimators": 50,
        "random_state": 42
    })
    assert res_ml.status_code == 200
    data_ml = res_ml.get_json()
    assert data_ml["status"] == "SUCCESS"
    assert data_ml["model_settings"]["algorithm"] == "IsolationForest"
