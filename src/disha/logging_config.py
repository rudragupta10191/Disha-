"""Logging setup for the Disha command-line runtime."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure a concise stderr logger for the CLI."""

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(levelname)s %(name)s: %(message)s",
    )
