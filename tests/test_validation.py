"""Unit tests for the Data Quality Validation framework."""

from __future__ import annotations

import pandas as pd
import pytest

from src.validation.validator import DataValidator


def test_validator_null_checks() -> None:
    """Verifies null validation triggers correct results."""
    df = pd.DataFrame({
        "Order ID": ["CA-2022-001", None],
        "Sales": [10.50, 20.00]
    })
    
    validator = DataValidator()
    results = validator.check_nulls(df, ["Order ID", "Sales"])

    # Order ID should fail null check, Sales should pass
    assert len(results) == 2
    
    order_id_check = next(r for r in results if r.rule_name == "null_check_Order ID")
    sales_check = next(r for r in results if r.rule_name == "null_check_Sales")
    
    assert order_id_check.passed is False
    assert order_id_check.affected_rows == 1
    assert sales_check.passed is True


def test_validator_duplicates_check() -> None:
    """Verifies composite key duplicates check flag duplicates."""
    df = pd.DataFrame({
        "Order ID": ["CA-2022-01", "CA-2022-01", "CA-2022-02"],
        "Product ID": ["TEC-1", "TEC-1", "OFF-2"]
    })
    
    validator = DataValidator()
    result = validator.check_duplicates(df, ["Order ID", "Product ID"])

    assert result.passed is False
    assert result.affected_rows == 2


def test_validator_range_checks() -> None:
    """Verifies range check logic bounds numbers."""
    df = pd.DataFrame({
        "Sales": [100.0, -5.0, 500000.0],  # -5 is below min, 500000 is above max
        "Discount": [0.0, 0.2, 1.2]        # 1.2 is above max
    })
    
    validator = DataValidator()
    range_rules = {
        "Sales": {"min": 0.0, "max": 100000.0},
        "Discount": {"min": 0.0, "max": 1.0}
    }
    
    results = validator.check_ranges(df, range_rules)

    sales_check = next(r for r in results if r.rule_name == "range_check_Sales")
    discount_check = next(r for r in results if r.rule_name == "range_check_Discount")

    assert sales_check.passed is False
    assert sales_check.affected_rows == 2  # -5 and 500000
    
    assert discount_check.passed is False
    assert discount_check.affected_rows == 1  # 1.2


def test_validator_business_rules() -> None:
    """Verifies that business rules are evaluated and flag violations."""
    df = pd.DataFrame({
        "Order Date": ["2022-01-10", "2022-01-10"],
        "Ship Date": ["2022-01-15", "2022-01-05"]  # Row 1 is invalid
    })
    
    validator = DataValidator()
    results = validator.check_business_rules(df)

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].affected_rows == 1


def test_validator_full_report(sample_raw_data: pd.DataFrame) -> None:
    """Verifies compiling quality reports over the complete dataset."""
    validator = DataValidator()
    report = validator.validate(sample_raw_data, stage="raw")

    assert report.total_checks > 0
    assert report.quality_score == 100.0
    assert report.failed == 0
