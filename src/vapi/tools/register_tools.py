"""
HAES HVAC - Tool Registration

Registers all Vapi tools with the tool registry.

Architecture (post-optimization):
  - Riley Customer Inbound: 5 in-call tools only (read-only lookups + availability)
  - Riley OPS Internal: 6 tools (ivr_close_sale + HR + operations)
  - Post-call processing: 13 tools handled by PostCallProcessor via structured outputs
  - All handlers remain registered here for Riley OPS and PostCallProcessor reuse
"""

from src.vapi.tools import register_tool

# ── IN-CALL TOOLS (Riley Customer Inbound — 5 active) ──────────────
from src.vapi.tools.ops.check_availability import handle_check_availability
from src.vapi.tools.ops.check_appointment_status import handle_check_appointment_status
from src.vapi.tools.ops.lookup_customer_profile import handle_lookup_customer_profile
from src.vapi.tools.revenue.check_lead_status import handle_check_lead_status
from src.vapi.tools.core.billing_inquiry import handle_billing_inquiry

# ── POST-CALL TOOLS (processed by PostCallProcessor, not called in-call) ──
from src.vapi.tools.ops.create_service_request import handle_create_service_request
from src.vapi.tools.ops.schedule_appointment import handle_schedule_appointment
from src.vapi.tools.ops.reschedule_appointment import handle_reschedule_appointment
from src.vapi.tools.ops.cancel_appointment import handle_cancel_appointment
from src.vapi.tools.revenue.request_quote import handle_request_quote
from src.vapi.tools.revenue.request_membership_enrollment import handle_request_membership_enrollment
from src.vapi.tools.core.payment_terms_inquiry import handle_payment_terms_inquiry
from src.vapi.tools.core.invoice_request import handle_invoice_request
from src.vapi.tools.core.get_pricing import handle_get_pricing
from src.vapi.tools.core.create_complaint import handle_create_complaint
from src.vapi.tools.utils.check_business_hours import handle_check_business_hours
from src.vapi.tools.utils.get_service_area_info import handle_get_service_area_info
from src.vapi.tools.utils.get_maintenance_plans import handle_get_maintenance_plans
from src.vapi.tools.utils.send_notification import handle_send_notification

# ── RILEY OPS INTERNAL TOOLS (6 active on OPS line) ─────────────────
from src.vapi.tools.revenue.ivr_close_sale import handle_ivr_close_sale
from src.vapi.tools.core.inventory_inquiry import handle_inventory_inquiry
from src.vapi.tools.core.purchase_request import handle_purchase_request
from src.vapi.tools.people.hiring_inquiry import handle_hiring_inquiry
from src.vapi.tools.people.onboarding_inquiry import handle_onboarding_inquiry
from src.vapi.tools.people.payroll_inquiry import handle_payroll_inquiry


def register_all_tools():
    """Register all Vapi tools.

    All tools remain registered in the dispatcher because:
    - Riley OPS assistant may still call any tool via tool-calls webhook
    - PostCallProcessor imports handler logic directly for post-call actions
    - The VAPI Dashboard controls which tools are attached to each assistant
    """
    # ── In-call tools (Riley Customer Inbound) ──
    register_tool("check_availability", handle_check_availability)
    register_tool("check_appointment_status", handle_check_appointment_status)
    register_tool("lookup_customer_profile", handle_lookup_customer_profile)
    register_tool("check_lead_status", handle_check_lead_status)
    register_tool("billing_inquiry", handle_billing_inquiry)

    # ── Post-call tools (PostCallProcessor via structured outputs) ──
    register_tool("create_service_request", handle_create_service_request)
    register_tool("schedule_appointment", handle_schedule_appointment)
    register_tool("reschedule_appointment", handle_reschedule_appointment)
    register_tool("cancel_appointment", handle_cancel_appointment)
    register_tool("request_quote", handle_request_quote)
    register_tool("request_membership_enrollment", handle_request_membership_enrollment)
    register_tool("payment_terms_inquiry", handle_payment_terms_inquiry)
    register_tool("invoice_request", handle_invoice_request)
    register_tool("get_pricing", handle_get_pricing)
    register_tool("create_complaint", handle_create_complaint)
    register_tool("check_business_hours", handle_check_business_hours)
    register_tool("get_service_area_info", handle_get_service_area_info)
    register_tool("get_maintenance_plans", handle_get_maintenance_plans)
    register_tool("send_notification", handle_send_notification)

    # ── Riley OPS internal tools ──
    register_tool("ivr_close_sale", handle_ivr_close_sale)
    register_tool("inventory_inquiry", handle_inventory_inquiry)
    register_tool("purchase_request", handle_purchase_request)
    register_tool("hiring_inquiry", handle_hiring_inquiry)
    register_tool("onboarding_inquiry", handle_onboarding_inquiry)
    register_tool("payroll_inquiry", handle_payroll_inquiry)


# Auto-register on import
register_all_tools()
