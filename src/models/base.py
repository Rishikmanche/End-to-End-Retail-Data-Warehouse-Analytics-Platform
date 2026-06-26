"""Base classes and mixins for the Retail Data Warehouse ORM models.

This module provides the declarative base class and reusable mixins
for timestamp tracking and soft-delete functionality across all models.

Typical usage::

    from src.models.base import Base, TimestampMixin, SoftDeleteMixin

    class MyModel(Base, TimestampMixin, SoftDeleteMixin):
        __tablename__ = 'my_table'
        ...
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class for all ORM models.

    Provides automatic ``__repr__`` generation based on the model's
    primary key columns and table name.
    """

    def __repr__(self) -> str:
        """Generate a human-readable string representation.

        Returns:
            A string of the form ``ClassName(pk_col=value, ...)``.
        """
        mapper = self.__class__.__mapper__
        pk_cols = mapper.primary_key
        pk_values = ", ".join(
            f"{col.name}={getattr(self, col.name)!r}" for col in pk_cols
        )
        return f"{self.__class__.__name__}({pk_values})"


class TimestampMixin:
    """Mixin that adds ``created_at`` and ``updated_at`` audit columns.

    Both columns default to the database server's current timestamp.
    ``updated_at`` is automatically refreshed on every row update via
    SQLAlchemy's ``onupdate`` hook.

    Attributes:
        created_at: Timestamp set when the row is first inserted.
        updated_at: Timestamp refreshed on every update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when the record was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when the record was last updated.",
    )


class SoftDeleteMixin:
    """Mixin that adds soft-delete support to a model.

    Instead of physically removing rows, consumers set ``is_deleted``
    to ``True`` and record the deletion time in ``deleted_at``.

    Attributes:
        is_deleted: Flag indicating whether the row is logically deleted.
        deleted_at: Timestamp of when the soft delete occurred.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether this record has been soft-deleted.",
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Timestamp when the record was soft-deleted.",
    )
