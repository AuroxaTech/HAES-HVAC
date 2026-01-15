"""
HAES HVAC Monitoring Router

Endpoints for metrics and monitoring.
"""

from fastapi import APIRouter, Query

from src.monitoring.metrics import get_metrics
from src.monitoring.call_metrics import get_call_metrics_summary

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


@router.get("/call-metrics")
async def call_metrics(days: int = Query(default=30, ge=1, le=365)) -> dict:
    """
    Get call performance metrics summary (Test 9.1-9.5).
    
    Args:
        days: Number of days to aggregate (default: 30, max: 365)
    
    Returns:
        Dictionary with aggregated call metrics:
        - Response time metrics (Test 9.1)
        - Call completion rate (Test 9.2)
        - Data accuracy rate (Test 9.3)
        - User satisfaction average (Test 9.4)
        - Issue tracking summary (Test 9.5)
        - Target values and alerts
    """
    return get_call_metrics_summary(days=days)

