"""
HAES HVAC Logging Configuration

Structured logging with request ID correlation.
"""

import logging
import sys
from typing import Any

from src.utils.request_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Add request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class StructuredFormatter(logging.Formatter):
    """Structured log formatter with request ID."""

    def format(self, record: logging.LogRecord) -> str:
        # Ensure request_id attribute exists
        if not hasattr(record, "request_id"):
            record.request_id = "-"

        # Generate timestamp using the formatter's formatTime method
        timestamp = self.formatTime(record, self.datefmt)

        return (
            f"{timestamp} | {record.levelname:8} | "
            f"[{record.request_id}] | {record.name} | {record.getMessage()}"
        )


def setup_logging(level: str = "INFO") -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # Add formatter and filter
    formatter = StructuredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())

    root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    return logger


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra: Any,
) -> None:
    """
    Log an HTTP request in a structured format.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **extra: Additional fields to log
    """
    extra_str = " | ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
    logger.info(
        f"{method} {path} | status={status_code} | duration_ms={duration_ms:.2f}"
        + (f" | {extra_str}" if extra_str else "")
    )

