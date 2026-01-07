"""
HAES HVAC Monitoring Router

Endpoints for metrics and monitoring.
"""

from fastapi import APIRouter

from src.monitoring.metrics import get_metrics

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def metrics() -> dict:
    """
    Get application metrics.

    Returns:
        Dictionary of metric values including:
        - uptime_seconds: Time since application start
        - requests_total: Total HTTP requests processed
        - environment: Current environment
    """
    return get_metrics()

