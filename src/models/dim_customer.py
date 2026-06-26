"""DimCustomer dimension model for the Retail Data Warehouse.

Implements Slowly Changing Dimension Type 2 (SCD-2) to preserve the
full history of customer attribute changes over time.

Typical usage::

    from src.models.dim_customer import DimCustomer

    customer = DimCustomer(
        customer_id="CUST-001",
        customer_name="Jane Doe",
        segment="Consumer",
        effective_date=date(2024, 1, 1),
    )
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.fact_sales import FactSales


class DimCustomer(Base, TimestampMixin):
    """Customer dimension table with SCD Type 2 versioning.

    Each row represents a *version* of a customer record.  When customer
    attributes change, the current row is expired (``is_current = False``,
    ``expiry_date`` is set) and a new row is inserted.

    Attributes:
        customer_key: Surrogate primary key (auto-incremented).
        customer_id: Natural business key — stable across versions.
        customer_name: Full name of the customer.
        segment: Market segment (Consumer, Corporate, Home Office).
        effective_date: Date this version became active.
        expiry_date: Date this version was superseded (``None`` if current).
        is_current: Whether this is the active version of the customer.
        sales_facts: Related ``FactSales`` rows for this version.
    """

    __tablename__ = "dim_customer"

    # ── Primary Key ──────────────────────────────────────────────────
    customer_key: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Surrogate primary key.",
    )

    # ── Natural Key ──────────────────────────────────────────────────
    customer_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Natural business key for the customer.",
    )

    # ── Descriptive Attributes ───────────────────────────────────────
    customer_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Full name of the customer.",
    )
    segment: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        doc="Market segment: Consumer, Corporate, or Home Office.",
    )

    # ── SCD Type 2 Columns ───────────────────────────────────────────
    effective_date: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
        doc="Date from which this version is effective.",
    )
    expiry_date: Mapped[Optional[datetime.date]] = mapped_column(
        Date,
        nullable=True,
        default=None,
        doc="Date this version was superseded (None if current).",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Whether this is the currently active customer version.",
    )

    # ── Indexes ──────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_dim_customer_customer_id", "customer_id"),
        Index("ix_dim_customer_segment", "segment"),
        Index("ix_dim_customer_is_current", "is_current"),
    )

    # ── Relationships ────────────────────────────────────────────────
    sales_facts: Mapped[list["FactSales"]] = relationship(
        "FactSales",
        back_populates="customer",
        lazy="select",
        doc="Fact rows linked to this customer version.",
    )
