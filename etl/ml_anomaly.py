import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import IsolationForest
from etl.config import ML_MODEL_CONFIG, ONLINE_RETAIL_CSV_PATH, SAMPLE_DIRTY_CSV_PATH
from etl.ml_preprocessing import PreprocessingPipeline
from etl.generate_retail_dataset import ensure_datasets_exist

class AnomalyDetectionEngine:
    """
    ML Anomaly Detection engine using scikit-learn Isolation Forest.
    Strictly separates Rule-Based Data Quality Issues from ML-Detected Multivariate Anomalies.
    """

    def __init__(self, contamination=0.05, n_estimators=100, random_state=42):
        self.contamination = float(contamination)
        self.n_estimators = int(n_estimators)
        self.random_state = int(random_state)
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.pipeline = PreprocessingPipeline()

    def identify_rule_based_dq_issues(self, df_raw: pd.DataFrame) -> tuple[pd.DataFrame, list]:
        """
        Executes strict rule-based validation for obvious data-quality issues:
        - Missing CustomerID
        - Duplicate rows
        - Negative quantities on non-cancellations
        - Extreme / negative unit prices below 0.01 or over 50,000.00
        - Invalid date formats
        - Missing descriptions
        - Inconsistent country names
        """
        df = df_raw.copy()
        dq_issues = []
        df["dq_issue_flag"] = False
        df["dq_issue_reason"] = None

        for idx, row in df.iterrows():
            reasons = []
            
            # Rule 1: Missing CustomerID
            if pd.isna(row.get("CustomerID")):
                reasons.append("Missing CustomerID")
                
            # Rule 2: Missing Description
            if pd.isna(row.get("Description")) or str(row.get("Description")).strip() == "":
                reasons.append("Missing Description")
                
            # Rule 3: Negative quantity on non-cancellation invoice
            inv_str = str(row.get("InvoiceNo", ""))
            qty = pd.to_numeric(row.get("Quantity"), errors="coerce")
            if pd.isna(qty) or (qty < 0 and not inv_str.startswith("C")):
                reasons.append("Negative Quantity on Non-Cancellation")

            # Rule 4: Invalid UnitPrice
            price = pd.to_numeric(row.get("UnitPrice"), errors="coerce")
            if pd.isna(price) or price <= 0 or price > 50000:
                reasons.append("Invalid/Extreme UnitPrice Bounds")

            # Rule 5: Invalid Date format
            date_str = str(row.get("InvoiceDate", ""))
            try:
                pd.to_datetime(date_str)
            except Exception:
                reasons.append("Invalid Date Timestamp")

            # Rule 6: Inconsistent Country Casing/Format
            country_str = str(row.get("Country", ""))
            if country_str in ["uk", "U.K.", "UNITED KINGDOM", "united kingdom", "UNKNOWN_COUNTRY"] or country_str.strip() != country_str:
                reasons.append("Inconsistent Country Name Format")

            if reasons:
                df.at[idx, "dq_issue_flag"] = True
                df.at[idx, "dq_issue_reason"] = ", ".join(reasons)
                dq_issues.append({
                    "row_index": int(idx),
                    "invoice_no": str(inv_str),
                    "stock_code": str(row.get("StockCode", "")),
                    "reasons": reasons
                })

        # Rule 7: Duplicate Rows
        dupe_mask = df.duplicated(subset=["InvoiceNo", "StockCode", "InvoiceDate"], keep="first")
        for idx in df[dupe_mask].index:
            df.at[idx, "dq_issue_flag"] = True
            current_reason = df.at[idx, "dq_issue_reason"]
            df.at[idx, "dq_issue_reason"] = (current_reason + ", Duplicate Row") if current_reason else "Duplicate Row"

        return df, dq_issues

    def train_and_predict(self, dataset_name="online_retail.csv") -> dict:
        """
        Loads specified dataset, extracts features, trains Isolation Forest dynamically,
        scores transactions, separates DQ vs ML anomalies, and returns full JSON report.
        """
        ensure_datasets_exist()

        # Select file path
        if dataset_name == "sample_dirty_data.csv":
            file_path = SAMPLE_DIRTY_CSV_PATH
        else:
            file_path = ONLINE_RETAIL_CSV_PATH
            dataset_name = "online_retail.csv"

        df_raw = pd.read_csv(file_path)
        total_records = len(df_raw)

        # Step 1: Identify Rule-Based Data Quality Issues
        df_dq, dq_issues_list = self.identify_rule_based_dq_issues(df_raw)
        total_dq_issues = len(df_dq[df_dq["dq_issue_flag"]])

        # Step 2: Feature Engineering & Preprocessing
        df_processed, X_scaled = self.pipeline.extract_features(df_dq)

        # Step 3: Train Isolation Forest Model dynamically
        self.model.fit(X_scaled)

        # Step 4: Model Predictions (-1 = Anomaly, 1 = Normal)
        preds = self.model.predict(X_scaled)
        
        # Step 5: Raw decision function scores (lower = more anomalous)
        raw_scores = self.model.decision_function(X_scaled)
        
        # Normalize anomaly scores to range [0, 1] where 1 is highest anomaly severity
        score_min, score_max = raw_scores.min(), raw_scores.max()
        if score_max != score_min:
            normalized_scores = (score_max - raw_scores) / (score_max - score_min)
        else:
            normalized_scores = np.zeros_like(raw_scores)

        df_processed["ml_anomaly_pred"] = preds
        df_processed["ml_anomaly_label"] = np.where(preds == -1, "Anomaly", "Normal")
        df_processed["ml_anomaly_score"] = np.round(normalized_scores, 4)

        # System Classification: Clearly separate DQ vs ML Anomaly
        def classify_status(row):
            if row["dq_issue_flag"]:
                return "DATA QUALITY ISSUE"
            elif row["ml_anomaly_pred"] == -1:
                return "ML-DETECTED ANOMALY"
            else:
                return "NORMAL"

        df_processed["system_status"] = df_processed.apply(classify_status, axis=1)

        # Summary Metrics
        ml_anomalies_count = int((df_processed["ml_anomaly_pred"] == -1).sum())
        normal_count = int((df_processed["ml_anomaly_pred"] == 1).sum())
        anomaly_percentage = round((ml_anomalies_count / total_records) * 100, 2)
        avg_score = round(float(normalized_scores.mean()), 4)

        # Score distribution histogram (10 bins)
        hist, bin_edges = np.histogram(normalized_scores, bins=10, range=(0, 1))
        distribution = [
            {"bin_start": round(bin_edges[i], 2), "bin_end": round(bin_edges[i+1], 2), "count": int(hist[i])}
            for i in range(len(hist))
        ]

        # Anomalies by Country
        country_anomalies = (
            df_processed[df_processed["system_status"] == "ML-DETECTED ANOMALY"]
            .groupby("Country")["InvoiceNo"]
            .count()
            .reset_index()
            .rename(columns={"InvoiceNo": "anomaly_count"})
            .sort_values(by="anomaly_count", ascending=False)
            .head(10)
            .to_dict("records")
        )

        # Anomalies by Product/StockCode
        product_anomalies = (
            df_processed[df_processed["system_status"] == "ML-DETECTED ANOMALY"]
            .groupby(["StockCode", "Description"])["InvoiceNo"]
            .count()
            .reset_index()
            .rename(columns={"InvoiceNo": "anomaly_count"})
            .sort_values(by="anomaly_count", ascending=False)
            .head(10)
            .to_dict("records")
        )

        # Top Suspicious Transactions (sorted by ML anomaly score descending)
        top_suspicious_df = df_processed.sort_values(by="ml_anomaly_score", ascending=False).head(100)
        
        suspicious_transactions = []
        for idx, row in top_suspicious_df.iterrows():
            suspicious_transactions.append({
                "transaction_index": int(idx),
                "invoice_no": str(row.get("InvoiceNo", "")),
                "stock_code": str(row.get("StockCode", "")),
                "description": str(row.get("Description", "")),
                "quantity": float(row.get("Quantity", 0)),
                "unit_price": float(row.get("UnitPrice", 0.0)),
                "total_amount": round(float(row.get("TotalAmount", 0.0)), 2),
                "customer_id": "GUEST" if pd.isna(row.get("CustomerID")) else str(row.get("CustomerID")),
                "country": str(row.get("Country", "")),
                "system_status": str(row.get("system_status")),
                "anomaly_label": str(row.get("ml_anomaly_label")),
                "anomaly_score": float(row.get("ml_anomaly_score")),
                "dq_reason": row.get("dq_issue_reason")
            })

        # Data Quality Breakdown by Rule type
        dq_rule_breakdown = {}
        for issue in dq_issues_list:
            for r in issue["reasons"]:
                dq_rule_breakdown[r] = dq_rule_breakdown.get(r, 0) + 1

        return {
            "status": "SUCCESS",
            "model_settings": {
                "dataset_name": dataset_name,
                "contamination": self.contamination,
                "n_estimators": self.n_estimators,
                "random_state": self.random_state,
                "algorithm": "IsolationForest",
                "features_used": ML_MODEL_CONFIG["numerical_features"]
            },
            "kpi_summary": {
                "total_transactions": total_records,
                "ml_anomalies_count": ml_anomalies_count,
                "normal_transactions_count": normal_count,
                "anomaly_percentage": anomaly_percentage,
                "rule_based_dq_issues_count": total_dq_issues,
                "average_anomaly_score": avg_score
            },
            "score_distribution": distribution,
            "anomalies_by_country": country_anomalies,
            "anomalies_by_product": product_anomalies,
            "top_suspicious_transactions": suspicious_transactions,
            "dq_rule_breakdown": dq_rule_breakdown
        }
