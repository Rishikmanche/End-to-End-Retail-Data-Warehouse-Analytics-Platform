"""Data cleaner module for the ETL pipeline.

Handles duplicate removal, missing values, data type coercion, whitespace trimming,
and invalid record filtering based on business rules.
"""

from __future__ import annotations

import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """Cleans and standardizes raw retail data before transformation."""

    def __init__(self) -> None:
        self.logger = logger

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main cleaning pipeline.

        Args:
            df: Input raw pandas DataFrame.

        Returns:
            A cleaned pandas DataFrame.
        """
        self.logger.info("Starting data cleaning process. Input shape: %s", df.shape)
        
        # Avoid modifying the original DataFrame in place
        cleaned_df = df.copy()

        # 1. Trim whitespace from string columns
        cleaned_df = self.trim_whitespace(cleaned_df)

        # 2. Fix data types
        cleaned_df = self.fix_data_types(cleaned_df)

        # 3. Handle missing values
        cleaned_df = self.handle_missing_values(cleaned_df)

        # 4. Remove duplicate rows
        cleaned_df = self.remove_duplicates(cleaned_df)

        # 5. Filter out invalid records based on business constraints
        cleaned_df = self.remove_invalid_records(cleaned_df)

        self.logger.info("Finished data cleaning process. Output shape: %s", cleaned_df.shape)
        return cleaned_df

    def trim_whitespace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Trims whitespace from string columns."""
        string_cols = df.select_dtypes(include=["object", "string"]).columns
        for col in string_cols:
            df[col] = df[col].astype(str).str.strip()
        self.logger.debug("Trimmed whitespace on string columns: %s", list(string_cols))
        return df

    def fix_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Coerces columns to their appropriate types."""
        # Convert numeric columns
        numeric_conversions = {
            "Sales": "float64",
            "Quantity": "int64",
            "Discount": "float64",
            "Profit": "float64",
        }
        for col, dtype in numeric_conversions.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                # Fill NaN with 0 for numeric fields before converting to int/float if needed,
                # but let handle_missing_values handle nulls.
        
        # Convert date columns
        date_cols = ["Order Date", "Ship Date"]
        for col in date_cols:
            if col in df.columns:
                # Support multiple date formats during parse
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Convert postal code to string
        if "Postal Code" in df.columns:
            # Handle float conversions from CSV (like 90024.0 -> 90024)
            df["Postal Code"] = df["Postal Code"].fillna("Unknown")
            df["Postal Code"] = df["Postal Code"].apply(
                lambda x: str(int(float(x))) if str(x).endswith(".0") or isinstance(x, (int, float)) and not pd.isna(x) else str(x)
            )

        self.logger.debug("Completed data type coercion.")
        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handles missing values using drop/fill/interpolate strategies."""
        # Critical columns that must not be null (otherwise drop row)
        critical_cols = ["Order ID", "Customer ID", "Product ID", "Sales", "Quantity", "Profit"]
        initial_rows = len(df)
        df = df.dropna(subset=[col for col in critical_cols if col in df.columns])
        dropped_rows = initial_rows - len(df)
        if dropped_rows > 0:
            self.logger.warning("Dropped %d rows with missing critical fields.", dropped_rows)

        # Fill other missing values
        if "Postal Code" in df.columns:
            df["Postal Code"] = df["Postal Code"].replace("nan", "Unknown").fillna("Unknown")
        if "Customer Name" in df.columns:
            df["Customer Name"] = df["Customer Name"].fillna("Unknown Customer")
        if "Segment" in df.columns:
            df["Segment"] = df["Segment"].fillna("Consumer")
        if "Country" in df.columns:
            df["Country"] = df["Country"].fillna("United States")
        if "City" in df.columns:
            df["City"] = df["City"].fillna("Unknown City")
        if "State" in df.columns:
            df["State"] = df["State"].fillna("Unknown State")
        if "Region" in df.columns:
            df["Region"] = df["Region"].fillna("Unknown Region")
        if "Sub-Category" in df.columns:
            df["Sub-Category"] = df["Sub-Category"].fillna("Unknown Sub-Category")

        # Log null counts remaining
        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        if not cols_with_nulls.empty:
            self.logger.warning("Remaining nulls after cleaning: %s", cols_with_nulls.to_dict())

        return df

    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes duplicate transactions based on composite unique key.

        For retail sales data, Row ID or Order ID + Product ID are standard.
        """
        initial_len = len(df)
        # Unique identifier in Superstore is Row ID, but Order ID + Product ID is the business key
        dup_keys = ["Order ID", "Product ID"]
        if all(col in df.columns for col in dup_keys):
            df = df.drop_duplicates(subset=dup_keys, keep="first")
        else:
            df = df.drop_duplicates(keep="first")
        
        dups_removed = initial_len - len(df)
        if dups_removed > 0:
            self.logger.info("Removed %d duplicate rows.", dups_removed)
        return df

    def remove_invalid_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filters out records that violate business logic constraints."""
        initial_len = len(df)

        # 1. Quantity must be greater than zero
        if "Quantity" in df.columns:
            df = df[df["Quantity"] > 0]

        # 2. Discount must be between 0 and 1
        if "Discount" in df.columns:
            df = df[(df["Discount"] >= 0.0) & (df["Discount"] <= 1.0)]

        # 3. Order Date must be less than or equal to Ship Date
        if "Order Date" in df.columns and "Ship Date" in df.columns:
            df = df[df["Order Date"] <= df["Ship Date"]]

        invalid_count = initial_len - len(df)
        if invalid_count > 0:
            self.logger.warning("Filtered out %d invalid records violating business constraints.", invalid_count)
        return df
