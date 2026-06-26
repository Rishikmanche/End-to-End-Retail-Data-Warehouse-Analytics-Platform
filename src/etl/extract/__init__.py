"""Data extraction module.

Handles reading raw data from CSV files with encoding detection,
schema validation, and quality metrics generation.
"""

from src.etl.extract.extractor import DataExtractor

__all__: list[str] = ["DataExtractor"]
