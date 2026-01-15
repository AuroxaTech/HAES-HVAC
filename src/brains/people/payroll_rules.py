"""
HAES HVAC - PEOPLE Brain Payroll Rules

Payroll and commission rules from RDD Section 6.
"""

from datetime import datetime, date
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
    Get commission rate for a service type (legacy - fixed rates).

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


def get_tenure_based_commission_rate(employee_start_date: date | datetime, calculation_date: date | datetime | None = None) -> float:
    """
    Get commission rate based on employee tenure (Test 6.2).
    
    Rules:
    - 0-24 months: 16% commission
    - 4+ years: 20% commission
    - Between 24 months and 4 years: Default to 16% (or could be configured)
    
    Args:
        employee_start_date: Employee hire/start date
        calculation_date: Date to calculate tenure from (defaults to today)
        
    Returns:
        Commission rate as percentage (16.0 or 20.0)
    """
    if calculation_date is None:
        calculation_date = date.today()
    
    # Convert datetime to date if needed
    if isinstance(employee_start_date, datetime):
        employee_start_date = employee_start_date.date()
    if isinstance(calculation_date, datetime):
        calculation_date = calculation_date.date()
    
    # Calculate tenure in months
    years_diff = calculation_date.year - employee_start_date.year
    months_diff = calculation_date.month - employee_start_date.month
    total_months = years_diff * 12 + months_diff
    
    # Adjust if day of month hasn't been reached yet
    if calculation_date.day < employee_start_date.day:
        total_months -= 1
    
    # Apply tenure-based rates
    if total_months < 24:
        # 0-24 months: 16%
        return 16.0
    elif total_months >= 48:  # 4 years = 48 months
        # 4+ years: 20%
        return 20.0
    else:
        # 24-47 months: Default to 16% (could be configured to a different rate)
        return 16.0


def calculate_commission_split(
    selling_tech_id: str,
    completing_tech_id: str,
    commission_amount: float,
    is_approved_transfer: bool = False,
) -> dict[str, float]:
    """
    Calculate commission split for transferred work (Test 6.4).
    
    Rules:
    - Approved transfer: 40% to selling tech, 60% to completing tech
    - Unapproved transfer: 100% to selling tech OR forfeit if doesn't return
    
    Args:
        selling_tech_id: Technician who sold/diagnosed the work
        completing_tech_id: Technician who completed the work
        commission_amount: Total commission amount
        is_approved_transfer: Whether transfer was approved by management
        
    Returns:
        Dictionary with commission amounts for each tech
    """
    if is_approved_transfer:
        # Approved transfer: 40/60 split
        selling_commission = commission_amount * 0.40
        completing_commission = commission_amount * 0.60
    else:
        # Unapproved transfer: 100% to selling tech (or forfeit if doesn't return)
        # For now, we'll give 100% to selling tech - forfeit logic would be handled separately
        selling_commission = commission_amount
        completing_commission = 0.0
    
    return {
        selling_tech_id: selling_commission,
        completing_tech_id: completing_commission,
    }


def calculate_commission(
    employee_id: str,
    period_start: datetime,
    period_end: datetime,
    repair_invoices: list[dict[str, Any]],
    install_invoices: list[dict[str, Any]],
    employee_start_date: date | datetime | None = None,
    equipment_sales: float = 0.0,
) -> PayrollCalculation:
    """
    Calculate commission for an employee (Test 6.2).

    From RDD:
    - Legacy rates: Repairs 15%, Installs 5%
    - Tenure-based rates (if employee_start_date provided):
      - 0-24 months: 16% commission
      - 4+ years: 20% commission
    - Equipment bonus: 2.5% of equipment sales
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
        employee_start_date: Employee hire/start date (for tenure-based rates)
        equipment_sales: Total equipment sales amount (for 2.5% bonus)

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

    # Determine commission rates (tenure-based or legacy fixed rates)
    if employee_start_date:
        # Use tenure-based rate for service work
        service_rate = get_tenure_based_commission_rate(employee_start_date, period_end)
        repair_rate = service_rate / 100.0
        install_rate = 0.05  # Installs still at 5% per RDD
    else:
        # Legacy fixed rates
        repair_rate = 15.0 / 100.0
        install_rate = 5.0 / 100.0

    # Calculate service commissions
    repair_commission = repair_total * repair_rate
    install_commission = install_total * install_rate
    
    # Calculate equipment bonus (2.5% of equipment sales)
    equipment_bonus = equipment_sales * (2.5 / 100.0)
    
    total_commission = repair_commission + install_commission + equipment_bonus

    # Eligible = invoiced, Payable = collected
    repair_eligible = repair_total * repair_rate
    repair_payable = repair_collected * repair_rate
    install_eligible = install_total * install_rate
    install_payable = install_collected * install_rate
    equipment_eligible = equipment_sales * (2.5 / 100.0)  # Equipment bonus eligible on sale
    equipment_payable = equipment_eligible  # Equipment bonus paid when equipment sold

    commission_eligible = repair_eligible + install_eligible + equipment_eligible
    commission_payable = repair_payable + install_payable + equipment_payable

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


# Installation bonus rates from RDD
# Complete Split System (3 pieces): $1,050
# Other installation types: TBD based on RDD
INSTALLATION_BONUS_RATES: dict[str, float] = {
    "complete_split_system": 1050.0,
    "split_system_3_pieces": 1050.0,
    "furnace_only": 350.0,  # Estimated
    "air_conditioner_only": 350.0,  # Estimated
    "heat_pump": 500.0,  # Estimated
    "ductless_mini_split": 400.0,  # Estimated
}


def calculate_installation_bonus(
    installation_type: str,
    crew_member_ids: list[str],
) -> dict[str, Any]:
    """
    Calculate installation bonus and split evenly among crew (Test 6.3).
    
    Args:
        installation_type: Type of installation (e.g., "complete_split_system", "split_system_3_pieces")
        crew_member_ids: List of technician IDs in the installation crew
        
    Returns:
        Dictionary with:
        - total_bonus: Total bonus amount
        - bonus_per_technician: Bonus amount per technician (split evenly)
        - crew_count: Number of crew members
        - installation_type: Type of installation
        - crew_bonuses: Dict mapping technician_id to bonus amount
    """
    installation_type_lower = installation_type.lower().replace(" ", "_")
    
    # Find matching bonus rate
    total_bonus = None
    for key, rate in INSTALLATION_BONUS_RATES.items():
        if key in installation_type_lower or installation_type_lower in key:
            total_bonus = rate
            break
    
    # Default bonus if not found (use complete split system as default)
    if total_bonus is None:
        total_bonus = INSTALLATION_BONUS_RATES.get("complete_split_system", 1050.0)
    
    # Split evenly among crew
    crew_count = len(crew_member_ids) if crew_member_ids else 1
    if crew_count == 0:
        crew_count = 1  # Prevent division by zero
    
    bonus_per_technician = total_bonus / crew_count
    
    # Create mapping of technician to bonus
    crew_bonuses = {
        tech_id: bonus_per_technician
        for tech_id in crew_member_ids
    }
    
    return {
        "total_bonus": total_bonus,
        "bonus_per_technician": bonus_per_technician,
        "crew_count": crew_count,
        "installation_type": installation_type,
        "crew_bonuses": crew_bonuses,
    }


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
        "installation_bonus_rates": INSTALLATION_BONUS_RATES,
    }

