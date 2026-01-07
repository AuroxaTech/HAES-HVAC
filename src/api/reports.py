"""
HAES HVAC - Reports API

Endpoints for report generation and retrieval.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.reporting.schema import ReportData, ReportType, ReportSummary
from src.reporting.generate import generate_report, generate_summary, get_period_for_report_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRunRequest(BaseModel):
    """Request to run a report."""
    report_type: ReportType
    period_start: datetime | None = None
    period_end: datetime | None = None


class ReportResponse(BaseModel):
    """Report response wrapper."""
    report: ReportData
    summary: ReportSummary


@router.get("/latest")
async def get_latest_report(
    type: ReportType = Query(default=ReportType.DAILY),
) -> dict[str, Any]:
    """
    Get the most recent report of a given type.
    
    Note: In production, this would fetch from report_runs table.
    For MVP, generates on-demand.
    """
    period_start, period_end = get_period_for_report_type(type)
    
    report = generate_report(
        report_type=type,
        period_start=period_start,
        period_end=period_end,
    )
    
    summary = generate_summary(report)
    
    return {
        "report": report.model_dump(),
        "summary": summary.model_dump(),
    }


@router.post("/run-once")
async def run_report_once(request: ReportRunRequest) -> dict[str, Any]:
    """
    Generate a report on-demand.
    
    Admin endpoint for immediate report generation.
    """
    if request.period_start and request.period_end:
        period_start = request.period_start
        period_end = request.period_end
    else:
        period_start, period_end = get_period_for_report_type(request.report_type)
    
    report = generate_report(
        report_type=request.report_type,
        period_start=period_start,
        period_end=period_end,
    )
    
    summary = generate_summary(report)
    
    return {
        "status": "generated",
        "report": report.model_dump(),
        "summary": summary.model_dump(),
    }


@router.get("/runs")
async def list_report_runs(
    type: ReportType | None = None,
    limit: int = Query(default=10, le=100),
) -> dict[str, Any]:
    """
    List stored report runs.
    
    Note: In production, this would query report_runs table.
    """
    return {
        "runs": [],
        "total": 0,
        "note": "Report persistence pending database integration",
    }

