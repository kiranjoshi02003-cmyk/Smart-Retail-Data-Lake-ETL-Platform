import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler
from etl.config import ML_MODEL_CONFIG

class PreprocessingPipeline:
    """
    Feature engineering and preprocessing pipeline for retail transaction anomaly detection.
    Converts raw retail transaction records into rich numerical features.
    """

    def __init__(self, use_robust_scaling=True):
        self.use_robust_scaling = use_robust_scaling
        self.scaler = RobustScaler() if use_robust_scaling else StandardScaler()
        self.feature_columns = ML_MODEL_CONFIG["numerical_features"]

    def extract_features(self, df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Takes raw transaction DataFrame and produces derived feature matrix for ML modeling.
        
        Derived Features Created:
        1. TotalAmount = Quantity * UnitPrice
        2. Quantity
        3. UnitPrice
        4. CustomerPurchaseFrequency = total transactions count per customer
        5. CustomerTotalSpend = sum of TotalAmount per customer
        6. AverageTransactionValue = mean TotalAmount per customer
        7. CountryTransactionCount = total transactions count per country
        
        Returns:
            df_processed: Full DataFrame with raw + derived feature columns.
            X_scaled: Preprocessed and scaled numpy array ready for Isolation Forest.
        """
        df = df_raw.copy()

        # Ensure correct numerical types
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(1.0)
        df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce").fillna(0.0)

        # 1. TotalAmount = Quantity * UnitPrice
        df["TotalAmount"] = df["Quantity"] * df["UnitPrice"]

        # Clean CustomerID for grouping (NaN customer -> 'GUEST')
        cust_key = df["CustomerID"].fillna("GUEST").astype(str)

        # 2. Customer Aggregations (Frequency, Total Spend, Avg Spend)
        cust_stats = df.groupby(cust_key)["TotalAmount"].agg(
            CustomerPurchaseFrequency="count",
            CustomerTotalSpend="sum",
            AverageTransactionValue="mean"
        ).reset_index()

        df = df.merge(cust_stats, left_on=cust_key, right_on="CustomerID", how="left", suffixes=("", "_cust"))

        # 3. Country Aggregations (Country Transaction Count)
        country_key = df["Country"].fillna("Unknown").astype(str).str.strip().str.upper()
        country_counts = df.groupby(country_key)["InvoiceNo"].transform("count")
        df["CountryTransactionCount"] = country_counts

        # Handle potential NaNs in numerical features
        for col in self.feature_columns:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median() if not df[col].median() != df[col].median() else 0.0)

        # Extract numerical matrix for scikit-learn
        X_num = df[self.feature_columns].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X_num)

        return df, X_scaled
