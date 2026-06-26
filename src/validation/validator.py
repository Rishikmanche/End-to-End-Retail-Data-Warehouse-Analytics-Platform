"""Data quality validation module.

Defines a comprehensive validation framework to check data types, nulls, ranges,
duplicates, primary keys, referential integrity, and business rules, generating
structured validation reports.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from src.models.dim_category import DimCategory
from src.models.dim_customer import DimCustomer
from src.models.dim_product import DimProduct
from src.models.dim_region import DimRegion
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Represents the output of a single data quality validation check."""
    rule_name: str
    passed: bool
    severity: str  # 'critical', 'warning', 'info'
    message: str
    affected_rows: int
    total_rows: int
    details: dict | None = None


@dataclass
class ValidationReport:
    """Represents a full suite data quality report containing multiple checks."""
    timestamp: datetime.datetime
    stage: str
    total_checks: int
    passed: int
    failed: int
    warnings: int
    quality_score: float  # 0 to 100
    results: list[ValidationResult]

    def to_dict(self) -> dict:
        """Converts the report to a dictionary representation."""
        report_dict = asdict(self)
        report_dict["timestamp"] = self.timestamp.isoformat()
        return report_dict

    def to_json(self, filepath: str | Path) -> None:
        """Writes the report to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    def summary(self) -> str:
        """Generates a human-readable summary string of the validation report."""
        return (
            f"=== DATA QUALITY REPORT ({self.stage.upper()}) ===\n"
            f"Timestamp: {self.timestamp}\n"
            f"Quality Score: {self.quality_score:.2f}%\n"
            f"Total Checks: {self.total_checks} | Passed: {self.passed} | Failed: {self.failed} | Warnings: {self.warnings}\n"
            f"Status: {'PASSED' if self.failed == 0 else 'FAILED'}\n"
            f"=================================================="
        )


class DataValidator:
    """Validates Pandas DataFrames against quality criteria before staging/loading."""

    def __init__(self, engine: Engine | None = None) -> None:
        self.engine = engine
        self.logger = logger
        if self.engine:
            self.SessionLocal = sessionmaker(bind=self.engine)

    def validate(self, df: pd.DataFrame, stage: str = "raw") -> ValidationReport:
        """Runs all validations for the specified data warehouse pipeline stage.

        Args:
            df: Input pandas DataFrame to validate.
            stage: The stage identifier (e.g. 'raw', 'clean', 'transformed').

        Returns:
            A ValidationReport object.
        """
        self.logger.info("Starting data quality validation for stage: %s", stage)
        results: list[ValidationResult] = []

        # 1. Primary Key validation / Uniqueness
        results.append(self.check_primary_keys(df, ["Row ID" if "Row ID" in df.columns else "Order ID"]))

        # 2. Check duplicate keys (business composite key Order ID + Product ID)
        results.append(self.check_duplicates(df, ["Order ID", "Product ID"]))

        # 3. Null validation on critical fields
        critical_cols = ["Order ID", "Customer ID", "Product ID", "Sales", "Quantity"]
        results.extend(self.check_nulls(df, critical_cols))

        # 4. Check data types (validate numeric columns are actually float/int)
        type_rules = {
            "Sales": "float",
            "Quantity": "int",
            "Discount": "float",
            "Profit": "float"
        }
        results.extend(self.check_data_types(df, type_rules))

        # 5. Range validation on financial metrics
        range_rules = {
            "Sales": {"min": 0.0001, "max": 100000.0},
            "Quantity": {"min": 1, "max": 200},
            "Discount": {"min": 0.0, "max": 1.0},
            "Profit": {"min": -20000.0, "max": 50000.0}
        }
        results.extend(self.check_ranges(df, range_rules))

        # 6. Business rules validation (Order Date vs Ship Date)
        results.extend(self.check_business_rules(df))

        # 7. Referential Integrity checks (if DB engine is available)
        if self.engine and stage == "post_load":
            results.extend(self.check_referential_integrity(df))

        # Compile report
        report = self.generate_quality_report(results, stage)
        self.logger.info("Validation completed. %s", report.summary())
        return report

    def check_nulls(self, df: pd.DataFrame, critical_columns: list[str]) -> list[ValidationResult]:
        """Validates that critical columns contain no null values."""
        results = []
        total_rows = len(df)

        for col in critical_columns:
            if col in df.columns:
                null_count = int(df[col].isnull().sum())
                passed = (null_count == 0)
                results.append(ValidationResult(
                    rule_name=f"null_check_{col}",
                    passed=passed,
                    severity="critical" if col != "Discount" else "warning",
                    message=f"Column '{col}' has {null_count} null values.",
                    affected_rows=null_count,
                    total_rows=total_rows,
                    details={"null_count": null_count} if null_count > 0 else None
                ))
            else:
                results.append(ValidationResult(
                    rule_name=f"null_check_{col}",
                    passed=False,
                    severity="critical",
                    message=f"Critical column '{col}' is missing from DataFrame.",
                    affected_rows=total_rows,
                    total_rows=total_rows
                ))
        return results

    def check_duplicates(self, df: pd.DataFrame, key_columns: list[str]) -> ValidationResult:
        """Validates that composite business key has no duplicates."""
        total_rows = len(df)
        if not all(col in df.columns for col in key_columns):
            missing = [col for col in key_columns if col not in df.columns]
            return ValidationResult(
                rule_name="composite_duplicates_check",
                passed=False,
                severity="warning",
                message=f"Duplicate check skipped due to missing columns: {missing}",
                affected_rows=total_rows,
                total_rows=total_rows
            )
        
        duplicates = df.duplicated(subset=key_columns, keep=False)
        duplicate_count = int(duplicates.sum())
        passed = (duplicate_count == 0)

        return ValidationResult(
            rule_name="composite_duplicates_check",
            passed=passed,
            severity="warning",
            message=f"Found {duplicate_count} duplicate records based on keys {key_columns}.",
            affected_rows=duplicate_count,
            total_rows=total_rows,
            details={"keys": key_columns, "duplicate_count": duplicate_count} if duplicate_count > 0 else None
        )

    def check_ranges(self, df: pd.DataFrame, range_rules: dict) -> list[ValidationResult]:
        """Validates numeric ranges for numeric columns."""
        results = []
        total_rows = len(df)

        for col, rules in range_rules.items():
            if col in df.columns:
                series = pd.to_numeric(df[col], errors="coerce")
                min_val = rules.get("min")
                max_val = rules.get("max")
                
                out_of_bounds = pd.Series(False, index=df.index)
                if min_val is not None:
                    out_of_bounds = out_of_bounds | (series < min_val)
                if max_val is not None:
                    out_of_bounds = out_of_bounds | (series > max_val)
                
                violation_count = int(out_of_bounds.sum())
                passed = (violation_count == 0)
                
                results.append(ValidationResult(
                    rule_name=f"range_check_{col}",
                    passed=passed,
                    severity="warning",
                    message=f"Column '{col}' has {violation_count} values outside range [{min_val}, {max_val}].",
                    affected_rows=violation_count,
                    total_rows=total_rows,
                    details={"min": min_val, "max": max_val, "violations": violation_count} if violation_count > 0 else None
                ))
        return results

    def check_data_types(self, df: pd.DataFrame, type_rules: dict) -> list[ValidationResult]:
        """Validates columns match expected target pandas/numpy types."""
        results = []
        total_rows = len(df)

        for col, expected_type in type_rules.items():
            if col in df.columns:
                passed = True
                fail_count = 0
                
                if expected_type == "int":
                    # Check if series can be converted to int without loss
                    converted = pd.to_numeric(df[col], errors="coerce")
                    is_null = converted.isnull()
                    is_not_int = (converted % 1 != 0)
                    fail_count = int((is_null & df[col].notnull() | is_not_int).sum())
                    passed = (fail_count == 0)
                elif expected_type == "float":
                    converted = pd.to_numeric(df[col], errors="coerce")
                    fail_count = int((converted.isnull() & df[col].notnull()).sum())
                    passed = (fail_count == 0)
                
                results.append(ValidationResult(
                    rule_name=f"type_check_{col}_{expected_type}",
                    passed=passed,
                    severity="critical",
                    message=f"Column '{col}' data type check for {expected_type} failed for {fail_count} rows.",
                    affected_rows=fail_count,
                    total_rows=total_rows
                ))
        return results

    def check_primary_keys(self, df: pd.DataFrame, pk_columns: list[str]) -> ValidationResult:
        """Validates primary key uniqueness and non-nullability."""
        total_rows = len(df)
        if not all(col in df.columns for col in pk_columns):
            return ValidationResult(
                rule_name="pk_uniqueness_check",
                passed=False,
                severity="critical",
                message=f"PK uniqueness check failed: missing PK columns: {pk_columns}",
                affected_rows=total_rows,
                total_rows=total_rows
            )
            
        null_pks = df[pk_columns].isnull().any(axis=1)
        null_count = int(null_pks.sum())
        
        duplicates = df.duplicated(subset=pk_columns, keep=False)
        duplicate_count = int(duplicates.sum())
        
        passed = (null_count == 0 and duplicate_count == 0)
        
        return ValidationResult(
            rule_name="pk_uniqueness_check",
            passed=passed,
            severity="critical",
            message=f"PK columns uniqueness check: {null_count} null PKs, {duplicate_count} duplicate PKs.",
            affected_rows=null_count + duplicate_count,
            total_rows=total_rows,
            details={"null_pks": null_count, "duplicate_pks": duplicate_count}
        )

    def check_business_rules(self, df: pd.DataFrame) -> list[ValidationResult]:
        """Validates specific business constraints, like Order Date vs Ship Date."""
        results = []
        total_rows = len(df)

        if "Order Date" in df.columns and "Ship Date" in df.columns:
            # Order Date and Ship Date must be parsed as datetimes
            order_date = pd.to_datetime(df["Order Date"], errors="coerce")
            ship_date = pd.to_datetime(df["Ship Date"], errors="coerce")
            
            invalid_dates = (order_date > ship_date)
            invalid_count = int(invalid_dates.sum())
            passed = (invalid_count == 0)

            results.append(ValidationResult(
                rule_name="business_rule_order_date_before_ship_date",
                passed=passed,
                severity="critical",
                message=f"Business Rule: Order Date must be <= Ship Date. Violated by {invalid_count} records.",
                affected_rows=invalid_count,
                total_rows=total_rows,
                details={"violations": invalid_count} if invalid_count > 0 else None
            ))
        else:
            results.append(ValidationResult(
                rule_name="business_rule_order_date_before_ship_date",
                passed=False,
                severity="critical",
                message="Order Date or Ship Date columns missing from DataFrame.",
                affected_rows=total_rows,
                total_rows=total_rows
            ))
        return results

    def check_referential_integrity(self, df: pd.DataFrame) -> list[ValidationResult]:
        """Checks if foreign key references in the DataFrame exist in the database."""
        results = []
        total_rows = len(df)
        
        if not self.engine:
            return results

        with self.SessionLocal() as session:
            # 1. Customer reference check
            existing_custs = set(r[0] for r in session.execute(select(DimCustomer.customer_id)).fetchall())
            missing_custs = df[~df["Customer ID"].isin(existing_custs)]["Customer ID"].dropna().nunique()
            results.append(ValidationResult(
                rule_name="ref_integrity_customer_id",
                passed=(missing_custs == 0),
                severity="critical",
                message=f"Found {missing_custs} unique Customer IDs missing from dim_customer.",
                affected_rows=missing_custs,
                total_rows=total_rows
            ))

            # 2. Product reference check
            existing_prods = set(r[0] for r in session.execute(select(DimProduct.product_id)).fetchall())
            missing_prods = df[~df["Product ID"].isin(existing_prods)]["Product ID"].dropna().nunique()
            results.append(ValidationResult(
                rule_name="ref_integrity_product_id",
                passed=(missing_prods == 0),
                severity="critical",
                message=f"Found {missing_prods} unique Product IDs missing from dim_product.",
                affected_rows=missing_prods,
                total_rows=total_rows
            ))

            # 3. Region reference check
            existing_regions = set(
                (r[0], r[1], r[2])
                for r in session.execute(select(DimRegion.country, DimRegion.state, DimRegion.city)).fetchall()
            )
            df_regions = df[["Country", "State", "City"]].dropna().drop_duplicates()
            missing_regions = 0
            for _, r in df_regions.iterrows():
                if (r["Country"], r["State"], r["City"]) not in existing_regions:
                    missing_regions += 1
                    
            results.append(ValidationResult(
                rule_name="ref_integrity_region_country_state_city",
                passed=(missing_regions == 0),
                severity="critical",
                message=f"Found {missing_regions} geographical keys missing from dim_region.",
                affected_rows=missing_regions,
                total_rows=total_rows
            ))
            
        return results

    def generate_quality_report(self, results: list[ValidationResult], stage: str) -> ValidationReport:
        """Compiles validation results into a ValidationReport with quality scores."""
        total_checks = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed and r.severity == "critical")
        warnings = sum(1 for r in results if not r.passed and r.severity == "warning")

        # Compute data quality score: weighted penalty
        # Critical failures reduce score significantly, warnings less so.
        # Starting with 100.
        score = 100.0
        for r in results:
            if not r.passed:
                if r.severity == "critical":
                    score -= 15.0  # -15 per critical check failure
                elif r.severity == "warning":
                    score -= 5.0   # -5 per warning check failure
        
        # Clamp score between 0.0 and 100.0
        score = max(0.0, min(100.0, score))

        return ValidationReport(
            timestamp=datetime.datetime.utcnow(),
            stage=stage,
            total_checks=total_checks,
            passed=passed,
            failed=failed,
            warnings=warnings,
            quality_score=score,
            results=results
        )
