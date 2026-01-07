"""
HAES HVAC Metrics Collection

Simple in-memory metrics for basic monitoring.
"""

import time
from threading import Lock
from typing import Any

from src.config.settings import get_settings

# Application start time
_start_time: float = time.time()

# Request counter with thread-safe access
_requests_total: int = 0
_requests_lock: Lock = Lock()

# Error counter
_errors_total: int = 0
_errors_lock: Lock = Lock()


def increment_requests() -> None:
    """Increment the total requests counter."""
    global _requests_total
    with _requests_lock:
        _requests_total += 1


def increment_errors() -> None:
    """Increment the total errors counter."""
    global _errors_total
    with _errors_lock:
        _errors_total += 1


def get_uptime_seconds() -> float:
    """
    Get application uptime in seconds.

    Returns:
        Seconds since application start
    """
    return time.time() - _start_time


def get_requests_total() -> int:
    """
    Get total requests processed.

    Returns:
        Total request count
    """
    with _requests_lock:
        return _requests_total


def get_errors_total() -> int:
    """
    Get total errors encountered.

    Returns:
        Total error count
    """
    with _errors_lock:
        return _errors_total


def get_metrics() -> dict[str, Any]:
    """
    Get all metrics as a dictionary.

    Returns:
        Dictionary containing all metric values
    """
    settings = get_settings()
    return {
        "uptime_seconds": round(get_uptime_seconds(), 2),
        "requests_total": get_requests_total(),
        "errors_total": get_errors_total(),
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }

