"""
HAES HVAC Integrations Module

External service integrations:
- Odoo 18 Enterprise (Module 2)
- Vapi.ai Voice (Module 8)
- Twilio SMS/Voice (Module 8)
"""

from src.integrations.odoo import OdooClient, create_odoo_client_from_settings

# Additional integrations will be exported as implemented:
# from src.integrations.vapi_client import VapiClient  # Module 8
# from src.integrations.twilio_client import TwilioClient  # Module 8

__all__ = ["OdooClient", "create_odoo_client_from_settings"]

