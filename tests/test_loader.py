"""Integration tests for database loading and SCD Type 2 tracking."""

from __future__ import annotations

import datetime
import pandas as pd
import pytest
from sqlalchemy import select

from src.etl.load.loader import DataLoader
from src.models.dim_category import DimCategory
from src.models.dim_customer import DimCustomer
from src.models.dim_product import DimProduct
from src.models.dim_region import DimRegion
from src.models.fact_sales import FactSales


def test_loader_date_dimension(test_session, sample_raw_data) -> None:
    """Verifies loader generates date dimensions properly."""
    loader = DataLoader(test_session.get_bind())
    
    # conftest pre-seeded dates, load_date_dimension checks for duplicates and inserts missing
    # Let's verify we can call it without error
    loaded = loader.load_date_dimension(sample_raw_data)
    # Since dates are already pre-loaded in conftest, loaded count should be 0
    assert loaded == 0


def test_loader_category_dimension(test_session, sample_raw_data) -> None:
    """Verifies unique categories and sub-categories are loaded."""
    loader = DataLoader(test_session.get_bind())
    
    loaded = loader.load_category_dimension(sample_raw_data)
    assert loaded == 3  # Technology-Phones, Furniture-Chairs, Office Supplies-Binders
    
    # Query database
    cats = test_session.scalars(select(DimCategory)).all()
    assert len(cats) == 3
    assert set(c.category_name for c in cats) == {"Technology", "Furniture", "Office Supplies"}


def test_loader_region_dimension(test_session, sample_raw_data) -> None:
    """Verifies geographic region records are loaded with constraints."""
    loader = DataLoader(test_session.get_bind())
    
    loaded = loader.load_region_dimension(sample_raw_data)
    # Los Angeles (duplicated in rows 1 and 2), New York City (row 3) -> 2 unique regions
    assert loaded == 2

    regions = test_session.scalars(select(DimRegion)).all()
    assert len(regions) == 2
    assert set(r.city for r in regions) == {"Los Angeles", "New York City"}


def test_loader_customer_scd2(test_session) -> None:
    """Verifies that changes in customer attributes trigger SCD Type 2 history tracking."""
    loader = DataLoader(test_session.get_bind())
    
    # 1. Insert new customer
    df_initial = pd.DataFrame({
        "Customer ID": ["CUST-999"],
        "Customer Name": ["Zack Miller"],
        "Segment": ["Consumer"],
        "Order Date": [pd.Timestamp("2022-01-01")]
    })
    
    loader.load_customer_dimension(df_initial)
    
    cust1 = test_session.scalar(
        select(DimCustomer).where(DimCustomer.customer_id == "CUST-999", DimCustomer.is_current == True)
    )
    assert cust1 is not None
    assert cust1.segment == "Consumer"
    assert cust1.effective_date == datetime.date(2022, 1, 1)
    assert cust1.expiry_date is None

    # 2. Update same customer segment (trigger SCD Type 2 change)
    df_changed = pd.DataFrame({
        "Customer ID": ["CUST-999"],
        "Customer Name": ["Zack Miller"],
        "Segment": ["Corporate"],  # Segment changed!
        "Order Date": [pd.Timestamp("2022-06-15")]
    })
    
    loader.load_customer_dimension(df_changed)
    
    test_session.expire_all()
    # Query all records for CUST-999
    records = test_session.scalars(
        select(DimCustomer).where(DimCustomer.customer_id == "CUST-999").order_by(DimCustomer.customer_key)
    ).all()
    
    assert len(records) == 2
    
    # Active record
    active = next(r for r in records if r.is_current)
    # Expired record
    expired = next(r for r in records if not r.is_current)

    assert expired.segment == "Consumer"
    assert expired.expiry_date == datetime.date(2022, 6, 14)
    
    assert active.segment == "Corporate"
    assert active.effective_date == datetime.date(2022, 6, 15)
    assert active.expiry_date is None


def test_loader_fact_sales(test_session, sample_raw_data) -> None:
    """Verifies that facts are loaded and surrogate foreign keys are resolved correctly."""
    loader = DataLoader(test_session.get_bind())
    
    # Prepare dimensions first
    loader.load_category_dimension(sample_raw_data)
    loader.load_region_dimension(sample_raw_data)
    loader.load_customer_dimension(sample_raw_data)
    loader.load_product_dimension(sample_raw_data)
    
    # Clean and transform dataframe to match load expectations (adds Revenue & Profit_Margin)
    from src.etl.transform.clean import DataCleaner
    from src.etl.transform.transformer import DataTransformer
    
    cleaner = DataCleaner()
    transformer = DataTransformer()
    cleaned_df = cleaner.clean(sample_raw_data)
    transformed_df = transformer.transform(cleaned_df)

    loaded_facts = loader.load_fact_sales(transformed_df)
    assert loaded_facts == 3

    facts = test_session.scalars(select(FactSales)).all()
    assert len(facts) == 3
    # Check if first fact connects to correct resolved customer
    first_fact = facts[0]
    assert first_fact.customer.customer_id == "CS-12345"
    assert first_fact.product.product_id == "TEC-PH-10001"
    assert first_fact.sales == 250.00
