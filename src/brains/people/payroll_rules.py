"""
HAES HVAC - PEOPLE Brain Payroll Rules

Payroll and commission rules from RDD Section 6.
"""

from datetime import datetime
from typing import Any

from src.brains.people.schema import CommissionRule, PayrollCalculation, PayrollPeriod


# Payroll configuration from RDD
PAY_PERIOD = PayrollPeriod.BIWEEKLY

# Commission rules from RDD Section 6
# Repairs: 15% of sales
# Installs: 5% of sales
# Paid on: invoice AND collection (both checked in RDD)

COMMISSION_RULES: list[CommissionRule] = [
    CommissionRule(
        type="repairs",
        rate_percent=15.0,
        paid_on="both",  # invoice and collection
    ),
    CommissionRule(
        type="installs",
        rate_percent=5.0,
        paid_on="both",  # invoice and collection
    ),
]


def get_commission_rate(service_type: str) -> float:
    """
    Get commission rate for a service type.

    Args:
        service_type: Type of service (repairs, installs)

    Returns:
        Commission rate as percentage
    """
    service_lower = service_type.lower()

    if "install" in service_lower:
        return 5.0
    elif "repair" in service_lower:
        return 15.0
    else:
        # Default to repair rate
        return 15.0


def calculate_commission(
    employee_id: str,
    period_start: datetime,
    period_end: datetime,
    repair_invoices: list[dict[str, Any]],
    install_invoices: list[dict[str, Any]],
) -> PayrollCalculation:
    """
    Calculate commission for an employee.

    From RDD:
    - Repairs: 15% commission
    - Installs: 5% commission
    - Commission paid on: invoice AND collection (both checked)

    Interpretation:
    - commission_eligible: Based on invoiced amount
    - commission_payable: Based on collected amount

    Args:
        employee_id: Employee identifier
        period_start: Period start date
        period_end: Period end date
        repair_invoices: List of repair invoices with amount and collected status
        install_invoices: List of install invoices with amount and collected status

    Returns:
        PayrollCalculation with commission breakdown
    """
    # Calculate repair totals
    repair_total = sum(inv.get("amount", 0) for inv in repair_invoices)
    repair_collected = sum(
        inv.get("amount", 0) for inv in repair_invoices
        if inv.get("collected", False)
    )

    # Calculate install totals
    install_total = sum(inv.get("amount", 0) for inv in install_invoices)
    install_collected = sum(
        inv.get("amount", 0) for inv in install_invoices
        if inv.get("collected", False)
    )

    # Calculate commissions
    repair_commission = repair_total * (15.0 / 100)
    install_commission = install_total * (5.0 / 100)
    total_commission = repair_commission + install_commission

    # Eligible = invoiced, Payable = collected
    repair_eligible = repair_total * (15.0 / 100)
    repair_payable = repair_collected * (15.0 / 100)
    install_eligible = install_total * (5.0 / 100)
    install_payable = install_collected * (5.0 / 100)

    commission_eligible = repair_eligible + install_eligible
    commission_payable = repair_payable + install_payable

    # Check if there's uncollected commission
    requires_verification = commission_eligible > commission_payable

    return PayrollCalculation(
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
        repair_sales=repair_total,
        install_sales=install_total,
        repair_commission=repair_commission,
        install_commission=install_commission,
        total_commission=total_commission,
        commission_eligible=commission_eligible,
        commission_payable=commission_payable,
        requires_collection_verification=requires_verification,
    )


def get_payroll_summary() -> dict:
    """Get payroll configuration summary."""
    return {
        "pay_period": PAY_PERIOD.value,
        "commission_rules": [
            {
                "type": rule.type,
                "rate_percent": rule.rate_percent,
                "paid_on": rule.paid_on,
            }
            for rule in COMMISSION_RULES
        ],
    }

