"""Data transformer module for the ETL pipeline.

Handles data normalization, outlier detection, and feature engineering to
prepare cleaned raw data for loading into the star schema.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataTransformer:
    """Transforms cleaned data, standardizes regions/categories, and engineers analytical features."""

    def __init__(self) -> None:
        self.logger = logger

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs the transformation pipeline on a cleaned DataFrame.

        Args:
            df: Cleaned input DataFrame.

        Returns:
            A transformed DataFrame ready for loading.
        """
        self.logger.info("Starting data transformation. Shape: %s", df.shape)
        
        transformed_df = df.copy()

        # 1. Normalize Category, Sub-Category, and Region names
        transformed_df = self.normalize_categories(transformed_df)
        transformed_df = self.normalize_regions(transformed_df)

        # 2. Perform Outlier Detection (adds flags, doesn't drop)
        transformed_df = self.detect_outliers(transformed_df, columns=["Sales", "Quantity", "Profit"])

        # 3. Feature Engineering
        transformed_df = self.engineer_features(transformed_df)

        self.logger.info("Finished data transformation. Shape: %s", transformed_df.shape)
        return transformed_df

    def normalize_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes category and sub-category names (casing, trimming, spelling corrections)."""
        if "Category" in df.columns:
            # Category standard mapping
            category_mapping = {
                "furniture": "Furniture",
                "furnitures": "Furniture",
                "office supplies": "Office Supplies",
                "officesupplies": "Office Supplies",
                "technology": "Technology",
                "tech": "Technology",
            }
            df["Category"] = df["Category"].str.lower().str.strip()
            df["Category"] = df["Category"].map(lambda x: category_mapping.get(x, x.title()))

        if "Sub-Category" in df.columns:
            df["Sub-Category"] = df["Sub-Category"].str.strip().str.title()
            # Handle specific abbreviations or naming mismatches
            sub_cat_mapping = {
                "Appliances": "Appliances",
                "Art": "Art",
                "Binders": "Binders",
                "Bookcases": "Bookcases",
                "Chairs": "Chairs",
                "Copiers": "Copiers",
                "Envelopes": "Envelopes",
                "Fasteners": "Fasteners",
                "Furnishings": "Furnishings",
                "Labels": "Labels",
                "Machines": "Machines",
                "Paper": "Paper",
                "Phones": "Phones",
                "Storage": "Storage",
                "Supplies": "Supplies",
                "Tables": "Tables",
                "Accessories": "Accessories",
            }
            # Clean and map if matching key exists
            df["Sub-Category"] = df["Sub-Category"].apply(lambda x: sub_cat_mapping.get(x, x))

        self.logger.debug("Normalized Category and Sub-Category values.")
        return df

    def normalize_regions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes region, country, state, and city names."""
        if "Region" in df.columns:
            region_mapping = {
                "east": "East",
                "west": "West",
                "central": "Central",
                "south": "South",
                "e": "East",
                "w": "West",
                "c": "Central",
                "s": "South",
            }
            df["Region"] = df["Region"].str.lower().str.strip()
            df["Region"] = df["Region"].map(lambda x: region_mapping.get(x, x.title()))

        if "Country" in df.columns:
            df["Country"] = df["Country"].str.strip()
            country_mapping = {
                "US": "United States",
                "USA": "United States",
                "United States of America": "United States",
            }
            df["Country"] = df["Country"].replace(country_mapping)

        if "State" in df.columns:
            df["State"] = df["State"].str.strip().str.title()

        if "City" in df.columns:
            df["City"] = df["City"].str.strip().str.title()

        self.logger.debug("Normalized geography and Region fields.")
        return df

    def detect_outliers(self, df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """Detects outliers using the Interquartile Range (IQR) method.

        Adds a boolean column `is_outlier` representing if the record is an outlier
        in any of the specified columns.
        """
        outlier_mask = pd.Series(False, index=df.index)
        
        for col in columns:
            if col in df.columns:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                col_outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
                outlier_mask = outlier_mask | col_outliers
                self.logger.debug(
                    "Column '%s' outlier bounds: [%.2f, %.2f]. Found %d outliers.",
                    col, lower_bound, upper_bound, col_outliers.sum()
                )

        df["is_outlier"] = outlier_mask
        self.logger.info("Outlier detection completed. Marked %d total rows as outliers.", outlier_mask.sum())
        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineers derived variables from raw data:

        - Revenue = Sales * (1 - Discount)
        - Profit Margin = Profit / Sales (or Profit / Revenue)
        - Order to Ship Days = Ship Date - Order Date
        - Date granularities: Year, Quarter, Month, Month Name, Day of Week
        """
        # 1. Net Revenue: Sales * (1 - Discount)
        if "Sales" in df.columns and "Discount" in df.columns:
            # Discount might be percentage (0.2) or already deducted.
            # Assuming Discount is a fraction from 0.0 to 1.0 (e.g. 0.2 represents 20%).
            df["Revenue"] = df["Sales"] * (1.0 - df["Discount"])
        else:
            df["Revenue"] = df["Sales"]

        # 2. Profit Margin: Profit / Sales (handle zero Sales safely)
        if "Profit" in df.columns and "Sales" in df.columns:
            df["Profit_Margin"] = np.where(
                df["Sales"] > 0,
                df["Profit"] / df["Sales"],
                0.0
            )
            # Clip margins to realistic limits [-10, 1]
            df["Profit_Margin"] = df["Profit_Margin"].clip(lower=-10.0, upper=1.0)
        else:
            df["Profit_Margin"] = 0.0

        # 3. Order to Ship Days
        if "Order Date" in df.columns and "Ship Date" in df.columns:
            df["Order_to_Ship_Days"] = (df["Ship Date"] - df["Order Date"]).dt.days
        else:
            df["Order_to_Ship_Days"] = -1

        # 4. Date components (helpful for dimension mapping and testing)
        if "Order Date" in df.columns:
            df["Order_Year"] = df["Order Date"].dt.year
            df["Order_Quarter"] = df["Order Date"].dt.quarter
            df["Order_Month"] = df["Order Date"].dt.month
            df["Order_Month_Name"] = df["Order Date"].dt.strftime("%B")
            df["Order_Day_of_Week"] = df["Order Date"].dt.dayofweek
            df["Order_Day_Name"] = df["Order Date"].dt.strftime("%A")

        self.logger.debug("Feature engineering completed.")
        return df
