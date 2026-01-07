"""
HAES HVAC - Webhooks Module

Inbound webhook handlers:
- Vapi.ai call lifecycle webhooks (Module 8)
- Other integration webhooks
"""

from src.webhooks.vapi import router as vapi_webhooks_router

__all__ = ["vapi_webhooks_router"]

