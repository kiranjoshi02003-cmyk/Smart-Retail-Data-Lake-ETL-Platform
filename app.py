import os
import logging
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from etl.config import BASE_DIR, DATABASE_URI, USE_POSTGRES
from etl.db import execute_raw_sql, get_table_names, init_db
from etl.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize Flask App specifying templates and static folders
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "web" / "templates"),
    static_folder=str(BASE_DIR / "web" / "static")
)
CORS(app)

# Ensure DB is initialized on startup
init_db()

@app.route("/")
def index():
    """Serves the main interactive dashboard application."""
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns system status, database configuration, and table count."""
    try:
        tables = get_table_names()
        return jsonify({
            "status": "ONLINE",
            "database_type": "PostgreSQL" if USE_POSTGRES else "SQLite",
            "database_uri": DATABASE_URI,
            "table_count": len(tables),
            "tables": tables
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/pipeline/run", methods=["POST"])
def trigger_pipeline():
    """Triggers end-to-end Medallion ETL pipeline run."""
    try:
        payload = request.get_json(silent=True) or {}
        force_regen = payload.get("force_regenerate", False)
        
        logger.info(f"Received API request to run ETL pipeline (force_regenerate={force_regen})")
        report = run_pipeline(force_regenerate=force_regen)
        return jsonify(report)
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/medallion/summary", methods=["GET"])
def get_medallion_summary():
    """Returns table row counts across Bronze, Silver, and Gold layers."""
    try:
        query = """
        SELECT 
            (SELECT COUNT(*) FROM bronze_sales_raw) AS bronze_sales,
            (SELECT COUNT(*) FROM bronze_customers_raw) AS bronze_customers,
            (SELECT COUNT(*) FROM bronze_inventory_raw) AS bronze_inventory,
            (SELECT COUNT(*) FROM silver_sales) AS silver_sales,
            (SELECT COUNT(*) FROM silver_customers) AS silver_customers,
            (SELECT COUNT(*) FROM silver_products) AS silver_products,
            (SELECT COUNT(*) FROM silver_inventory) AS silver_inventory,
            (SELECT COUNT(*) FROM fact_sales) AS gold_fact_sales,
            (SELECT COUNT(*) FROM dim_customers) AS gold_dim_customers,
            (SELECT COUNT(*) FROM dim_products) AS gold_dim_products,
            (SELECT COUNT(*) FROM dim_stores) AS gold_dim_stores,
            (SELECT COUNT(*) FROM fact_inventory_snapshot) AS gold_fact_inventory
        """
        res = execute_raw_sql(query)
        summary_data = res["rows"][0] if res["rows"] else {}
        return jsonify({"status": "SUCCESS", "summary": summary_data})
    except Exception as e:
        logger.warning(f"Failed to query summary, running pipeline: {str(e)}")
        report = run_pipeline()
        return jsonify({"status": "SUCCESS", "summary_triggered": True, "report": report})

@app.route("/api/kpis", methods=["GET"])
def get_dashboard_kpis():
    """Returns aggregated executive KPIs for the Power BI dashboard view."""
    try:
        # 1. Total Financial Metrics
        fin_query = """
        SELECT 
            COALESCE(SUM(gross_amount), 0) AS total_revenue,
            COALESCE(SUM(net_profit), 0) AS total_profit,
            COALESCE(AVG(gross_amount), 0) AS avg_order_value,
            COUNT(DISTINCT transaction_id) AS total_transactions,
            COALESCE(SUM(quantity), 0) AS total_units_sold
        FROM fact_sales
        """
        fin_stats = execute_raw_sql(fin_query)["rows"][0]

        # 2. Inventory Health Metrics
        inv_query = """
        SELECT 
            COUNT(*) AS total_skus,
            COALESCE(SUM(stock_on_hand), 0) AS total_stock,
            COALESCE(SUM(inventory_valuation), 0) AS total_inventory_value,
            COUNT(CASE WHEN reorder_status = 'REORDER_NEEDED' THEN 1 END) AS reorder_alerts
        FROM fact_inventory_snapshot
        """
        inv_stats = execute_raw_sql(inv_query)["rows"][0]

        # 3. Customer RFM Distribution
        rfm_query = """
        SELECT rfm_segment, COUNT(*) AS count, COALESCE(SUM(total_spend), 0) AS spend
        FROM dim_customers
        GROUP BY rfm_segment
        """
        rfm_stats = execute_raw_sql(rfm_query)["rows"]

        # 4. Monthly Trend Data
        trend_query = """
        SELECT 
            STRFTIME('%Y-%m', transaction_date) AS month,
            ROUND(SUM(gross_amount), 2) AS revenue,
            ROUND(SUM(net_profit), 2) AS profit,
            COUNT(DISTINCT transaction_id) AS orders
        FROM fact_sales
        GROUP BY month
        ORDER BY month ASC
        """
        trend_stats = execute_raw_sql(trend_query)["rows"]

        # 5. Category Performance Data
        cat_query = """
        SELECT 
            category,
            ROUND(SUM(total_revenue), 2) AS revenue,
            ROUND(SUM(total_profit), 2) AS profit,
            SUM(total_units_sold) AS units
        FROM gold_category_performance
        GROUP BY category
        ORDER BY revenue DESC
        """
        cat_stats = execute_raw_sql(cat_query)["rows"]

        return jsonify({
            "status": "SUCCESS",
            "financials": fin_stats,
            "inventory": inv_stats,
            "rfm_segments": rfm_stats,
            "monthly_trends": trend_stats,
            "category_performance": cat_stats
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/sql/execute", methods=["POST"])
def run_custom_sql():
    """Executes a custom SQL query against database tables safely."""
    try:
        data = request.get_json() or {}
        query_str = data.get("query", "").strip()
        
        if not query_str:
            return jsonify({"status": "ERROR", "message": "Query string cannot be empty"}), 400
        
        # Read-only check for UI workbench safety
        lower_q = query_str.lower()
        if any(keyword in lower_q for keyword in ["drop table", "truncate", "delete from"]):
            return jsonify({"status": "ERROR", "message": "Destructive DDL/DML statements restricted in web workbench."}), 403

        res = execute_raw_sql(query_str)
        return jsonify({
            "status": "SUCCESS",
            "row_count": len(res["rows"]),
            "columns": res["columns"],
            "data": res["rows"]
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

@app.route("/api/table/<table_name>", methods=["GET"])
def get_table_sample(table_name):
    """Fetches sample rows from a specific table."""
    try:
        allowed_tables = get_table_names()
        if table_name not in allowed_tables:
            return jsonify({"status": "ERROR", "message": f"Table '{table_name}' does not exist"}), 404
        
        limit = min(int(request.args.get("limit", 50)), 500)
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        res = execute_raw_sql(query)
        
        return jsonify({
            "status": "SUCCESS",
            "table": table_name,
            "row_count": len(res["rows"]),
            "columns": res["columns"],
            "data": res["rows"]
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/validation-logs", methods=["GET"])
def get_validation_logs():
    """Fetches recent Data Quality Validation log entries."""
    try:
        query = "SELECT * FROM silver_validation_log ORDER BY id DESC LIMIT 50"
        res = execute_raw_sql(query)
        return jsonify({"status": "SUCCESS", "logs": res["rows"]})
    except Exception as e:
        return jsonify({"status": "SUCCESS", "logs": []})

@app.route("/api/ml/datasets", methods=["GET"])
def list_ml_datasets():
    """Returns available retail datasets for ML anomaly detection."""
    try:
        from etl.generate_retail_dataset import ensure_datasets_exist
        from etl.config import ONLINE_RETAIL_CSV_PATH, SAMPLE_DIRTY_CSV_PATH
        
        ensure_datasets_exist()

        def get_file_info(path, name, is_dirty=False):
            if path.exists():
                import pandas as pd
                df = pd.read_csv(path)
                return {
                    "filename": name,
                    "records": len(df),
                    "size_kb": round(path.stat().st_size / 1024, 2),
                    "is_dirty_sample": is_dirty
                }
            return {"filename": name, "records": 0, "size_kb": 0, "is_dirty_sample": is_dirty}

        return jsonify({
            "status": "SUCCESS",
            "datasets": [
                get_file_info(ONLINE_RETAIL_CSV_PATH, "online_retail.csv", False),
                get_file_info(SAMPLE_DIRTY_CSV_PATH, "sample_dirty_data.csv", True)
            ]
        })
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/ml/anomaly-detect", methods=["POST"])
def run_ml_anomaly_detection():
    """
    Triggers dynamic Isolation Forest training & evaluation on chosen retail dataset.
    Accepts contamination rate, n_estimators, and random_state.
    """
    try:
        data = request.get_json(silent=True) or {}
        contamination = float(data.get("contamination", 0.05))
        n_estimators = int(data.get("n_estimators", 100))
        random_state = int(data.get("random_state", 42))
        dataset_name = data.get("dataset_name", "online_retail.csv")

        logger.info(f"Running ML IsolationForest: dataset={dataset_name}, contamination={contamination}, n_estimators={n_estimators}, random_state={random_state}")

        from etl.ml_anomaly import AnomalyDetectionEngine
        engine = AnomalyDetectionEngine(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state
        )
        report = engine.train_and_predict(dataset_name=dataset_name)
        return jsonify(report)
    except Exception as e:
        logger.error(f"ML Anomaly Detection failed: {str(e)}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500


if __name__ == "__main__":
    try:
        execute_raw_sql("SELECT COUNT(*) FROM fact_sales")
    except Exception:
        logger.info("First startup: triggering initial ETL pipeline run...")
        run_pipeline()

    print("\n" + "="*60)
    print(" [START] SMART RETAIL DATA LAKE & ETL PLATFORM - FLASK BACKEND")
    print(" [INFO] Web UI: http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
