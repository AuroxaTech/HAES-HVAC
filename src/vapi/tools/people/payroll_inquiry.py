"""
HAES HVAC - Payroll Inquiry Tool

Direct Vapi tool for payroll inquiries.
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
from src.brains.people import handle_people_command
from src.brains.people.schema import PeopleStatus
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)


async def handle_payroll_inquiry(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle payroll_inquiry tool call.
    
    Parameters:
        - employee_email (required): Employee email
        - employee_name (optional): Employee name
    """
    handler = BaseToolHandler("payroll_inquiry")
    
    # Validate required parameters
    required = ["employee_email"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you with payroll information.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Build Entity
    entities = Entity(
        email=handler.normalize_email(parameters.get("employee_email")),
        full_name=parameters.get("employee_name"),
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or "payroll inquiry",
        intent=Intent.PAYROLL_INQUIRY,
        brain=Brain.PEOPLE,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
        },
    )
    
    # Call PEOPLE brain handler
    try:
        result = handle_people_command(command)
        
        if result.requires_human or result.status == PeopleStatus.NEEDS_HUMAN:
            return handler.format_needs_human_response(
                result.message,
                missing_fields=getattr(result, "missing_fields", None),
                data=result.data or {},
            )
        
        if result.status == PeopleStatus.ERROR:
            return handler.format_error_response(
                Exception(result.message),
                "I encountered an error retrieving payroll information. Please try again or contact us directly.",
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
