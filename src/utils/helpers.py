"""General-purpose helper utilities for the Retail Data Warehouse platform.

This module collects small, reusable functions used across the ETL pipeline,
API layer, and analytics notebooks.  Every public function carries full type
hints and Google-style docstrings.

Typical usage::

    from src.utils.helpers import (
        generate_surrogate_key,
        format_currency,
        timer_decorator,
    )

    key = generate_surrogate_key("US-2024-001", "FUR-BO-10001")
    print(format_currency(1234.5))   # "$1,234.50"
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import math
import random
import time
import unicodedata
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Generator, TypeVar

import pandas as pd

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


def generate_surrogate_key(*fields: str) -> str:
    """Generate a deterministic surrogate key from one or more field values.

    The key is derived by concatenating *fields* with a pipe (``|``)
    separator, hashing the result with SHA-256, and truncating the hex
    digest to 16 characters.

    Args:
        *fields: One or more string values that together uniquely identify
            a business entity.

    Returns:
        A 16-character hexadecimal string suitable for use as a surrogate
        key in dimension tables.

    Raises:
        ValueError: If no fields are provided.

    Example::

        >>> generate_surrogate_key("US-2024-001", "FUR-BO-10001")
        'a3f7c1d2e4b56789'
    """
    if not fields:
        raise ValueError("At least one field is required to generate a key.")

    combined = "|".join(str(f) for f in fields)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_currency(
    value: float | Decimal | None,
    currency_symbol: str = "$",
) -> str:
    """Format a numeric value as a currency string.

    Args:
        value: The amount to format.  ``None`` and ``NaN`` values are
            handled gracefully and return ``"N/A"``.
        currency_symbol: Prefix symbol.  Defaults to ``"$"``.

    Returns:
        A formatted currency string (e.g. ``"$1,234.56"``), or ``"N/A"``
        when *value* cannot be represented.

    Example::

        >>> format_currency(1234.5)
        '$1,234.50'
        >>> format_currency(None)
        'N/A'
    """
    if value is None:
        return "N/A"

    try:
        numeric = float(value)
    except (TypeError, ValueError, InvalidOperation):
        return "N/A"

    if math.isnan(numeric) or math.isinf(numeric):
        return "N/A"

    return f"{currency_symbol}{numeric:,.2f}"


# ---------------------------------------------------------------------------
# Date utilities
# ---------------------------------------------------------------------------


def calculate_date_key(dt: date | datetime | str) -> int:
    """Convert a date to an integer key in ``YYYYMMDD`` format.

    String dates are parsed automatically using common ISO formats.

    Args:
        dt: A :class:`~datetime.date`, :class:`~datetime.datetime`, or an
            ISO-8601 date string (``"YYYY-MM-DD"``).

    Returns:
        An integer in the form ``YYYYMMDD`` (e.g. ``20240115``).

    Raises:
        ValueError: If *dt* cannot be interpreted as a valid date.

    Example::

        >>> calculate_date_key(date(2024, 1, 15))
        20240115
        >>> calculate_date_key("2024-01-15")
        20240115
    """
    if isinstance(dt, datetime):
        d = dt.date()
    elif isinstance(dt, date):
        d = dt
    elif isinstance(dt, str):
        dt_stripped = dt.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                d = datetime.strptime(dt_stripped, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise ValueError(
                f"Unable to parse '{dt}' as a valid date. "
                f"Supported formats: YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY, "
                f"DD-MM-YYYY."
            )
    else:
        raise ValueError(
            f"Expected date, datetime, or str; got {type(dt).__name__}."
        )

    return int(d.strftime("%Y%m%d"))


# ---------------------------------------------------------------------------
# DataFrame utilities
# ---------------------------------------------------------------------------


def chunk_dataframe(
    df: pd.DataFrame,
    chunk_size: int = 10_000,
) -> Generator[pd.DataFrame, None, None]:
    """Yield successive chunks of a DataFrame.

    Args:
        df: The DataFrame to split.
        chunk_size: Maximum number of rows per chunk.  Must be ≥ 1.

    Yields:
        :class:`~pandas.DataFrame` slices of at most *chunk_size* rows.

    Raises:
        TypeError: If *df* is not a :class:`~pandas.DataFrame`.
        ValueError: If *chunk_size* is less than 1.

    Example::

        for chunk in chunk_dataframe(large_df, chunk_size=5000):
            process(chunk)
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"Expected pandas DataFrame; got {type(df).__name__}."
        )
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be >= 1; got {chunk_size}.")

    for start in range(0, len(df), chunk_size):
        yield df.iloc[start : start + chunk_size]


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def timer_decorator(func: F) -> F:
    """Decorator that logs the wall-clock execution time of a function.

    Works seamlessly with both synchronous and ``async`` functions.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function with timing instrumentation.

    Example::

        @timer_decorator
        def heavy_query():
            ...
    """
    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.monotonic() - start
                logger.info(
                    "%s completed in %.3fs",
                    func.__qualname__,
                    elapsed,
                )

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            logger.info(
                "%s completed in %.3fs",
                func.__qualname__,
                elapsed,
            )

    return sync_wrapper  # type: ignore[return-value]


def retry_decorator(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator factory for retry with exponential back-off and jitter.

    Args:
        max_retries: Maximum number of retry attempts (excluding the
            initial call).
        base_delay: Initial delay in seconds before the first retry.
        exponential_base: Multiplier applied to the delay after each
            failed attempt.
        exceptions: Tuple of exception types that trigger a retry.

    Returns:
        A decorator that wraps a function with retry logic.

    Example::

        @retry_decorator(max_retries=5, base_delay=0.5)
        def fetch_from_api():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = base_delay * (
                            exponential_base ** attempt
                        ) + random.uniform(0, 0.5)
                        logger.warning(
                            "%s failed (attempt %d/%d): %s – retrying "
                            "in %.2fs",
                            func.__qualname__,
                            attempt + 1,
                            max_retries + 1,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__qualname__,
                            max_retries + 1,
                            exc,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_dataframe_schema(
    df: pd.DataFrame,
    expected_columns: list[str],
    raise_on_missing: bool = True,
) -> tuple[bool, list[str]]:
    """Validate that a DataFrame contains the expected columns.

    Args:
        df: The DataFrame to validate.
        expected_columns: Column names that must be present.
        raise_on_missing: If ``True``, raise :class:`ValueError` when
            columns are missing.  Defaults to ``True``.

    Returns:
        A tuple of ``(is_valid, missing_columns)`` where *is_valid* is
        ``True`` when all expected columns are present and
        *missing_columns* lists any that are absent.

    Raises:
        ValueError: If *raise_on_missing* is ``True`` and columns are
            missing.
        TypeError: If *df* is not a :class:`~pandas.DataFrame`.

    Example::

        ok, missing = validate_dataframe_schema(df, ["order_id", "sales"])
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"Expected pandas DataFrame; got {type(df).__name__}."
        )

    actual_columns = set(df.columns)
    missing = [
        col for col in expected_columns if col not in actual_columns
    ]
    is_valid = len(missing) == 0

    if not is_valid and raise_on_missing:
        raise ValueError(
            f"DataFrame is missing expected columns: {missing}. "
            f"Available columns: {sorted(actual_columns)}"
        )

    return is_valid, missing


# ---------------------------------------------------------------------------
# String utilities
# ---------------------------------------------------------------------------


def clean_string(value: str | None) -> str | None:
    """Clean and normalize a string value.

    Operations performed:

    1. Return ``None`` immediately for ``None`` inputs.
    2. Strip leading/trailing whitespace.
    3. Normalize Unicode to NFC form.
    4. Return ``None`` if the result is an empty string.

    Args:
        value: The string to clean, or ``None``.

    Returns:
        The cleaned string, or ``None`` if the input is ``None`` or
        empty after stripping.

    Example::

        >>> clean_string("  Hello World  ")
        'Hello World'
        >>> clean_string(None) is None
        True
    """
    if value is None:
        return None

    cleaned = unicodedata.normalize("NFC", value.strip())
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# Numeric utilities
# ---------------------------------------------------------------------------


def safe_divide(
    numerator: float,
    denominator: float,
    default: float = 0.0,
) -> float:
    """Perform division with zero-division protection.

    Args:
        numerator: The dividend.
        denominator: The divisor.
        default: Value returned when *denominator* is zero.  Defaults to
            ``0.0``.

    Returns:
        ``numerator / denominator``, or *default* when *denominator* is
        zero.

    Example::

        >>> safe_divide(10, 3)
        3.3333333333333335
        >>> safe_divide(10, 0)
        0.0
    """
    if denominator == 0:
        return default
    return numerator / denominator
