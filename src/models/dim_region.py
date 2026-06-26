"""DimRegion dimension model for the Retail Data Warehouse.

Stores geographic location data used for regional sales analysis.
Each unique combination of (country, state, city) forms a distinct
region record.

Typical usage::

    from src.models.dim_region import DimRegion

    region = DimRegion(
        country="United States",
        region="West",
        state="California",
        city="Los Angeles",
        postal_code="90001",
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.fact_sales import FactSales


class DimRegion(Base, TimestampMixin):
    """Geographic region dimension table.

    Represents a unique location defined by country, state, and city.
    A ``UniqueConstraint`` prevents duplicate location entries.

    Attributes:
        region_key: Surrogate primary key (auto-incremented).
        country: Country name.
        region: High-level region label (East, West, Central, South).
        state: State or province name.
        city: City name.
        postal_code: Optional postal / ZIP code.
        sales_facts: Related ``FactSales`` rows for this region.
    """

    __tablename__ = "dim_region"

    # ── Primary Key ──────────────────────────────────────────────────
    region_key: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Surrogate primary key.",
    )

    # ── Descriptive Attributes ───────────────────────────────────────
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Country name.",
    )
    region: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="High-level region (East, West, Central, South).",
    )
    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="State or province name.",
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="City name.",
    )
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default=None,
        doc="Postal or ZIP code.",
    )

    # ── Constraints & Indexes ────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("country", "state", "city", name="uq_region_location"),
        Index("ix_dim_region_region", "region"),
        Index("ix_dim_region_state", "state"),
    )

    # ── Relationships ────────────────────────────────────────────────
    sales_facts: Mapped[list["FactSales"]] = relationship(
        "FactSales",
        back_populates="region",
        lazy="select",
        doc="Fact rows linked to this region.",
    )
