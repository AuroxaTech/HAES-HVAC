"""
HAES HVAC - KPI Computation

Functions to compute KPI values from data sources.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.db.models import AuditLog
from src.reporting.schema import KPISource, KPIValue, ReportType
from src.reporting.kpi_catalog import get_computable_kpis, get_kpi_by_id

logger = logging.getLogger(__name__)


def compute_kpi(
    kpi_id: str,
    period_start: datetime,
    period_end: datetime,
    db_session: Session | None = None,
    odoo_data: dict[str, Any] | None = None,
) -> KPIValue:
    """
    Compute a single KPI value.
    
    Args:
        kpi_id: KPI identifier
        period_start: Period start
        period_end: Period end
        db_session: Database session for audit_log queries
        odoo_data: Pre-fetched Odoo data
        
    Returns:
        KPIValue with computed value or missing reason
    """
    kpi_def = get_kpi_by_id(kpi_id)
    if not kpi_def:
        return KPIValue(
            kpi_id=kpi_id,
            name="Unknown KPI",
            value=None,
            unit="unknown",
            source=KPISource.COMPUTED,
            computed_at=datetime.utcnow(),
            missing_reason=f"KPI {kpi_id} not found in catalog",
        )
    
    if not kpi_def.computable:
        return KPIValue(
            kpi_id=kpi_id,
            name=kpi_def.name,
            value=None,
            unit=kpi_def.unit,
            source=kpi_def.source,
            computed_at=datetime.utcnow(),
            missing_reason=kpi_def.missing_reason,
        )
    
    # Compute based on source
    try:
        if kpi_def.source == KPISource.AUDIT_LOG:
            value = _compute_from_audit_log(kpi_id, period_start, period_end, db_session)
        elif kpi_def.source == KPISource.ODOO:
            value = _compute_from_odoo(kpi_id, period_start, period_end, odoo_data)
        else:
            value = _compute_derived(kpi_id, period_start, period_end, db_session, odoo_data)
        
        return KPIValue(
            kpi_id=kpi_id,
            name=kpi_def.name,
            value=value,
            unit=kpi_def.unit,
            source=kpi_def.source,
            computed_at=datetime.utcnow(),
        )
    except Exception as e:
        logger.exception(f"Error computing KPI {kpi_id}: {e}")
        return KPIValue(
            kpi_id=kpi_id,
            name=kpi_def.name,
            value=None,
            unit=kpi_def.unit,
            source=kpi_def.source,
            computed_at=datetime.utcnow(),
            missing_reason=f"Computation error: {str(e)}",
        )


def _compute_from_audit_log(
    kpi_id: str,
    period_start: datetime,
    period_end: datetime,
    db_session: Session | None,
) -> int | float | None:
    """Compute KPI from audit log."""
    if not db_session:
        return None
    
    if kpi_id == "calls_received":
        count = db_session.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.channel == "voice",
                AuditLog.created_at >= period_start,
                AuditLog.created_at < period_end,
            )
        ).scalar()
        return count or 0
    
    elif kpi_id == "appointments_booked":
        count = db_session.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.intent.in_(["service_request", "schedule_appointment"]),
                AuditLog.status == "processed",
                AuditLog.created_at >= period_start,
                AuditLog.created_at < period_end,
            )
        ).scalar()
        return count or 0
    
    elif kpi_id == "errors_today":
        count = db_session.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.status == "error",
                AuditLog.created_at >= period_start,
                AuditLog.created_at < period_end,
            )
        ).scalar()
        return count or 0
    
    return None


def _compute_from_odoo(
    kpi_id: str,
    period_start: datetime,
    period_end: datetime,
    odoo_data: dict[str, Any] | None,
) -> int | float | None:
    """Compute KPI from Odoo data."""
    # In production, this would query Odoo
    # For now, return None with placeholder
    if not odoo_data:
        return None
    
    return odoo_data.get(kpi_id)


def _compute_derived(
    kpi_id: str,
    period_start: datetime,
    period_end: datetime,
    db_session: Session | None,
    odoo_data: dict[str, Any] | None,
) -> int | float | None:
    """Compute derived/calculated KPIs."""
    # Placeholder for computed metrics
    return None


def compute_all_kpis(
    report_type: ReportType,
    period_start: datetime,
    period_end: datetime,
    db_session: Session | None = None,
    odoo_data: dict[str, Any] | None = None,
) -> list[KPIValue]:
    """
    Compute all KPIs for a report type.
    
    Args:
        report_type: Type of report
        period_start: Period start
        period_end: Period end
        db_session: Database session
        odoo_data: Pre-fetched Odoo data
        
    Returns:
        List of computed KPI values
    """
    kpis = get_computable_kpis(report_type)
    results = []
    
    for kpi_def in kpis:
        result = compute_kpi(
            kpi_id=kpi_def.id,
            period_start=period_start,
            period_end=period_end,
            db_session=db_session,
            odoo_data=odoo_data,
        )
        results.append(result)
    
    return results

