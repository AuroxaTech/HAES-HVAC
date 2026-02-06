"""
HAES HVAC - Lookup Customer Profile Tool

Look up an existing customer by phone and address (e.g. after they say yes to
"Have we provided service or warranty work at your house before?").
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.integrations.odoo_leads import create_lead_service

logger = logging.getLogger(__name__)


async def handle_lookup_customer_profile(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Look up a customer profile by phone and address.
    Use when the customer confirmed they have had service/warranty work at their house before.
    """
    handler = BaseToolHandler("lookup_customer_profile")
    phone = (parameters.get("phone") or "").strip()
    address = (parameters.get("address") or "").strip()
    if not phone:
        return ToolResponse(
            speak="I need a phone number to look up your profile.",
            action="needs_human",
            data={"found": False, "reason": "missing_phone"},
        )
    try:
        lead_service = await create_lead_service()
        profile = await lead_service.find_partner_by_phone_and_address(phone, address or None)
        if not profile:
            msg = "I wasn't able to find a profile with that phone." if not address else "I wasn't able to find a profile with that phone and address."
            return ToolResponse(
                speak=f"{msg} We can set you up as a new customer.",
                action="completed",
                data={"found": False},
            )
        return ToolResponse(
            speak=f"I found your profile: {profile.get('name')} at {profile.get('address') or 'your address'}. Is that correct?",
            action="needs_human",
            data={
                "found": True,
                "name": profile.get("name"),
                "address": profile.get("address"),
                "partner_id": profile.get("partner_id"),
            },
        )
    except Exception as e:
        logger.warning(f"lookup_customer_profile failed: {e}")
        return ToolResponse(
            speak="I had trouble looking that up. We can continue and set you up as a new customer.",
            action="completed",
            data={"found": False, "error": str(e)},
        )
