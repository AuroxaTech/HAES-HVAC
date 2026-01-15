"""
HAES HVAC - Invoice Request Tool

Direct Vapi tool for requesting invoice copies.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.hael.schema import (
    Channel,
    Entity,
    HaelCommand,
    Intent,
    Brain,
)
from src.brains.core import handle_core_command
from src.brains.core.schema import CoreStatus
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)


async def handle_invoice_request(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle invoice_request tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (optional): Phone number
        - email (optional): Email address
        - invoice_number (optional): Specific invoice number
    """
    handler = BaseToolHandler("invoice_request")
    
    # Validate required parameters - need phone OR email
    customer_name = parameters.get("customer_name")
    phone = parameters.get("phone")
    email = parameters.get("email")
    
    missing = []
    if not customer_name:
        missing.append("customer_name")
    if not phone and not email:
        missing.append("phone or email")
    
    if missing:
        return handler.format_needs_human_response(
            "I can help you get a copy of your invoice.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Build Entity
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=handler.normalize_phone(parameters.get("phone")),
        email=handler.normalize_email(parameters.get("email")),
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or "invoice request",
        intent=Intent.INVOICE_REQUEST,
        brain=Brain.CORE,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
            "invoice_number": parameters.get("invoice_number"),
        },
    )
    
    # Call CORE brain handler
    try:
        result = handle_core_command(command)
        
        if result.requires_human or result.status == CoreStatus.NEEDS_HUMAN:
            return handler.format_needs_human_response(
                result.message,
                missing_fields=getattr(result, "missing_fields", None),
                data=result.data or {},
            )
        
        if result.status == CoreStatus.ERROR:
            return handler.format_error_response(
                Exception(result.message),
                "I encountered an error retrieving your invoice. Please try again or contact us directly.",
            )
        
        # Format success response
        response_data = result.data or {}
        response_data["request_id"] = request_id
        
        return handler.format_success_response(
            result.message,
            data=response_data,
        )
    
    except Exception as e:
        return handler.format_error_response(e)
