"""
HAES HVAC - Check Lead Status Tool

Direct Vapi tool for checking quote/lead status.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.integrations.odoo import create_odoo_client_from_settings

logger = logging.getLogger(__name__)


async def handle_check_lead_status(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle check_lead_status tool call.
    
    Parameters:
        - customer_name (optional): Customer name
        - phone (optional): Phone number
        - email (optional): Email address
        - lead_id (optional): Specific lead ID if known
    """
    handler = BaseToolHandler("check_lead_status")
    
    # Need at least one identifier
    if not any([parameters.get("customer_name"), parameters.get("phone"), parameters.get("email"), parameters.get("lead_id")]):
        return handler.format_needs_human_response(
            "I can help you check your quote status.",
            missing_fields=["customer_name", "phone", "email", "lead_id"],
            intent_acknowledged=False,
        )
    
    try:
        odoo_client = handler.get_odoo_client()
        await odoo_client.authenticate()
        
        # Look up lead
        lead_id = parameters.get("lead_id")
        if lead_id:
            # Direct lookup by ID
            leads = await odoo_client.search_read(
                "crm.lead",
                domain=[("id", "=", int(lead_id))],
                fields=["name", "stage_id", "probability", "expected_revenue", "partner_id"],
            )
        else:
            # Search by contact info
            domain = []
            if parameters.get("phone"):
                domain.append(("phone", "=", handler.normalize_phone(parameters["phone"])))
            if parameters.get("email"):
                domain.append(("email_from", "=", handler.normalize_email(parameters["email"])))
            if parameters.get("customer_name"):
                domain.append(("contact_name", "ilike", parameters["customer_name"]))
            
            if not domain:
                return handler.format_needs_human_response(
                    "I couldn't find your lead. Please provide your name, phone, email, or lead ID.",
                )
            
            leads = await odoo_client.search_read(
                "crm.lead",
                domain=domain,
                fields=["name", "stage_id", "probability", "expected_revenue", "partner_id"],
                limit=1,
                order="create_date desc",
            )
        
        if not leads:
            return ToolResponse(
                speak="I couldn't find a lead matching that information. Would you like me to create a new quote request?",
                action="needs_human",
                data={"lead_not_found": True},
            )
        
        lead = leads[0]
        
        # Get stage name
        stage_id = lead.get("stage_id")
        stage_name = "Unknown"
        if stage_id and isinstance(stage_id, list) and len(stage_id) > 1:
            stage_name = stage_id[1]
        
        # Format response
        message = f"Your quote request is in the {stage_name} stage."
        if lead.get("expected_revenue"):
            message += f" Estimated value: ${lead.get('expected_revenue', 0):,.2f}"
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "lead_id": lead.get("id"),
                "lead_name": lead.get("name"),
                "stage": stage_name,
                "probability": lead.get("probability", 0),
                "expected_revenue": lead.get("expected_revenue", 0),
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
