"""Unit tests for the ETL cleaning and transformation modules."""

from __future__ import annotations

import pandas as pd
import pytest

from src.etl.transform.clean import DataCleaner
from src.etl.transform.transformer import DataTransformer


def test_cleaner_trim_whitespace() -> None:
    """Verifies that whitespace is correctly trimmed from string columns."""
    df = pd.DataFrame({"Customer Name": ["  John Smith  ", "Jane Doe   ", "  Bob"]})
    cleaner = DataCleaner()
    df_clean = cleaner.trim_whitespace(df)
    
    assert list(df_clean["Customer Name"]) == ["John Smith", "Jane Doe", "Bob"]


def test_cleaner_handle_missing_values(sample_raw_data: pd.DataFrame) -> None:
    """Verifies that missing critical values trigger rows deletion, and non-critical are filled."""
    # Create copy and introduce null values
    df = sample_raw_data.copy()
    # Add row with critical null (Sales)
    df.loc[len(df)] = [4, "CA-2022-1003", "2022-05-10", "2022-05-14", "Standard Class", "CS-12", "Alice", "Corporate", "USA", "LA", "CA", None, "West", "TEC-PH-1", "Technology", "Phones", "Phone", None, 2, 0.0, None]
    # Add row with non-critical null (Postal Code)
    df.loc[len(df)] = [5, "CA-2022-1004", "2022-05-10", "2022-05-14", "Standard Class", "CS-12", "Alice", "Corporate", "USA", "LA", "CA", None, "West", "TEC-PH-1", "Technology", "Phones", "Phone", 100.0, 2, 0.0, 20.0]

    cleaner = DataCleaner()
    df_fixed = cleaner.handle_missing_values(df)

    # Row 4 should be dropped because Sales is Null. Row 5 should remain but Postal Code filled.
    assert len(df_fixed) == 4
    assert df_fixed.iloc[3]["Postal Code"] == "Unknown"


def test_cleaner_remove_invalid_records() -> None:
    """Verifies that records violating range/business rules are removed."""
    df = pd.DataFrame({
        "Quantity": [1, -5, 3],
        "Discount": [0.1, 0.2, 1.5],  # 1.5 is invalid (> 1.0)
        "Order Date": [pd.Timestamp("2022-01-01"), pd.Timestamp("2022-01-05"), pd.Timestamp("2022-01-05")],
        "Ship Date": [pd.Timestamp("2022-01-05"), pd.Timestamp("2022-01-01"), pd.Timestamp("2022-01-01")]  # Row 3 order > ship
    })
    
    cleaner = DataCleaner()
    df_valid = cleaner.remove_invalid_records(df)

    # Row 0: Valid
    # Row 1: Quantity -5 (invalid)
    # Row 2: Discount 1.5 (invalid)
    # Row 3: Order > Ship (invalid)
    assert len(df_valid) == 1
    assert df_valid.iloc[0]["Quantity"] == 1


def test_transformer_normalize_category() -> None:
    """Verifies category names mapping to standard casing."""
    df = pd.DataFrame({
        "Category": ["furniture", "officesupplies", "technology", "tech"],
        "Sub-Category": ["bookcases", "binders", "phones", "copiers"]
    })
    transformer = DataTransformer()
    df_norm = transformer.normalize_categories(df)

    assert list(df_norm["Category"]) == ["Furniture", "Office Supplies", "Technology", "Technology"]
    assert list(df_norm["Sub-Category"]) == ["Bookcases", "Binders", "Phones", "Copiers"]


def test_transformer_engineer_features(sample_raw_data: pd.DataFrame) -> None:
    """Verifies feature engineering of Revenue, Profit Margin, and Date components."""
    # Ensure Order Date and Ship Date are converted to datetimes
    df = sample_raw_data.copy()
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    df["Ship Date"] = pd.to_datetime(df["Ship Date"])
    
    transformer = DataTransformer()
    df_feats = transformer.engineer_features(df)

    # Row 1: Sales 250.00, Discount 0.0 -> Revenue 250.00, Margin 50/250 = 0.2
    # Row 2: Sales 120.00, Discount 0.1 -> Revenue 120 * 0.9 = 108.00, Margin 10/120 = 0.0833
    assert df_feats.iloc[0]["Revenue"] == 250.00
    assert df_feats.iloc[0]["Profit_Margin"] == 0.20
    
    assert df_feats.iloc[1]["Revenue"] == 108.00
    assert round(df_feats.iloc[1]["Profit_Margin"], 4) == 0.0833
    
    assert df_feats.iloc[0]["Order_Year"] == 2022
    assert df_feats.iloc[0]["Order_Month_Name"] == "May"
    assert df_feats.iloc[0]["Order_to_Ship_Days"] == 4
