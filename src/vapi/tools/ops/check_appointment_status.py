"""
HAES HVAC - Check Appointment Status Tool

Direct Vapi tool for checking appointment status.
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
from src.brains.ops import handle_ops_command
from src.brains.ops.schema import OpsStatus
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)


async def handle_check_appointment_status(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle check_appointment_status tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - address (optional): Service address (for lookup)
        - appointment_id (optional): Specific appointment ID if known
    """
    handler = BaseToolHandler("check_appointment_status")
    
    # Validate required parameters
    required = ["customer_name", "phone"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you check your appointment status.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you check your appointment status.",
            missing_fields=["phone"],
            intent_acknowledged=False,
        )
    
    # Build Entity
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=phone,
        address=parameters.get("address"),
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or "check appointment status",
        intent=Intent.STATUS_UPDATE_REQUEST,
        brain=Brain.OPS,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
            "appointment_id": parameters.get("appointment_id"),
        },
    )
    
    # Call OPS brain handler
    try:
        result = await handle_ops_command(command)
        
        if result.requires_human or result.status == OpsStatus.NEEDS_HUMAN:
            return handler.format_needs_human_response(
                result.message,
                missing_fields=getattr(result, "missing_fields", None),
                data=result.data or {},
            )
        
        if result.status == OpsStatus.ERROR:
            return handler.format_error_response(
                Exception(result.message),
                "I encountered an error checking your appointment status. Please try again or contact us directly.",
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
