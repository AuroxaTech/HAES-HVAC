"""
HAES HVAC Integrations Module

External service integrations:
- Odoo 18 Enterprise (Module 2)
- Odoo CRM Lead Service (Lead upsert for calls)
- Vapi.ai Voice (Module 8)
- Twilio SMS/Voice (Module 8)
"""

from src.integrations.odoo import OdooClient, create_odoo_client_from_settings
from src.integrations.odoo_leads import LeadService, create_lead_service, upsert_lead_for_call
from src.integrations.odoo_appointments import AppointmentService, create_appointment_service

# Additional integrations will be exported as implemented:
# from src.integrations.vapi_client import VapiClient  # Module 8
# from src.integrations.twilio_client import TwilioClient  # Module 8

__all__ = [
    "OdooClient",
    "create_odoo_client_from_settings",
    "LeadService",
    "create_lead_service",
    "upsert_lead_for_call",
    "AppointmentService",
    "create_appointment_service",
]

