"""Pytest configuration and shared test fixtures.

Exposes mock datasets, temporary file structures, and a transactional
in-memory SQLite database environment matching warehouse schemas.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.main import app
from src.database.database import get_db
from src.models.base import Base
from src.models.dim_category import DimCategory
from src.models.dim_customer import DimCustomer
from src.models.dim_date import DimDate
from src.models.dim_product import DimProduct
from src.models.dim_region import DimRegion
from src.models.fact_sales import FactSales


@pytest.fixture(scope="session")
def test_engine():
    """Session-wide engine for in-memory SQLite database."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    import src.database.database
    src.database.database.engine = engine
    
    # Pre-populate some dates in the date dimension since it's required for fact key resolution
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        # Pre-load dates for 2021 to 2024
        start_date = datetime.date(2021, 1, 1)
        end_date = datetime.date(2024, 12, 31)
        current = start_date
        dates = []
        while current <= end_date:
            date_key = int(current.strftime("%Y%m%d"))
            dates.append(DimDate(
                date_key=date_key,
                full_date=current,
                day_of_week=current.weekday() + 1,
                day_name=current.strftime("%A"),
                day_of_month=current.day,
                day_of_year=current.timetuple().tm_yday,
                week_of_year=current.isocalendar()[1],
                month=current.month,
                month_name=current.strftime("%B"),
                quarter=(current.month - 1) // 3 + 1,
                year=current.year,
                is_weekend=current.weekday() in (5, 6),
                is_holiday=False,
                fiscal_quarter=((current.month - 4) % 12 + 1 - 1) // 3 + 1,
                fiscal_year=current.year if current.month >= 4 else current.year - 1
            ))
            current += datetime.timedelta(days=1)
        session.bulk_save_objects(dates)
        session.commit()

    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    """Provides a clean transactional session for database unit tests."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def clean_db(test_engine):
    """Automatically cleans up tables before each test runs to ensure isolation."""
    from sqlalchemy import text
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM fact_sales;"))
        conn.execute(text("DELETE FROM dim_product;"))
        conn.execute(text("DELETE FROM dim_customer;"))
        conn.execute(text("DELETE FROM dim_region;"))
        conn.execute(text("DELETE FROM dim_category;"))


@pytest.fixture
def api_client(test_engine):
    """Exposes a FastAPI test client with mocked DB session injector."""
    SessionLocal = sessionmaker(bind=test_engine)

    def _get_test_db():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Override get_db dependency
    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_raw_data() -> pd.DataFrame:
    """Generates a small valid pandas DataFrame simulating source sales data."""
    data = {
        "Row ID": [1, 2, 3],
        "Order ID": ["CA-2022-1001", "CA-2022-1001", "CA-2022-1002"],
        "Order Date": ["2022-05-10", "2022-05-10", "2022-06-15"],
        "Ship Date": ["2022-05-14", "2022-05-14", "2022-06-18"],
        "Ship Mode": ["Standard Class", "Standard Class", "First Class"],
        "Customer ID": ["CS-12345", "CS-12345", "CG-54321"],
        "Customer Name": ["Alice Smith", "Alice Smith", "Bob Johnson"],
        "Segment": ["Corporate", "Corporate", "Consumer"],
        "Country": ["United States", "United States", "United States"],
        "City": ["Los Angeles", "Los Angeles", "New York City"],
        "State": ["California", "California", "New York"],
        "Postal Code": [90012, 90012, 10001],
        "Region": ["West", "West", "East"],
        "Product ID": ["TEC-PH-10001", "FUR-CH-10002", "OFF-BI-10003"],
        "Category": ["Technology", "Furniture", "Office Supplies"],
        "Sub-Category": ["Phones", "Chairs", "Binders"],
        "Product Name": ["Logitech Desk Phone", "HON Task Chair", "Wilson Ring Binder"],
        "Sales": [250.00, 120.00, 15.50],
        "Quantity": [2, 1, 5],
        "Discount": [0.0, 0.1, 0.0],
        "Profit": [50.00, 10.00, 3.20]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_csv(tmp_path: Path, sample_raw_data: pd.DataFrame) -> Path:
    """Writes the sample raw data to a temporary CSV file and returns its path."""
    csv_file = tmp_path / "superstore_sales.csv"
    sample_raw_data.to_csv(csv_file, index=False)
    return csv_file
