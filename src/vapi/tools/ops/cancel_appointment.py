"""
HAES HVAC - Cancel Appointment Tool

Direct Vapi tool for canceling appointments.
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


async def handle_cancel_appointment(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle cancel_appointment tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - address (optional): Service address (for lookup)
        - appointment_id (optional): Specific appointment ID if known
        - cancellation_reason (optional): Reason for cancellation
    """
    handler = BaseToolHandler("cancel_appointment")
    
    # Validate required parameters
    required = ["customer_name", "phone"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you cancel your appointment.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you cancel your appointment.",
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
        raw_text=conversation_context or "cancel appointment",
        intent=Intent.CANCEL_APPOINTMENT,
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
            "cancellation_reason": parameters.get("cancellation_reason"),
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
                "I encountered an error canceling your appointment. Please try again or contact us directly.",
            )
        
        # Format success response
        response_data = result.data or {}
        response_data["request_id"] = request_id
        
        # Add cancellation policy information
        from datetime import datetime, timedelta
        appointment_id = result.data.get("appointment_id") if result.data else None
        
        # Check if appointment is within 24 hours (would apply cancellation policy)
        # Note: This is a simplified check - in production, we'd look up the actual appointment time
        cancellation_policy = {
            "notice_required_hours": 24,
            "policy_text": "We request 24 hours notice for cancellations or reschedules. No-show appointments may be subject to a trip charge.",
            "applies": True,  # Policy always applies, but enforcement may vary
        }
        
        response_data["cancellation_policy"] = cancellation_policy
        
        # Enhance message with policy information
        enhanced_message = result.message
        if cancellation_policy["applies"]:
            enhanced_message += " As a reminder, we request 24 hours notice for cancellations. Thank you for letting us know in advance."
        
        return handler.format_success_response(
            enhanced_message,
            data=response_data,
        )
    
    except Exception as e:
        return handler.format_error_response(e)
