"""Logging utilities for the Retail Data Warehouse platform.

Provides structured JSON logging, rotating file handlers, and a
pipeline-aware logger wrapper that enriches every log record with
run context (run_id, pipeline_name, stage).

Typical usage::

    from src.utils.logger import setup_logging, get_logger

    setup_logging(log_level="DEBUG", log_file="logs/pipeline.log")
    logger = get_logger(__name__)
    logger.info("Pipeline started")
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------


class JsonFormatter(logging.Formatter):
    """Custom :class:`logging.Formatter` that outputs each record as a
    single-line JSON object.

    The JSON payload always includes:

    * ``timestamp`` – ISO-8601 UTC timestamp.
    * ``level`` – Log level name (e.g. ``"INFO"``).
    * ``logger`` – Name of the logger that emitted the record.
    * ``message`` – Formatted log message.

    Any extra fields attached to the :class:`~logging.LogRecord` (via the
    ``extra`` dict) are merged into the top-level JSON object.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string representing the log record.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge user-supplied extra fields.
        default_attrs = logging.LogRecord(
            "", 0, "", 0, "", (), None
        ).__dict__.keys()
        for key, value in record.__dict__.items():
            if key not in default_attrs and key not in log_entry:
                log_entry[key] = value

        # Capture exception info when present.
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def setup_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """Configure the root logger with console and optional file handlers.

    This function is idempotent – calling it multiple times replaces existing
    handlers rather than duplicating them.

    Args:
        log_level: Minimum log level (e.g. ``"DEBUG"``, ``"INFO"``).
            Defaults to ``"INFO"``.
        log_file: Optional path for a rotating log file.  Parent directories
            are created automatically.  When ``None``, only the console
            handler is attached.

    Example::

        setup_logging(log_level="DEBUG", log_file="logs/etl.log")
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove pre-existing handlers to guarantee idempotency.
    root_logger.handlers.clear()

    # -- Console handler ---------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(
        fmt=_CONSOLE_FORMAT, datefmt=_DATE_FORMAT
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # -- Rotating file handler (optional) ----------------------------------
    if log_file is not None:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=_MAX_LOG_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    This is a thin convenience wrapper around :func:`logging.getLogger`
    that ensures a consistent entry point for obtaining loggers across
    the project.

    Args:
        name: Logical name for the logger, typically ``__name__``.

    Returns:
        A :class:`logging.Logger` instance bound to *name*.
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# PipelineLogger
# ---------------------------------------------------------------------------


class PipelineLogger:
    """Context-aware logger wrapper for ETL/ELT pipeline stages.

    Every log message emitted through this class is automatically enriched
    with ``run_id``, ``pipeline_name``, and the current ``stage``.

    Args:
        pipeline_name: Human-readable name of the pipeline.
        run_id: Unique identifier for this pipeline run.  Generated
            automatically when not supplied.
        logger_name: Name passed to :func:`get_logger`.  Defaults to
            *pipeline_name*.

    Example::

        pl = PipelineLogger("ingest_orders", run_id="abc-123")
        pl.start_stage("extract")
        pl.info("Fetching data from source system")
        pl.end_stage("extract")
    """

    def __init__(
        self,
        pipeline_name: str,
        run_id: str | None = None,
        logger_name: str | None = None,
    ) -> None:
        self.pipeline_name: str = pipeline_name
        self.run_id: str = run_id or uuid.uuid4().hex[:12]
        self.stage: str = "init"
        self._logger: logging.Logger = get_logger(
            logger_name or pipeline_name
        )
        self._stage_timers: dict[str, float] = {}

    # -- Convenience properties --------------------------------------------

    @property
    def _extra(self) -> dict[str, str]:
        """Build the extra dict injected into every log record."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "stage": self.stage,
        }

    # -- Standard log-level methods ----------------------------------------

    def info(self, message: str, **kwargs: Any) -> None:
        """Emit an ``INFO``-level message with pipeline context.

        Args:
            message: Log message.
            **kwargs: Additional key-value pairs merged into the record.
        """
        self._logger.info(message, extra={**self._extra, **kwargs})

    def error(self, message: str, **kwargs: Any) -> None:
        """Emit an ``ERROR``-level message with pipeline context.

        Args:
            message: Log message.
            **kwargs: Additional key-value pairs merged into the record.
        """
        self._logger.error(message, extra={**self._extra, **kwargs})

    def warning(self, message: str, **kwargs: Any) -> None:
        """Emit a ``WARNING``-level message with pipeline context.

        Args:
            message: Log message.
            **kwargs: Additional key-value pairs merged into the record.
        """
        self._logger.warning(message, extra={**self._extra, **kwargs})

    def debug(self, message: str, **kwargs: Any) -> None:
        """Emit a ``DEBUG``-level message with pipeline context.

        Args:
            message: Log message.
            **kwargs: Additional key-value pairs merged into the record.
        """
        self._logger.debug(message, extra={**self._extra, **kwargs})

    # -- Stage lifecycle ---------------------------------------------------

    def start_stage(self, stage_name: str) -> None:
        """Mark the beginning of a named pipeline stage.

        Records the current monotonic time so that :meth:`end_stage` can
        calculate elapsed duration.

        Args:
            stage_name: Identifier for the stage being started.
        """
        self.stage = stage_name
        self._stage_timers[stage_name] = time.monotonic()
        self.info(f"Stage '{stage_name}' started")

    def end_stage(self, stage_name: str) -> None:
        """Mark the end of a named pipeline stage and log elapsed time.

        Args:
            stage_name: Identifier for the stage being completed.  Must
                match a prior :meth:`start_stage` call.
        """
        start_time = self._stage_timers.pop(stage_name, None)
        if start_time is not None:
            elapsed = time.monotonic() - start_time
            self.info(
                f"Stage '{stage_name}' completed in {elapsed:.3f}s",
                elapsed_seconds=round(elapsed, 3),
            )
        else:
            self.warning(
                f"end_stage called for '{stage_name}' without a matching "
                f"start_stage"
            )
        self.stage = "between_stages"
