"""
HAES HVAC - KPI Catalog

KPI definitions from RDD Section 3.4.
"""

from src.reporting.schema import KPIDefinition, KPISource, ReportType


# KPI catalog from RDD
KPI_CATALOG: list[KPIDefinition] = [
    # Daily KPIs
    KPIDefinition(
        id="revenue_collected_today",
        name="Revenue Collected Today",
        description="Total payments received today",
        source=KPISource.ODOO,
        unit="currency",
        report_types=[ReportType.DAILY],
    ),
    KPIDefinition(
        id="revenue_billed_today",
        name="Revenue Billed Today",
        description="Total invoices issued today",
        source=KPISource.ODOO,
        unit="currency",
        report_types=[ReportType.DAILY],
    ),
    KPIDefinition(
        id="outstanding_ar",
        name="Outstanding AR Balance",
        description="Total accounts receivable",
        source=KPISource.ODOO,
        unit="currency",
        report_types=[ReportType.DAILY, ReportType.WEEKLY],
    ),
    KPIDefinition(
        id="calls_received",
        name="Calls Received",
        description="Total inbound voice calls",
        source=KPISource.AUDIT_LOG,
        unit="count",
        report_types=[ReportType.DAILY],
    ),
    KPIDefinition(
        id="appointments_booked",
        name="Appointments Booked",
        description="Service appointments scheduled",
        source=KPISource.AUDIT_LOG,
        unit="count",
        report_types=[ReportType.DAILY],
    ),
    KPIDefinition(
        id="jobs_completed",
        name="Jobs Completed",
        description="Work orders marked complete",
        source=KPISource.ODOO,
        unit="count",
        report_types=[ReportType.DAILY],
    ),
    KPIDefinition(
        id="errors_today",
        name="System Errors",
        description="Errors encountered in processing",
        source=KPISource.AUDIT_LOG,
        unit="count",
        report_types=[ReportType.DAILY],
    ),

    # Weekly KPIs
    KPIDefinition(
        id="lead_count_week",
        name="Leads This Week",
        description="New leads created",
        source=KPISource.ODOO,
        unit="count",
        report_types=[ReportType.WEEKLY],
    ),
    KPIDefinition(
        id="conversion_rate",
        name="Conversion Rate",
        description="Leads converted to jobs",
        source=KPISource.COMPUTED,
        unit="percent",
        report_types=[ReportType.WEEKLY, ReportType.MONTHLY],
    ),
    KPIDefinition(
        id="avg_ticket_size",
        name="Average Ticket Size",
        description="Average invoice amount",
        source=KPISource.ODOO,
        unit="currency",
        report_types=[ReportType.WEEKLY, ReportType.MONTHLY],
    ),

    # Monthly KPIs
    KPIDefinition(
        id="total_revenue_month",
        name="Total Revenue",
        description="Total revenue for the month",
        source=KPISource.ODOO,
        unit="currency",
        report_types=[ReportType.MONTHLY],
    ),
    KPIDefinition(
        id="payroll_percent",
        name="Payroll % of Revenue",
        description="Payroll cost as percentage of revenue",
        source=KPISource.COMPUTED,
        unit="percent",
        report_types=[ReportType.MONTHLY],
        computable=False,
        missing_reason="Payroll data integration pending",
    ),
    KPIDefinition(
        id="customer_satisfaction",
        name="Customer Satisfaction",
        description="Average customer rating",
        source=KPISource.ODOO,
        unit="rating",
        report_types=[ReportType.MONTHLY],
        computable=False,
        missing_reason="Rating system not configured",
    ),
]


def get_kpis_for_report_type(report_type: ReportType) -> list[KPIDefinition]:
    """Get KPIs applicable to a report type."""
    return [kpi for kpi in KPI_CATALOG if report_type in kpi.report_types]


def get_computable_kpis(report_type: ReportType) -> list[KPIDefinition]:
    """Get KPIs that can be computed for a report type."""
    return [
        kpi for kpi in KPI_CATALOG
        if report_type in kpi.report_types and kpi.computable
    ]


def get_kpi_by_id(kpi_id: str) -> KPIDefinition | None:
    """Get KPI definition by ID."""
    for kpi in KPI_CATALOG:
        if kpi.id == kpi_id:
            return kpi
    return None

