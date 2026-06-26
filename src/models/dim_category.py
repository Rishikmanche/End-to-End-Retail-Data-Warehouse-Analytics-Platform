"""DimCategory dimension model for the Retail Data Warehouse.

Represents the product category hierarchy in the Star Schema.
Categories include Furniture, Office Supplies, and Technology.

Typical usage::

    from src.models.dim_category import DimCategory

    category = DimCategory(
        category_id="CAT-001",
        category_name="Technology",
        description="Electronic devices and accessories.",
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.dim_product import DimProduct
    from src.models.fact_sales import FactSales


class DimCategory(Base, TimestampMixin):
    """Product category dimension table.

    Stores high-level product categories used to classify products.
    Acts as a parent dimension for ``DimProduct`` and is directly
    referenced by ``FactSales`` for query convenience.

    Attributes:
        category_key: Surrogate primary key (auto-incremented).
        category_id: Natural business key for the category.
        category_name: Human-readable category label.
        description: Optional extended description of the category.
        products: Related ``DimProduct`` records.
        sales_facts: Related ``FactSales`` records.
    """

    __tablename__ = "dim_category"

    # ── Primary Key ──────────────────────────────────────────────────
    category_key: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Surrogate primary key.",
    )

    # ── Natural Key ──────────────────────────────────────────────────
    category_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Natural business key for the category.",
    )

    # ── Descriptive Attributes ───────────────────────────────────────
    category_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Category label (e.g. Furniture, Office Supplies, Technology).",
    )
    sub_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Sub-category label within the parent category.",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Extended description of the category.",
    )

    # ── Indexes ──────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_dim_category_category_name", "category_name"),
        Index("ix_dim_category_sub_category", "sub_category"),
    )

    # ── Relationships ────────────────────────────────────────────────
    products: Mapped[list["DimProduct"]] = relationship(
        "DimProduct",
        back_populates="category",
        lazy="select",
        doc="Products belonging to this category.",
    )
    sales_facts: Mapped[list["FactSales"]] = relationship(
        "FactSales",
        back_populates="category",
        lazy="select",
        doc="Fact rows referencing this category.",
    )
