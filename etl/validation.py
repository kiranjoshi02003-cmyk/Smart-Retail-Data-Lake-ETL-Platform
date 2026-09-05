import logging
import pandas as pd
from datetime import datetime
from etl.config import VALIDATION_RULES
from etl.db import engine, logger

class DataQualityValidator:
    """Automated data quality checks, schema validation, and anomaly logging."""

    def __init__(self):
        self.validation_errors = []

    def log_error(self, layer: str, dataset_name: str, rule: str, severity: str, record_count: int, details: str):
        """Appends validation issue to internal registry and logs to database."""
        err_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "layer": layer,
            "dataset": dataset_name,
            "rule": rule,
            "severity": severity,
            "affected_records": record_count,
            "details": details
        }
        self.validation_errors.append(err_entry)
        logger.warning(f"[{severity}] Data Quality Issue on '{dataset_name}': {rule} -> {details} ({record_count} records affected)")

    def save_audit_log(self):
        """Persists validation audit trail into 'silver_validation_log' table."""
        if self.validation_errors:
            df_log = pd.DataFrame(self.validation_errors)
            df_log.to_sql("silver_validation_log", con=engine, if_exists="append", index=False)

    def validate_sales(self, df_sales: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """Validates and cleans sales transactions DataFrame."""
        df_clean = df_sales.copy()
        initial_count = len(df_clean)

        # 1. Deduplicate by transaction_id
        duplicates_count = df_clean.duplicated(subset=["transaction_id"]).sum()
        if duplicates_count > 0:
            self.log_error("Silver", "sales", "Deduplication", "HIGH", duplicates_count, "Found duplicate transaction_ids")
            df_clean = df_clean.drop_duplicates(subset=["transaction_id"], keep="first")

        # 2. Filter negative or zero quantity anomalies
        invalid_qty_count = (df_clean["quantity"] <= 0).sum()
        if invalid_qty_count > 0:
            self.log_error("Silver", "sales", "Quantity Bounds Check", "HIGH", invalid_qty_count, "Filtered transactions with quantity <= 0")
            df_clean = df_clean[df_clean["quantity"] > 0]

        # 3. Impute missing payment methods with 'Unknown'
        missing_pay = df_clean["payment_method"].isna().sum()
        if missing_pay > 0:
            self.log_error("Silver", "sales", "Null Imputation", "MEDIUM", missing_pay, "Imputed missing payment_method with 'Unknown'")
            df_clean["payment_method"] = df_clean["payment_method"].fillna("Unknown")

        # 4. Price bounds check
        min_p = VALIDATION_RULES["sales"]["min_unit_price"]
        invalid_price = (df_clean["unit_price"] < min_p).sum()
        if invalid_price > 0:
            self.log_error("Silver", "sales", "Price Bounds Check", "MEDIUM", invalid_price, f"Unit price below minimum {min_p}")

        clean_count = len(df_clean)
        metrics = {
            "initial_records": initial_count,
            "duplicates_removed": duplicates_count,
            "invalid_qty_removed": invalid_qty_count,
            "imputed_fields": missing_pay,
            "final_records": clean_count,
            "pass_rate": round((clean_count / initial_count) * 100, 2)
        }
        return df_clean, metrics

    def validate_customers(self, df_cust: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """Validates and cleans customers DataFrame."""
        df_clean = df_cust.copy()
        initial_count = len(df_clean)

        # Deduplicate customers by customer_id
        dupes = df_clean.duplicated(subset=["customer_id"]).sum()
        if dupes > 0:
            self.log_error("Silver", "customers", "Deduplication", "HIGH", dupes, "Removed duplicate customer IDs")
            df_clean = df_clean.drop_duplicates(subset=["customer_id"], keep="first")

        # Impute missing email addresses
        missing_email = df_clean["email"].isna().sum()
        if missing_email > 0:
            self.log_error("Silver", "customers", "Email Imputation", "LOW", missing_email, "Generated missing synthetic fallback emails")
            df_clean["email"] = df_clean.apply(
                lambda r: r["email"] if pd.notna(r["email"]) else f"{str(r['first_name']).lower()}.{str(r['last_name']).lower()}@placeholder.com",
                axis=1
            )

        clean_count = len(df_clean)
        metrics = {
            "initial_records": initial_count,
            "duplicates_removed": dupes,
            "emails_imputed": missing_email,
            "final_records": clean_count,
            "pass_rate": round((clean_count / initial_count) * 100, 2)
        }
        return df_clean, metrics
