"""Unit tests for the ETL extraction module."""

from __future__ import annotations

from pathlib import Path
import pytest
import pandas as pd

from src.etl.extract.extractor import DataExtractor
from src.utils.helpers import validate_dataframe_schema


def test_extract_valid_csv(sample_csv: Path) -> None:
    """Verifies that the extractor reads and parses a valid CSV correctly."""
    extractor = DataExtractor(sample_csv.parent)
    df = extractor.extract(sample_csv.name)

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 3
    assert "Order ID" in df.columns
    assert "Sales" in df.columns


def test_extract_missing_file() -> None:
    """Verifies that the extractor handles missing files by raising FileNotFoundExtractionError."""
    from src.etl.extract.extractor import FileNotFoundExtractionError
    with pytest.raises(FileNotFoundExtractionError):
        DataExtractor(Path("./non_existent_data_dir"))


def test_extract_missing_columns(tmp_path: Path) -> None:
    """Verifies that schema validation raises SchemaValidationError if required columns are missing."""
    from src.etl.extract.extractor import SchemaValidationError
    invalid_data = {
        "Order ID": ["CA-2022-1001"],
        "Sales": [250.00]
        # Missing all other required columns like Customer ID, Product ID, etc.
    }
    df_invalid = pd.DataFrame(invalid_data)
    csv_file = tmp_path / "invalid_columns.csv"
    df_invalid.to_csv(csv_file, index=False)

    extractor = DataExtractor(tmp_path)
    with pytest.raises(SchemaValidationError):
        extractor.extract(csv_file.name)

