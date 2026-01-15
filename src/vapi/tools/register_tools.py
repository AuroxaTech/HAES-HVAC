"""
HAES HVAC - Tool Registration

Registers all Vapi tools with the tool registry.
"""

from src.vapi.tools import register_tool

# OPS tools
from src.vapi.tools.ops.create_service_request import handle_create_service_request
from src.vapi.tools.ops.schedule_appointment import handle_schedule_appointment
from src.vapi.tools.ops.check_availability import handle_check_availability
from src.vapi.tools.ops.reschedule_appointment import handle_reschedule_appointment
from src.vapi.tools.ops.cancel_appointment import handle_cancel_appointment
from src.vapi.tools.ops.check_appointment_status import handle_check_appointment_status

# REVENUE tools
from src.vapi.tools.revenue.request_quote import handle_request_quote
from src.vapi.tools.revenue.check_lead_status import handle_check_lead_status
from src.vapi.tools.revenue.request_membership_enrollment import handle_request_membership_enrollment

# CORE tools
from src.vapi.tools.core.billing_inquiry import handle_billing_inquiry
from src.vapi.tools.core.payment_terms_inquiry import handle_payment_terms_inquiry
from src.vapi.tools.core.invoice_request import handle_invoice_request
from src.vapi.tools.core.inventory_inquiry import handle_inventory_inquiry
from src.vapi.tools.core.purchase_request import handle_purchase_request
from src.vapi.tools.core.get_pricing import handle_get_pricing
from src.vapi.tools.core.create_complaint import handle_create_complaint

# PEOPLE tools
from src.vapi.tools.people.hiring_inquiry import handle_hiring_inquiry
from src.vapi.tools.people.onboarding_inquiry import handle_onboarding_inquiry
from src.vapi.tools.people.payroll_inquiry import handle_payroll_inquiry

# UTILS tools
from src.vapi.tools.utils.check_business_hours import handle_check_business_hours
from src.vapi.tools.utils.get_service_area_info import handle_get_service_area_info
from src.vapi.tools.utils.get_maintenance_plans import handle_get_maintenance_plans


def register_all_tools():
    """Register all Vapi tools."""
    # OPS tools
    register_tool("create_service_request", handle_create_service_request)
    register_tool("schedule_appointment", handle_schedule_appointment)
    register_tool("check_availability", handle_check_availability)
    register_tool("reschedule_appointment", handle_reschedule_appointment)
    register_tool("cancel_appointment", handle_cancel_appointment)
    register_tool("check_appointment_status", handle_check_appointment_status)
    
    # REVENUE tools
    register_tool("request_quote", handle_request_quote)
    register_tool("check_lead_status", handle_check_lead_status)
    register_tool("request_membership_enrollment", handle_request_membership_enrollment)
    
    # CORE tools
    register_tool("billing_inquiry", handle_billing_inquiry)
    register_tool("payment_terms_inquiry", handle_payment_terms_inquiry)
    register_tool("invoice_request", handle_invoice_request)
    register_tool("inventory_inquiry", handle_inventory_inquiry)
    register_tool("purchase_request", handle_purchase_request)
    register_tool("get_pricing", handle_get_pricing)
    register_tool("create_complaint", handle_create_complaint)
    
    # PEOPLE tools
    register_tool("hiring_inquiry", handle_hiring_inquiry)
    register_tool("onboarding_inquiry", handle_onboarding_inquiry)
    register_tool("payroll_inquiry", handle_payroll_inquiry)
    
    # UTILS tools
    register_tool("check_business_hours", handle_check_business_hours)
    register_tool("get_service_area_info", handle_get_service_area_info)
    register_tool("get_maintenance_plans", handle_get_maintenance_plans)


# Auto-register on import
register_all_tools()
