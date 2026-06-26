"""DimProduct dimension model for the Retail Data Warehouse.

Stores product-level attributes and links to the parent category
dimension via a foreign key.

Typical usage::

    from src.models.dim_product import DimProduct

    product = DimProduct(
        product_id="PROD-001",
        product_name="Wireless Keyboard",
        category_key=3,
        sub_category="Accessories",
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.dim_category import DimCategory
    from src.models.fact_sales import FactSales


class DimProduct(Base, TimestampMixin):
    """Product dimension table.

    Each row represents a distinct product in the retail catalogue.
    Products belong to a category (via ``category_key``) and are
    referenced by ``FactSales`` for transactional analysis.

    Attributes:
        product_key: Surrogate primary key (auto-incremented).
        product_id: Natural business key for the product.
        product_name: Full descriptive name of the product.
        category_key: Foreign key to ``dim_category.category_key``.
        sub_category: Optional sub-category label within the parent category.
        category: Related ``DimCategory`` record.
        sales_facts: Related ``FactSales`` rows for this product.
    """

    __tablename__ = "dim_product"

    # ── Primary Key ──────────────────────────────────────────────────
    product_key: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Surrogate primary key.",
    )

    # ── Natural Key ──────────────────────────────────────────────────
    product_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Natural business key for the product.",
    )

    # ── Descriptive Attributes ───────────────────────────────────────
    product_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Full descriptive name of the product.",
    )
    category_key: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("dim_category.category_key"),
        nullable=True,
        doc="FK to the parent category dimension.",
    )
    sub_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        doc="Sub-category within the parent category.",
    )

    # ── Indexes ──────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_dim_product_product_id", "product_id"),
        Index("ix_dim_product_category_key", "category_key"),
    )

    # ── Relationships ────────────────────────────────────────────────
    category: Mapped[Optional["DimCategory"]] = relationship(
        "DimCategory",
        back_populates="products",
        lazy="select",
        doc="Parent category for this product.",
    )
    sales_facts: Mapped[list["FactSales"]] = relationship(
        "FactSales",
        back_populates="product",
        lazy="select",
        doc="Fact rows referencing this product.",
    )
