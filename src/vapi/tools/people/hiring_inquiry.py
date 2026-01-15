"""
HAES HVAC - Hiring Inquiry Tool

Direct Vapi tool for hiring inquiries.
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


async def handle_hiring_inquiry(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle hiring_inquiry tool call.
    
    Parameters:
        None (general inquiry)
    """
    handler = BaseToolHandler("hiring_inquiry")
    
    # Build Entity (hiring inquiry doesn't require customer info)
    entities = Entity()
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or "hiring inquiry",
        intent=Intent.HIRING_INQUIRY,
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
                "I encountered an error retrieving hiring information. Please try again or contact us directly.",
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
