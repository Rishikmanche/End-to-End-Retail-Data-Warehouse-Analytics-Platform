"""Integration tests for the REST API endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import insert

from src.models.dim_category import DimCategory
from src.models.dim_customer import DimCustomer
from src.models.dim_product import DimProduct
from src.models.dim_region import DimRegion
from src.models.fact_sales import FactSales


@pytest.fixture(autouse=True)
def seed_test_data(test_session) -> None:
    """Pre-seeds transactional records in in-memory test DB prior to running API routes."""
    # Create test dimensions
    cust = DimCustomer(
        customer_key=10,
        customer_id="CUST-01",
        customer_name="John Doe",
        segment="Consumer",
        effective_date=datetime.date(2022, 1, 1),
        is_current=True
    )
    cat = DimCategory(
        category_key=10,
        category_id="TEC-PHONE",
        category_name="Technology",
        sub_category="Phones",
        description="Phones description"
    )
    prod = DimProduct(
        product_key=10,
        product_id="PROD-01",
        product_name="Super Phone",
        category_key=10,
        sub_category="Phones"
    )
    reg = DimRegion(
        region_key=10,
        country="United States",
        region="East",
        state="New York",
        city="New York City",
        postal_code="10001"
    )
    
    test_session.add_all([cust, cat, prod, reg])
    test_session.commit()

    # Create test fact (make sure it references valid date key format YYYYMMDD pre-seeded in test_engine)
    fact = FactSales(
        sales_key=100,
        order_id="ORD-01",
        order_date_key=20220510,
        ship_date_key=20220514,
        customer_key=10,
        product_key=10,
        region_key=10,
        category_key=10,
        ship_mode="Standard Class",
        sales=500.00,
        quantity=2,
        discount=0.10,
        profit=100.00,
        revenue=450.00,
        profit_margin=0.2000
    )
    test_session.add(fact)
    test_session.commit()


def test_api_health_endpoint(api_client: TestClient) -> None:
    """Verifies GET /health returns online status and DB health status."""
    response = api_client.get("/health")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["db_status"] == "healthy"
    assert "timestamp" in payload


def test_api_kpis_endpoint(api_client: TestClient) -> None:
    """Verifies GET /kpis returns correct aggregate financials."""
    response = api_client.get("/kpis")
    assert response.status_code == 200
    
    payload = response.json()
    assert float(payload["total_sales"]) == 450.0  # matches fact revenue
    assert float(payload["total_profit"]) == 100.0
    assert payload["total_orders"] == 1
    assert payload["total_customers"] == 1
    assert float(payload["avg_order_value"]) == 450.0
    assert float(payload["profit_margin"]) == 0.2222  # profit (100) / revenue (450) = 0.222222...


def test_api_customers_list(api_client: TestClient) -> None:
    """Verifies GET /customers returns paginated customer payload."""
    response = api_client.get("/customers?segment=Consumer&page=1&page_size=10")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["customer_name"] == "John Doe"


def test_api_customer_not_found(api_client: TestClient) -> None:
    """Verifies GET /customers/{customer_id} returns 404 for non-existent customer."""
    response = api_client.get("/customers/MISSING-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_api_products_list(api_client: TestClient) -> None:
    """Verifies GET /products returns paginated products payload."""
    response = api_client.get("/products?category=Technology&page_size=5")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["product_name"] == "Super Phone"
    assert payload["items"][0]["category_name"] == "Technology"


def test_api_sales_transactions(api_client: TestClient) -> None:
    """Verifies GET /sales returns transactional transactions with joins."""
    response = api_client.get("/sales?region=East&page_size=10")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["order_id"] == "ORD-01"
    assert item["customer_name"] == "John Doe"
    assert item["product_name"] == "Super Phone"
    assert item["region"] == "East"
    assert item["category"] == "Technology"
    assert float(item["revenue"]) == 450.0
    assert float(item["sales"]) == 500.0


def test_api_dashboard_payload(api_client: TestClient) -> None:
    """Verifies GET /dashboard-data returns composite payload."""
    response = api_client.get("/dashboard-data")
    assert response.status_code == 200
    
    payload = response.json()
    assert "kpis" in payload
    assert "sales_by_category" in payload
    assert "sales_by_region" in payload
    assert "monthly_trend" in payload
    assert "top_products" in payload
    
    assert payload["sales_by_category"][0]["category"] == "Technology"
    assert float(payload["sales_by_category"][0]["sales"]) == 450.0
    
    assert payload["sales_by_region"][0]["region"] == "East"
    assert float(payload["sales_by_region"][0]["sales"]) == 450.0
