"""Pydantic v2 schemas for the Retail Data Warehouse API.

This module defines all request/response models used across the API layer,
including domain entities (Customer, Product, Sales), analytics aggregates
(KPI, Dashboard), and common utilities (pagination, date filtering, health).

All response models use ``from_attributes=True`` so they can be constructed
directly from SQLAlchemy ORM instances.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Customer schemas
# ---------------------------------------------------------------------------


class CustomerBase(BaseModel):
    """Base schema for customer data shared between create/update and read.

    Attributes:
        customer_id: Natural business key for the customer.
        customer_name: Full name of the customer.
        segment: Market segment the customer belongs to (e.g. Consumer,
            Corporate, Home Office).  May be ``None`` if not yet classified.
    """

    customer_id: str = Field(
        ...,
        min_length=1,
        description="Natural business key for the customer.",
    )
    customer_name: str = Field(
        ...,
        min_length=1,
        description="Full name of the customer.",
    )
    segment: str | None = Field(
        default=None,
        description="Market segment (e.g. Consumer, Corporate).",
    )


class CustomerResponse(CustomerBase):
    """Customer read-model returned from the API.

    Extends :class:`CustomerBase` with warehouse-specific surrogate key,
    SCD-2 tracking fields, and ORM compatibility.

    Attributes:
        customer_key: Surrogate key from the dimension table.
        effective_date: Date this version of the record became active.
        is_current: ``True`` if this is the most recent version (SCD-2).
    """

    model_config = ConfigDict(from_attributes=True)

    customer_key: int = Field(
        ...,
        description="Surrogate key assigned by the data warehouse.",
    )
    effective_date: date = Field(
        ...,
        description="SCD-2 effective date for this record version.",
    )
    is_current: bool = Field(
        ...,
        description="Whether this is the current active record.",
    )


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------


class ProductBase(BaseModel):
    """Base schema for product data.

    Attributes:
        product_id: Natural business key for the product.
        product_name: Display name of the product.
        sub_category: Product sub-category (e.g. Phones, Chairs).
    """

    product_id: str = Field(
        ...,
        min_length=1,
        description="Natural business key for the product.",
    )
    product_name: str = Field(
        ...,
        min_length=1,
        description="Display name of the product.",
    )
    sub_category: str | None = Field(
        default=None,
        description="Product sub-category.",
    )


class ProductResponse(ProductBase):
    """Product read-model returned from the API.

    Attributes:
        product_key: Surrogate key from the dimension table.
        category_name: Top-level product category.
    """

    model_config = ConfigDict(from_attributes=True)

    product_key: int = Field(
        ...,
        description="Surrogate key assigned by the data warehouse.",
    )
    category_name: str | None = Field(
        default=None,
        description="Top-level product category.",
    )


# ---------------------------------------------------------------------------
# Sales schemas
# ---------------------------------------------------------------------------


class SalesBase(BaseModel):
    """Base schema for sales fact data.

    Attributes:
        order_id: Unique identifier for the order.
        sales: Total sales amount for the line item.
        quantity: Number of units sold.
        discount: Discount percentage applied (0.0 – 1.0).
        profit: Profit amount for the line item.
    """

    order_id: str = Field(
        ...,
        min_length=1,
        description="Unique order identifier.",
    )
    sales: Decimal = Field(
        ...,
        description="Total sales amount.",
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="Number of units sold.",
    )
    discount: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Discount rate (0.0 – 1.0).",
    )
    profit: Decimal = Field(
        ...,
        description="Profit amount.",
    )


class SalesResponse(SalesBase):
    """Enriched sales read-model with denormalized dimension attributes.

    Attributes:
        sales_key: Surrogate key from the fact table.
        order_date: Date the order was placed.
        ship_date: Date the order was shipped.
        customer_name: Denormalized customer name.
        product_name: Denormalized product name.
        region: Geographic region of the sale.
        category: Product category of the sold item.
        revenue: Calculated revenue after discount.
        profit_margin: Profit as a percentage of revenue.
    """

    model_config = ConfigDict(from_attributes=True)

    sales_key: int = Field(
        ...,
        description="Surrogate key from the fact table.",
    )
    order_date: date | None = Field(
        default=None,
        description="Date the order was placed.",
    )
    ship_date: date | None = Field(
        default=None,
        description="Date the order was shipped.",
    )
    customer_name: str | None = Field(
        default=None,
        description="Denormalized customer name.",
    )
    product_name: str | None = Field(
        default=None,
        description="Denormalized product name.",
    )
    region: str | None = Field(
        default=None,
        description="Geographic region.",
    )
    category: str | None = Field(
        default=None,
        description="Product category.",
    )
    revenue: Decimal | None = Field(
        default=None,
        description="Calculated revenue after discount.",
    )
    profit_margin: Decimal | None = Field(
        default=None,
        description="Profit / revenue as a percentage.",
    )


# ---------------------------------------------------------------------------
# Analytics / Dashboard schemas
# ---------------------------------------------------------------------------


class KPIResponse(BaseModel):
    """Key performance indicators for the executive dashboard.

    Attributes:
        total_sales: Aggregate sales across all orders.
        total_profit: Aggregate profit across all orders.
        total_orders: Count of distinct orders.
        avg_order_value: Average revenue per order.
        profit_margin: Overall profit margin (profit / sales).
        total_customers: Count of distinct customers.
    """

    model_config = ConfigDict(from_attributes=True)

    total_sales: Decimal = Field(
        ...,
        description="Aggregate sales across all orders.",
    )
    total_profit: Decimal = Field(
        ...,
        description="Aggregate profit across all orders.",
    )
    total_orders: int = Field(
        ...,
        ge=0,
        description="Count of distinct orders.",
    )
    avg_order_value: Decimal = Field(
        ...,
        description="Average revenue per order.",
    )
    profit_margin: Decimal = Field(
        ...,
        description="Overall profit margin (profit / sales).",
    )
    total_customers: int = Field(
        ...,
        ge=0,
        description="Count of distinct customers.",
    )


class DashboardResponse(BaseModel):
    """Composite dashboard payload aggregating KPIs and chart data.

    Attributes:
        kpis: High-level key performance indicators.
        sales_by_category: Breakdown of sales by product category.
        sales_by_region: Breakdown of sales by geographic region.
        monthly_trend: Monthly sales/profit trend data.
        top_products: Top-selling products ranked by revenue.
    """

    model_config = ConfigDict(from_attributes=True)

    kpis: KPIResponse = Field(
        ...,
        description="High-level key performance indicators.",
    )
    sales_by_category: list[dict] = Field(
        default_factory=list,
        description="Sales breakdown by product category.",
    )
    sales_by_region: list[dict] = Field(
        default_factory=list,
        description="Sales breakdown by geographic region.",
    )
    monthly_trend: list[dict] = Field(
        default_factory=list,
        description="Monthly sales/profit trend data.",
    )
    top_products: list[dict] = Field(
        default_factory=list,
        description="Top-selling products ranked by revenue.",
    )


# ---------------------------------------------------------------------------
# Pagination & filtering
# ---------------------------------------------------------------------------


class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints.

    Attributes:
        page: 1-based page number.
        page_size: Number of records per page (1–100).
        sort_by: Column name to sort results by.
        sort_order: Sort direction – ascending or descending.
    """

    page: int = Field(
        default=1,
        ge=1,
        description="1-based page number.",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of records per page (1–100).",
    )
    sort_by: str = Field(
        default="sales_key",
        description="Column name to sort by.",
    )
    sort_order: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort direction.",
    )


class DateRangeFilter(BaseModel):
    """Optional date-range filter for analytics queries.

    Attributes:
        start_date: Inclusive lower bound of the date range.
        end_date: Inclusive upper bound of the date range.

    Raises:
        ValueError: If ``start_date`` is after ``end_date``.
    """

    start_date: date | None = Field(
        default=None,
        description="Inclusive start of date range.",
    )
    end_date: date | None = Field(
        default=None,
        description="Inclusive end of date range.",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> DateRangeFilter:
        """Ensure start_date does not exceed end_date when both are set."""
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError(
                f"start_date ({self.start_date}) must be on or before "
                f"end_date ({self.end_date})."
            )
        return self


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response model for the ``/health`` endpoint.

    Attributes:
        status: Overall application health status.
        db_status: Database connectivity status.
        timestamp: Server timestamp when the check was performed.
        version: Application version string.
        environment: Deployment environment (e.g. dev, staging, prod).
    """

    status: str = Field(
        ...,
        description="Overall health status (e.g. 'healthy').",
    )
    db_status: str = Field(
        ...,
        description="Database connectivity status.",
    )
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the health check.",
    )
    version: str = Field(
        ...,
        description="Application version string.",
    )
    environment: str = Field(
        ...,
        description="Deployment environment name.",
    )


# ---------------------------------------------------------------------------
# Generic paginated response
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated list responses.

    Type Parameters:
        T: The type of each item in the result set.

    Attributes:
        items: List of result items for the current page.
        total: Total number of records matching the query.
        page: Current page number (1-based).
        page_size: Number of records per page.
        total_pages: Total number of pages available.
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[T] = Field(
        ...,
        description="Result items for the current page.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total records matching the query.",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number.",
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Records per page.",
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total pages available.",
    )
