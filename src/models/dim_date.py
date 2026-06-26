"""DimDate dimension model for the Retail Data Warehouse.

A date dimension (calendar table) that enables efficient time-based
slicing and dicing of fact data.  The ``date_key`` uses the ``YYYYMMDD``
integer format and is *not* auto-incremented — it is populated by the
ETL pipeline.

Typical usage::

    from src.models.dim_date import DimDate

    dim = DimDate(
        date_key=20240101,
        full_date=date(2024, 1, 1),
        day_of_week=1,
        day_name="Monday",
        ...
    )
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.fact_sales import FactSales


class DimDate(Base):
    """Date dimension table (calendar / reference table).

    This table intentionally does **not** include ``TimestampMixin``
    because it is a static reference table populated once during ETL.

    Two relationships to ``FactSales`` exist — one for order dates and
    one for ship dates — disambiguated via the ``foreign_keys`` argument.

    Attributes:
        date_key: Integer PK in ``YYYYMMDD`` format.
        full_date: The actual ``date`` value.
        day_of_week: ISO day of week (1 = Monday … 7 = Sunday).
        day_name: English name of the day.
        day_of_month: Day number within the month (1–31).
        day_of_year: Day number within the year (1–366).
        week_of_year: ISO week number (1–53).
        month: Month number (1–12).
        month_name: English name of the month.
        quarter: Calendar quarter (1–4).
        year: Four-digit calendar year.
        is_weekend: ``True`` for Saturday and Sunday.
        is_holiday: ``True`` if the date is a public holiday.
        fiscal_quarter: Fiscal quarter (company-specific).
        fiscal_year: Fiscal year (company-specific).
        order_date_facts: ``FactSales`` rows whose order occurred on this date.
        ship_date_facts: ``FactSales`` rows whose shipment occurred on this date.
    """

    __tablename__ = "dim_date"

    # ── Primary Key (YYYYMMDD, no autoincrement) ─────────────────────
    date_key: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        doc="Surrogate key in YYYYMMDD format.",
    )

    # ── Core Date ────────────────────────────────────────────────────
    full_date: Mapped[datetime.date] = mapped_column(
        Date,
        unique=True,
        nullable=False,
        doc="Calendar date value.",
    )

    # ── Day-Level Attributes ─────────────────────────────────────────
    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="ISO day of week (1=Mon … 7=Sun).",
    )
    day_name: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="English name of the day (e.g. Monday).",
    )
    day_of_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Day of the month (1–31).",
    )
    day_of_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Day of the year (1–366).",
    )

    # ── Week-Level Attributes ────────────────────────────────────────
    week_of_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="ISO week number (1–53).",
    )

    # ── Month-Level Attributes ───────────────────────────────────────
    month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Month number (1–12).",
    )
    month_name: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="English name of the month.",
    )

    # ── Quarter / Year ───────────────────────────────────────────────
    quarter: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Calendar quarter (1–4).",
    )
    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Four-digit calendar year.",
    )

    # ── Boolean Flags ────────────────────────────────────────────────
    is_weekend: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="True for Saturday and Sunday.",
    )
    is_holiday: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if the date is a recognized public holiday.",
    )

    # ── Fiscal Calendar ──────────────────────────────────────────────
    fiscal_quarter: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Fiscal quarter (company-specific mapping).",
    )
    fiscal_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Fiscal year (company-specific mapping).",
    )

    # ── Indexes ──────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_dim_date_full_date", "full_date"),
        Index("ix_dim_date_year", "year"),
        Index("ix_dim_date_month", "month"),
        Index("ix_dim_date_quarter", "quarter"),
    )

    # ── Relationships (disambiguated by foreign_keys) ────────────────
    order_date_facts: Mapped[list["FactSales"]] = relationship(
        "FactSales",
        foreign_keys="[FactSales.order_date_key]",
        back_populates="order_date",
        lazy="select",
        doc="Fact rows whose order date matches this date.",
    )
    ship_date_facts: Mapped[list["FactSales"]] = relationship(
        "FactSales",
        foreign_keys="[FactSales.ship_date_key]",
        back_populates="ship_date",
        lazy="select",
        doc="Fact rows whose ship date matches this date.",
    )
