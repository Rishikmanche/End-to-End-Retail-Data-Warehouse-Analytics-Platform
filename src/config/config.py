"""Application configuration management.

Provides centralized settings via Pydantic BaseSettings with environment
variable support, .env file loading, and logging configuration.

Example:
    >>> from src.config.config import get_settings
    >>> settings = get_settings()
    >>> print(settings.DATABASE_URL)
    postgresql+psycopg2://retail_user:retail_pass_2024@localhost:5432/retail_warehouse
"""

from __future__ import annotations

import functools
import logging
import sys
from typing import Any

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    All fields can be overridden via environment variables. The .env file
    in the project root is loaded automatically if present.

    Attributes:
        DB_HOST: PostgreSQL server hostname.
        DB_PORT: PostgreSQL server port.
        DB_NAME: Target database name.
        DB_USER: Database authentication username.
        DB_PASSWORD: Database authentication password.
        LOG_LEVEL: Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        DATA_DIR: Directory path for raw and processed data files.
        API_HOST: FastAPI server bind address.
        API_PORT: FastAPI server bind port.
        ENVIRONMENT: Deployment environment (development, staging, production).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "retail_warehouse"
    DB_USER: str = "retail_user"
    DB_PASSWORD: str = "retail_pass_2024"

    # Application configuration
    LOG_LEVEL: str = "INFO"
    DATA_DIR: str = "./data"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ENVIRONMENT: str = "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Construct the full PostgreSQL connection URL from components.

        Returns:
            A SQLAlchemy-compatible PostgreSQL connection string using
            the psycopg2 driver.
        """
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings.

    Uses ``functools.lru_cache`` to ensure the settings are only
    parsed once from environment variables and the .env file.

    Returns:
        The application ``Settings`` instance.

    Example:
        >>> settings = get_settings()
        >>> settings.DB_HOST
        'localhost'
    """
    return Settings()


def setup_logging(settings: Settings | None = None) -> None:
    """Configure the root logger based on application settings.

    Sets up structured logging with a consistent format including
    timestamps, log level, logger name, and message. Configures
    output to stdout for container-friendly log collection.

    Args:
        settings: Optional settings instance. If not provided, the
            cached singleton from ``get_settings()`` is used.

    Example:
        >>> setup_logging()
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    if settings is None:
        settings = get_settings()

    log_level: str = settings.LOG_LEVEL.upper()
    numeric_level: int = getattr(logging, log_level, logging.INFO)

    log_format: str = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    date_format: str = "%Y-%m-%d %H:%M:%S"

    # Remove any existing handlers on the root logger
    root_logger: logging.Logger = logging.getLogger()
    root_logger.handlers.clear()

    # Configure the handler
    handler: logging.StreamHandler[Any] = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter: logging.Formatter = logging.Formatter(
        fmt=log_format,
        datefmt=date_format,
    )
    handler.setFormatter(formatter)

    # Apply to root logger
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger: logging.Logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured: level=%s, environment=%s",
        log_level,
        settings.ENVIRONMENT,
    )
