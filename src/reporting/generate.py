"""
HAES HVAC - Report Generation

Assembles KPIs into report artifacts.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.reporting.schema import KPIValue, ReportData, ReportSummary, ReportType
from src.reporting.compute import compute_all_kpis
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def generate_report(
    report_type: ReportType,
    period_start: datetime,
    period_end: datetime,
    db_session: Session | None = None,
    odoo_data: dict[str, Any] | None = None,
) -> ReportData:
    """
    Generate a complete report.
    
    Args:
        report_type: Type of report to generate
        period_start: Period start datetime
        period_end: Period end datetime
        db_session: Database session for audit queries
        odoo_data: Pre-fetched Odoo data
        
    Returns:
        ReportData with all KPIs and metadata
    """
    settings = get_settings()
    
    logger.info(f"Generating {report_type.value} report for {period_start} to {period_end}")
    
    # Compute KPIs
    kpis = compute_all_kpis(
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        db_session=db_session,
        odoo_data=odoo_data,
    )
    
    # Generate notes for missing data
    notes = []
    for kpi in kpis:
        if kpi.missing_reason:
            notes.append(f"{kpi.name}: {kpi.missing_reason}")
    
    # Generate alerts (simple threshold checks)
    alerts = _check_alerts(kpis)
    
    return ReportData(
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        timezone=settings.REPORT_TIMEZONE,
        generated_at=datetime.utcnow(),
        kpis=kpis,
        notes=notes,
        alerts=alerts,
    )


def generate_summary(report: ReportData, max_chars: int = 600) -> ReportSummary:
    """
    Generate SMS-safe summary of a report.
    
    Args:
        report: Full report data
        max_chars: Maximum characters for summary
        
    Returns:
        ReportSummary with condensed metrics
    """
    # Format period string
    period_str = f"{report.period_start.strftime('%m/%d')} - {report.period_end.strftime('%m/%d')}"
    
    # Build key metrics string
    metrics_parts = []
    for kpi in report.kpis:
        if kpi.value is not None:
            if kpi.unit == "currency":
                metrics_parts.append(f"{kpi.name}: ${kpi.value:,.0f}")
            elif kpi.unit == "percent":
                metrics_parts.append(f"{kpi.name}: {kpi.value:.1f}%")
            else:
                metrics_parts.append(f"{kpi.name}: {kpi.value}")
    
    # Truncate to max chars
    key_metrics = " | ".join(metrics_parts)
    if len(key_metrics) > max_chars:
        key_metrics = key_metrics[:max_chars-3] + "..."
    
    return ReportSummary(
        report_type=report.report_type,
        period=period_str,
        key_metrics=key_metrics or "No metrics computed",
        alerts=report.alerts[:3],  # Max 3 alerts
    )


def _check_alerts(kpis: list[KPIValue]) -> list[str]:
    """Check for alert conditions."""
    alerts = []
    
    # Check error rate
    errors = next((k for k in kpis if k.kpi_id == "errors_today"), None)
    if errors and errors.value and errors.value > 10:
        alerts.append(f"High error rate: {errors.value} errors detected")
    
    # Add more alert checks as needed
    
    return alerts


def get_period_for_report_type(
    report_type: ReportType,
    reference_date: datetime | None = None,
) -> tuple[datetime, datetime]:
    """
    Calculate period start/end for a report type.
    
    Args:
        report_type: Type of report
        reference_date: Reference date (defaults to now)
        
    Returns:
        Tuple of (period_start, period_end)
    """
    if reference_date is None:
        reference_date = datetime.utcnow()
    
    if report_type == ReportType.DAILY:
        # Yesterday
        end = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
    
    elif report_type == ReportType.WEEKLY:
        # Last 7 days
        end = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=7)
    
    elif report_type == ReportType.MONTHLY:
        # Last 30 days
        end = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=30)
    
    elif report_type == ReportType.QUARTERLY:
        # Last 90 days
        end = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=90)
    
    else:  # ANNUAL
        # Last 365 days
        end = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=365)
    
    return start, end

