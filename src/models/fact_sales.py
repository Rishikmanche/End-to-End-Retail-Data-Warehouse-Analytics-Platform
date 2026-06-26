"""FactSales model for the Retail Data Warehouse.

This table records transactional sales data with foreign keys pointing to
all dimension tables (customer, product, region, date, category) and captures
numerical measures like sales, quantity, discount, and profit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.dim_category import DimCategory
    from src.models.dim_customer import DimCustomer
    from src.models.dim_date import DimDate
    from src.models.dim_product import DimProduct
    from src.models.dim_region import DimRegion


class FactSales(Base, TimestampMixin):
    """Fact table for sales transactions.

    Contains foreign key links to dimensions and transactional metrics.
    Calculates derived metrics like revenue and profit margin using constraints.
    """

    __tablename__ = "fact_sales"

    # ── Primary Key ──────────────────────────────────────────────────
    sales_key: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Surrogate primary key for the sales fact record.",
    )

    # ── Natural Keys & Identifiers ──────────────────────────────────
    order_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Transactional order identifier from source systems.",
    )

    # ── Foreign Keys ─────────────────────────────────────────────────
    order_date_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dim_date.date_key", ondelete="RESTRICT"),
        nullable=False,
        doc="FK reference to order date in dim_date.",
    )
    ship_date_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dim_date.date_key", ondelete="RESTRICT"),
        nullable=False,
        doc="FK reference to shipping date in dim_date.",
    )
    customer_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dim_customer.customer_key", ondelete="RESTRICT"),
        nullable=False,
        doc="FK reference to customer dimension record.",
    )
    product_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dim_product.product_key", ondelete="RESTRICT"),
        nullable=False,
        doc="FK reference to product dimension record.",
    )
    region_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dim_region.region_key", ondelete="RESTRICT"),
        nullable=False,
        doc="FK reference to geography/region dimension record.",
    )
    category_key: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dim_category.category_key", ondelete="RESTRICT"),
        nullable=False,
        doc="FK reference to product category dimension.",
    )

    # ── Transactional Attributes ─────────────────────────────────────
    ship_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Shipping mode used (e.g., Standard Class, Second Class, First Class, Same Day).",
    )

    # ── Financial Measures ───────────────────────────────────────────
    sales: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Gross sales amount before discounts.",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of units ordered.",
    )
    discount: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0.00,
        server_default="0.00",
        doc="Discount percentage applied (e.g., 0.20 for 20% off).",
    )
    profit: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Net profit generated from the transaction.",
    )
    revenue: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Net revenue calculated as Sales * (1 - Discount).",
    )
    profit_margin: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        doc="Profit margin calculated as Profit / Sales.",
    )

    # ── Relationships ────────────────────────────────────────────────
    order_date: Mapped["DimDate"] = relationship(
        "DimDate",
        foreign_keys=[order_date_key],
        doc="Order date dimension link.",
    )
    ship_date: Mapped["DimDate"] = relationship(
        "DimDate",
        foreign_keys=[ship_date_key],
        doc="Ship date dimension link.",
    )
    customer: Mapped["DimCustomer"] = relationship(
        "DimCustomer",
        back_populates="sales_facts",
        doc="Customer dimension link.",
    )
    product: Mapped["DimProduct"] = relationship(
        "DimProduct",
        back_populates="sales_facts",
        doc="Product dimension link.",
    )
    region: Mapped["DimRegion"] = relationship(
        "DimRegion",
        back_populates="sales_facts",
        doc="Region/geography dimension link.",
    )
    category: Mapped["DimCategory"] = relationship(
        "DimCategory",
        back_populates="sales_facts",
        doc="Category dimension link.",
    )

    # ── Table Constraints & Indexes ──────────────────────────────────
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_fact_sales_quantity"),
        CheckConstraint("discount >= 0.00 AND discount <= 1.00", name="chk_fact_sales_discount"),
        Index("ix_fact_sales_order_id", "order_id"),
        Index("ix_fact_sales_order_date_key", "order_date_key"),
        Index("ix_fact_sales_ship_date_key", "ship_date_key"),
        Index("ix_fact_sales_customer_key", "customer_key"),
        Index("ix_fact_sales_product_key", "product_key"),
        Index("ix_fact_sales_region_key", "region_key"),
        Index("ix_fact_sales_category_key", "category_key"),
    )
