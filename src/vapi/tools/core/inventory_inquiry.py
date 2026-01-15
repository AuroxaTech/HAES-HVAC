"""
HAES HVAC - Inventory Inquiry Tool

Direct Vapi tool for checking parts/equipment availability.
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


async def handle_inventory_inquiry(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle inventory_inquiry tool call.
    
    Parameters:
        - part_name (required): Part name
        - part_number (optional): Part number
        - quantity (optional): Required quantity
    """
    handler = BaseToolHandler("inventory_inquiry")
    
    # Validate required parameters
    required = ["part_name"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you check parts availability.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Build Entity (inventory doesn't need customer info, but handler expects Entity)
    entities = Entity()
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or parameters.get("part_name", ""),
        intent=Intent.INVENTORY_INQUIRY,
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
                "I encountered an error checking inventory. Please try again or contact us directly.",
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
