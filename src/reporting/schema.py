"""
HAES HVAC - Reporting Schema

Pydantic models for KPI and reporting.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Report type/frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class KPISource(str, Enum):
    """Data source for KPI."""
    ODOO = "odoo"
    AUDIT_LOG = "audit_log"
    COMPUTED = "computed"


class KPIDefinition(BaseModel):
    """Definition of a KPI metric."""
    id: str
    name: str
    description: str
    source: KPISource
    unit: str  # currency, count, percent, etc.
    report_types: list[ReportType]
    computable: bool = True
    missing_reason: str | None = None


class KPIValue(BaseModel):
    """Computed KPI value."""
    kpi_id: str
    name: str
    value: float | int | None
    unit: str
    source: KPISource
    computed_at: datetime
    missing_reason: str | None = None


class ReportData(BaseModel):
    """Generated report data."""
    report_type: ReportType
    period_start: datetime
    period_end: datetime
    timezone: str
    generated_at: datetime
    kpis: list[KPIValue] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


class ReportSummary(BaseModel):
    """SMS-safe summary of a report."""
    report_type: ReportType
    period: str
    key_metrics: str  # Max 600 chars
    alerts: list[str] = Field(default_factory=list)

