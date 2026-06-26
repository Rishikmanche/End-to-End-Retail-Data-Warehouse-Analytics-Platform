"""Database engine, session management, and lifecycle utilities.

Provides SQLAlchemy 2.0 engine creation with connection pooling,
session factories, context managers for safe session handling,
FastAPI dependency injection, and database health checks.

Example:
    >>> from src.database.database import get_session
    >>> with get_session() as session:
    ...     result = session.execute(text("SELECT 1"))
    ...     print(result.scalar())
    1
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.config import get_settings
from src.models.base import Base

logger: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------

settings = get_settings()

engine: Engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=(settings.ENVIRONMENT == "development"),
)
"""Global SQLAlchemy engine with connection pooling.

Configured with:
    - ``pool_size=10``: Maintain 10 persistent connections.
    - ``max_overflow=20``: Allow up to 20 additional connections under load.
    - ``pool_pre_ping=True``: Verify connections before checkout to handle
      stale/disconnected connections gracefully.
    - ``echo``: Enabled in development for SQL statement logging.
"""

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
"""Session factory bound to the global engine.

Sessions are configured with:
    - ``autocommit=False``: Explicit transaction control required.
    - ``autoflush=False``: Manual flush control for batch operations.
    - ``expire_on_commit=False``: Objects remain accessible after commit
      without re-querying.
"""


# ---------------------------------------------------------------------------
# Session Context Manager
# ---------------------------------------------------------------------------


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session with automatic cleanup.

    Creates a new ``Session`` from the session factory, yields it for
    use, and ensures proper commit/rollback and close semantics.

    Yields:
        A SQLAlchemy ``Session`` instance.

    Raises:
        Exception: Re-raises any exception after rolling back the
            transaction and closing the session.

    Example:
        >>> with get_session() as session:
        ...     products = session.query(Product).all()
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Session rollback due to unhandled exception")
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session per request.

    Yields a session and ensures it is closed after the request
    completes, regardless of success or failure. Intended for use
    with FastAPI's ``Depends()`` injection.

    Yields:
        A SQLAlchemy ``Session`` instance.

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/items")
        ... def list_items(db: Session = Depends(get_db)):
        ...     return db.query(Item).all()
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Request session rollback due to unhandled exception")
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Database Lifecycle
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all database tables defined by SQLAlchemy models.

    Uses ``Base.metadata.create_all`` to issue CREATE TABLE statements
    for any tables that do not already exist. This is idempotent and
    safe to call multiple times.

    Note:
        All model modules must be imported before calling this function
        so that their table definitions are registered with ``Base.metadata``.

    Example:
        >>> init_db()  # Creates all tables
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def health_check() -> dict[str, Any]:
    """Verify database connectivity by executing a simple query.

    Attempts to run ``SELECT 1`` against the database and returns
    a status dictionary indicating the result.

    Returns:
        A dictionary with keys:
            - ``status`` (str): ``"healthy"`` or ``"unhealthy"``.
            - ``database`` (str): The database name from settings.
            - ``error`` (str | None): Error message if unhealthy,
              ``None`` otherwise.

    Example:
        >>> result = health_check()
        >>> result["status"]
        'healthy'
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.commit()
        logger.info("Database health check passed.")
        return {
            "status": "healthy",
            "database": settings.DB_NAME,
            "error": None,
        }
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "database": settings.DB_NAME,
            "error": str(exc),
        }
