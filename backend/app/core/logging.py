"""Logging configuration shared by the API and command-line processes."""

import logging

from .config import get_settings


def configure_logging() -> None:
    """Configure structured, timestamped application logging once per process."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
