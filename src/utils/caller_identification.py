"""
HAES HVAC - Caller Identification System

Hybrid employee identification using Odoo hr.employee lookup with static roster fallback.
Provides role-based access control foundation.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.brains.ops.tech_roster import (
    TECHNICIAN_ROSTER,
    Technician,
    get_technician_by_phone_static,
    normalize_phone as normalize_phone_roster,
)
from src.integrations.odoo import create_odoo_client_from_settings

logger = logging.getLogger(__name__)


class CallerRole(str, Enum):
    """Caller role for access control."""
    CUSTOMER = "customer"
    TECHNICIAN = "technician"
    HR = "hr"
    BILLING = "billing"
    MANAGER = "manager"
    DISPATCH = "dispatch"
    EXECUTIVE = "executive"
    ADMIN = "admin"
    UNKNOWN = "unknown"


@dataclass
class CallerIdentity:
    """Caller identity with role and permissions."""
    phone: str
    role: CallerRole
    employee_id: Optional[str] = None
    name: Optional[str] = None
    is_active: bool = True
    permissions: list[str] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []


# Re-export normalize_phone from tech_roster for convenience
normalize_phone = normalize_phone_roster


def determine_role_from_job(job_title: str | None) -> CallerRole:
    """
    Determine caller role from Odoo job title.
    
    Maps common job titles to roles:
    - Technician, Field Tech, Installer → TECHNICIAN
    - HR Manager, HR Coordinator, Recruiter → HR
    - Accountant, Billing Specialist, Accounts Receivable → BILLING
    - Operations Manager, Dispatch Manager, Service Manager → MANAGER
    - Dispatch Coordinator, Scheduler → DISPATCH
    - CEO, President, Owner, Executive → EXECUTIVE
    - Admin, Administrator → ADMIN
    """
    if not job_title:
        return CallerRole.UNKNOWN
    
    job_lower = job_title.lower()
    
    # Technician roles
    if any(keyword in job_lower for keyword in ["technician", "tech", "installer", "field tech", "service tech"]):
        return CallerRole.TECHNICIAN
    
    # HR roles
    if any(keyword in job_lower for keyword in ["hr", "human resources", "recruiter", "hiring"]):
        return CallerRole.HR
    
    # Billing roles
    if any(keyword in job_lower for keyword in ["billing", "accountant", "accounts receivable", "ar", "accounting"]):
        return CallerRole.BILLING
    
    # Manager roles
    if any(keyword in job_lower for keyword in ["manager", "supervisor", "director", "lead"]):
        if "dispatch" in job_lower or "scheduler" in job_lower:
            return CallerRole.DISPATCH
        return CallerRole.MANAGER
    
    # Dispatch roles
    if any(keyword in job_lower for keyword in ["dispatch", "scheduler", "coordinator"]):
        return CallerRole.DISPATCH
    
    # Executive roles
    if any(keyword in job_lower for keyword in ["ceo", "president", "owner", "executive", "vp", "vice president"]):
        return CallerRole.EXECUTIVE
    
    # Admin roles
    if any(keyword in job_lower for keyword in ["admin", "administrator"]):
        return CallerRole.ADMIN
    
    return CallerRole.UNKNOWN


def get_permissions_for_role(role: CallerRole) -> list[str]:
    """
    Get list of tool permissions for a role.
    
    Returns list of tool names this role can access.
    """
    # Base permissions for all roles
    base_permissions = [
        "check_business_hours",
        "get_service_area_info",
    ]
    
    if role == CallerRole.CUSTOMER:
        return base_permissions + [
            "create_service_request",
            "schedule_appointment",
            "reschedule_appointment",
            "cancel_appointment",
            "check_appointment_status",
            "check_availability",
            "request_quote",
            "check_lead_status",
            "request_membership_enrollment",
            "billing_inquiry",
            "invoice_request",
            "payment_terms_inquiry",
            "get_pricing",
            "get_maintenance_plans",
            "create_complaint",
        ]
    
    elif role == CallerRole.TECHNICIAN:
        return base_permissions + [
            "ivr_close_sale",
            "create_service_request",  # Technicians can create service requests
            "schedule_appointment",  # Technicians can schedule
        ]
    
    elif role == CallerRole.HR:
        return base_permissions + [
            "payroll_inquiry",
            "onboarding_inquiry",
            "hiring_inquiry",
        ]
    
    elif role == CallerRole.BILLING:
        return base_permissions + [
            "billing_inquiry",
            "invoice_request",
            "payment_terms_inquiry",
        ]
    
    elif role == CallerRole.MANAGER:
        return base_permissions + [
            "create_service_request",
            "schedule_appointment",
            "reschedule_appointment",
            "request_quote",
            "billing_inquiry",
            "invoice_request",
            "payment_terms_inquiry",
            "inventory_inquiry",
            "purchase_request",
            "ivr_close_sale",
            "payroll_inquiry",
            "onboarding_inquiry",
            "hiring_inquiry",
        ]
    
    elif role == CallerRole.DISPATCH:
        return base_permissions + [
            "create_service_request",
            "schedule_appointment",
            "reschedule_appointment",
            "inventory_inquiry",
            "purchase_request",
        ]
    
    elif role == CallerRole.EXECUTIVE:
        # Executives have access to all tools
        return base_permissions + [
            "create_service_request",
            "schedule_appointment",
            "reschedule_appointment",
            "cancel_appointment",
            "check_appointment_status",
            "check_availability",
            "request_quote",
            "check_lead_status",
            "request_membership_enrollment",
            "billing_inquiry",
            "invoice_request",
            "payment_terms_inquiry",
            "inventory_inquiry",
            "purchase_request",
            "get_pricing",
            "get_maintenance_plans",
            "create_complaint",
            "ivr_close_sale",
            "payroll_inquiry",
            "onboarding_inquiry",
            "hiring_inquiry",
        ]
    
    elif role == CallerRole.ADMIN:
        # Admins have access to all tools
        return get_permissions_for_role(CallerRole.EXECUTIVE)
    
    # Unknown role - minimal access
    return base_permissions


async def identify_from_odoo(phone: str) -> Optional[CallerIdentity]:
    """
    Identify caller from Odoo hr.employee model.
    
    Searches for employee by phone, mobile_phone, or work_phone fields.
    
    Args:
        phone: Normalized phone number
        
    Returns:
        CallerIdentity if found, None otherwise
    """
    if not phone:
        return None
    
    try:
        odoo_client = create_odoo_client_from_settings()
        if not odoo_client.is_authenticated:
            await odoo_client.authenticate()
        
        # Search for employee by phone number
        # Odoo hr.employee has phone, mobile_phone, and work_phone fields
        # Note: Field is "mobile_phone" not "mobile" in Odoo 18
        domain = [
            "|",
            "|",
            ("phone", "ilike", phone),
            ("mobile_phone", "ilike", phone),
            ("work_phone", "ilike", phone),
        ]
        
        employees = await odoo_client.search_read(
            model="hr.employee",
            domain=domain,
            fields=["id", "name", "job_title", "phone", "mobile_phone", "work_phone", "active"],
            limit=1,
        )
        
        if not employees:
            return None
        
        employee = employees[0]
        
        # Determine role from job title
        job_title = employee.get("job_title")
        role = determine_role_from_job(job_title)
        
        # Get permissions for role
        permissions = get_permissions_for_role(role)
        
        return CallerIdentity(
            phone=phone,
            role=role,
            employee_id=str(employee.get("id")),
            name=employee.get("name"),
            is_active=employee.get("active", True),
            permissions=permissions,
        )
        
    except Exception as e:
        logger.warning(f"Odoo employee lookup failed for {phone[:5]}***: {e}")
        return None


# Re-export get_technician_by_phone_static from tech_roster
# (function is already imported above)


async def identify_caller(phone: str | None) -> CallerIdentity:
    """
    Identify caller by phone number using hybrid approach.
    
    Flow:
    1. Try Odoo hr.employee lookup (supports multiple phones, dynamic)
    2. Fallback to static technician roster (fast, always available)
    3. Default to CUSTOMER if not found
    
    Args:
        phone: Phone number (any format)
        
    Returns:
        CallerIdentity with role and permissions
    """
    if not phone:
        return CallerIdentity(phone="", role=CallerRole.UNKNOWN)
    
    normalized = normalize_phone(phone)
    if not normalized:
        return CallerIdentity(phone=phone, role=CallerRole.UNKNOWN)
    
    # Step 1: Try Odoo lookup first (dynamic, supports multiple phones)
    try:
        odoo_identity = await identify_from_odoo(normalized)
        if odoo_identity:
            logger.info(
                f"Identified caller from Odoo: {odoo_identity.role.value} - {odoo_identity.name}"
            )
            return odoo_identity
    except Exception as e:
        logger.warning(f"Odoo lookup failed, using static roster: {e}")
    
    # Step 2: Fallback to static technician roster
    tech = get_technician_by_phone_static(normalized)
    if tech:
        return CallerIdentity(
            phone=normalized,
            role=CallerRole.TECHNICIAN,
            employee_id=tech.id,
            name=tech.name,
            is_active=True,
            permissions=get_permissions_for_role(CallerRole.TECHNICIAN),
        )
    
    # Step 3: Default to customer (public access)
    return CallerIdentity(
        phone=normalized,
        role=CallerRole.CUSTOMER,
        is_active=True,
        permissions=get_permissions_for_role(CallerRole.CUSTOMER),
    )
