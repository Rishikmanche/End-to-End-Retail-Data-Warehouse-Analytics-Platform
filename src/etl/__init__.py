"""
ETL Pipeline Package for Retail Data Warehouse.

This package provides a complete Extract, Transform, Load (ETL) pipeline
for processing retail sales data and loading it into a star-schema
data warehouse.

Modules:
    extract: Data extraction from CSV files with validation and quality checks.
    transform: Data cleaning and transformation with feature engineering.
    load: Data loading into the warehouse with dimension and fact table management.
    pipeline: Pipeline orchestration tying all stages together.
"""

__all__: list[str] = [
    "extract",
    "transform",
    "load",
    "pipeline",
]
