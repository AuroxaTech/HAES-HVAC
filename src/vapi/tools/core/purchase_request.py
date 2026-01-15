"""
HAES HVAC - Purchase Request Tool

Direct Vapi tool for requesting parts/equipment purchases.
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


async def handle_purchase_request(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle purchase_request tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - part_name (required): Part name
        - part_number (optional): Part number
        - quantity (required): Quantity needed
        - urgency (optional): "high", "medium", "low"
    """
    handler = BaseToolHandler("purchase_request")
    
    # Validate required parameters
    required = ["customer_name", "phone", "part_name", "quantity"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you with your purchase request.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you with your purchase request.",
            missing_fields=["phone"],
            intent_acknowledged=False,
        )
    
    # Build Entity
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=phone,
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or parameters.get("part_name", ""),
        intent=Intent.PURCHASE_REQUEST,
        brain=Brain.CORE,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
            "part_name": parameters.get("part_name"),
            "part_number": parameters.get("part_number"),
            "quantity": parameters.get("quantity"),
            "urgency": parameters.get("urgency"),
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
                "I encountered an error processing your purchase request. Please try again or contact us directly.",
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
