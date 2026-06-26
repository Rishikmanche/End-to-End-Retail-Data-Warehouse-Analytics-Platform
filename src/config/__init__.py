"""Configuration management for the Retail Data Warehouse platform.

Provides centralized settings management via Pydantic BaseSettings,
environment variable loading, and logging configuration.
"""

from src.config.config import Settings, get_settings, setup_logging

__all__: list[str] = [
    "Settings",
    "get_settings",
    "setup_logging",
]
