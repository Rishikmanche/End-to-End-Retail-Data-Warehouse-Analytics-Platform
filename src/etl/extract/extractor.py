"""Data extraction module for the Retail Data Warehouse ETL pipeline.

Provides the DataExtractor class for reading raw CSV data with automatic
encoding detection, schema validation, duplicate detection, and extraction
metrics generation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chardet
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class ExtractionError(Exception):
    """Raised when a general extraction failure occurs."""


class SchemaValidationError(ExtractionError):
    """Raised when the extracted DataFrame does not match the expected schema."""


class FileNotFoundExtractionError(ExtractionError):
    """Raised when the source data file cannot be found."""


# ---------------------------------------------------------------------------
# Expected raw CSV columns
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS: list[str] = [
    "Row ID",
    "Order ID",
    "Order Date",
    "Ship Date",
    "Ship Mode",
    "Customer ID",
    "Customer Name",
    "Segment",
    "Country",
    "City",
    "State",
    "Postal Code",
    "Region",
    "Product ID",
    "Category",
    "Sub-Category",
    "Product Name",
    "Sales",
    "Quantity",
    "Discount",
    "Profit",
]


# ---------------------------------------------------------------------------
# DataExtractor
# ---------------------------------------------------------------------------


class DataExtractor:
    """Extracts raw data from CSV files with validation and quality checks.

    The extractor performs the following steps:
        1. Validates that the source file exists.
        2. Detects file encoding using *chardet*.
        3. Reads the CSV into a ``pandas.DataFrame``.
        4. Validates the schema against the expected column list.
        5. Detects and flags duplicate rows.
        6. Logs comprehensive extraction metrics.

    Attributes:
        data_dir: Resolved ``Path`` to the directory containing source files.
    """

    def __init__(self, data_dir: str | Path) -> None:
        """Initialise the DataExtractor.

        Args:
            data_dir: Path to the directory containing raw data files.

        Raises:
            FileNotFoundExtractionError: If ``data_dir`` does not exist.
        """
        self.data_dir = Path(data_dir).resolve()
        if not self.data_dir.exists():
            raise FileNotFoundExtractionError(
                f"Data directory does not exist: {self.data_dir}"
            )
        logger.info("DataExtractor initialised with data_dir=%s", self.data_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, filename: str) -> pd.DataFrame:
        """Extract and validate data from a CSV file.

        Args:
            filename: Name of the CSV file (relative to ``data_dir``).

        Returns:
            A validated ``pandas.DataFrame`` with a ``_is_duplicate`` flag
            column appended.

        Raises:
            FileNotFoundExtractionError: If the file does not exist.
            SchemaValidationError: If the schema does not match expectations.
            ExtractionError: On any other read/parse failure.
        """
        filepath = self.data_dir / filename
        logger.info("Starting extraction for file: %s", filepath)

        # 1. Validate file exists
        if not filepath.is_file():
            raise FileNotFoundExtractionError(
                f"Source file not found: {filepath}"
            )

        try:
            # 2. Detect encoding
            encoding = self._detect_encoding(filepath)
            logger.info("Detected encoding: %s", encoding)

            # 3. Read CSV
            df = pd.read_csv(filepath, encoding=encoding)
            logger.info(
                "CSV loaded — rows=%d, columns=%d", len(df), len(df.columns)
            )

            # 4. Validate schema
            self._validate_schema(df)
            logger.info("Schema validation passed.")

            # 5. Detect duplicates
            df = self._detect_duplicates(df)

            # 6. Log metrics
            metrics = self._get_extraction_metrics(df, filepath)
            logger.info("Extraction metrics: %s", metrics)

            return df

        except (SchemaValidationError, FileNotFoundExtractionError):
            raise
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract data from {filepath}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_encoding(self, filepath: Path) -> str:
        """Detect file encoding using *chardet*.

        Reads up to the first 100 000 bytes of the file to make a best-guess
        determination of the character encoding.

        Args:
            filepath: Path to the file to analyse.

        Returns:
            The detected encoding string (e.g. ``'utf-8'``, ``'ascii'``).
        """
        sample_size = 100_000
        with open(filepath, "rb") as fh:
            raw_data = fh.read(sample_size)

        result = chardet.detect(raw_data)
        encoding: str = result.get("encoding", "utf-8") or "utf-8"
        confidence: float = result.get("confidence", 0.0) or 0.0

        logger.debug(
            "chardet result — encoding=%s, confidence=%.2f",
            encoding,
            confidence,
        )

        if confidence < 0.5:
            logger.warning(
                "Low encoding confidence (%.2f) for %s — defaulting to utf-8",
                confidence,
                filepath,
            )
            encoding = "utf-8"

        return encoding

    def _validate_schema(self, df: pd.DataFrame) -> None:
        """Validate that the DataFrame contains the expected columns.

        Args:
            df: The extracted DataFrame.

        Raises:
            SchemaValidationError: If required columns are missing or
                unexpected columns are present.
        """
        actual = set(df.columns.str.strip())
        expected = set(EXPECTED_COLUMNS)

        missing = expected - actual
        extra = actual - expected

        if missing:
            msg = (
                f"Schema validation failed — missing columns: "
                f"{sorted(missing)}"
            )
            logger.error(msg)
            if extra:
                logger.warning("Unexpected extra columns found: %s", sorted(extra))
            raise SchemaValidationError(msg)

        if extra:
            logger.warning(
                "Extra columns detected (will be kept): %s", sorted(extra)
            )

    def _detect_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect and flag fully-duplicate rows.

        A boolean column ``_is_duplicate`` is appended.  The *first*
        occurrence is kept as ``False``; subsequent duplicates are ``True``.

        Args:
            df: The DataFrame to inspect.

        Returns:
            The same DataFrame with the ``_is_duplicate`` column added.
        """
        df = df.copy()
        df["_is_duplicate"] = df.duplicated(keep="first")
        dup_count: int = int(df["_is_duplicate"].sum())

        if dup_count > 0:
            logger.warning("Detected %d duplicate rows.", dup_count)
        else:
            logger.info("No duplicate rows detected.")

        return df

    def _get_extraction_metrics(
        self, df: pd.DataFrame, filepath: Path
    ) -> dict[str, Any]:
        """Generate extraction metrics.

        Args:
            df: The extracted (and duplicate-flagged) DataFrame.
            filepath: The source file path (used for file-size calculation).

        Returns:
            A dictionary containing extraction metrics.
        """
        file_size_bytes = os.path.getsize(filepath)
        null_counts: dict[str, int] = df.isnull().sum().to_dict()
        null_counts = {k: v for k, v in null_counts.items() if v > 0}

        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 3),
            "null_counts": null_counts,
            "duplicate_count": int(df.get("_is_duplicate", pd.Series(dtype=bool)).sum()),
        }
