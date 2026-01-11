"""
HAES HVAC - Vapi Tool Endpoints

Vapi-facing tool endpoints for voice agent integration.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.hael import (
    Brain,
    Channel,
    RuleBasedExtractor,
    build_hael_command,
    route_command,
)
from src.brains.ops import handle_ops_command
from src.brains.core import handle_core_command
from src.brains.revenue import handle_revenue_command
from src.brains.people import handle_people_command
from src.utils.request_id import get_request_id, generate_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vapi/tools", tags=["vapi"])


class VapiToolRequest(BaseModel):
    """Request schema for Vapi tool calls."""
    request_id: str = Field(default_factory=generate_request_id)
    call_id: str
    tool_call_id: str
    user_text: str
    conversation_context: str | None = None


class VapiToolResponse(BaseModel):
    """Response schema for Vapi tool calls."""
    speak: str
    action: str  # completed, needs_human, unsupported, error
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/hael_route", response_model=VapiToolResponse)
async def hael_route(request: VapiToolRequest) -> VapiToolResponse:
    """
    Main Vapi tool endpoint for routing user requests.

    This is the single tool endpoint that Vapi calls to process
    user voice input. It runs the HAEL pipeline and routes to
    the appropriate brain.
    """
    logger.info(f"Vapi tool call: call_id={request.call_id}, tool_call_id={request.tool_call_id}")

    try:
        # Extract intent and entities
        extractor = RuleBasedExtractor()
        extraction = extractor.extract(request.user_text)

        # Route to brain
        routing = route_command(extraction)

        # Build command
        command = build_hael_command(
            request_id=request.request_id,
            channel=Channel.VOICE,
            raw_text=request.user_text,
            extraction=extraction,
            routing=routing,
            metadata={
                "call_id": request.call_id,
                "tool_call_id": request.tool_call_id,
                "conversation_context": request.conversation_context,
            },
        )

        # Route to brain handler
        if routing.brain == Brain.OPS:
            result = await handle_ops_command(command)
            speak = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        elif routing.brain == Brain.CORE:
            result = handle_core_command(command)
            speak = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        elif routing.brain == Brain.REVENUE:
            result = handle_revenue_command(command)
            speak = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        elif routing.brain == Brain.PEOPLE:
            result = handle_people_command(command)
            speak = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        else:
            # Unknown brain - needs human
            result = None
            speak = (
                "I'm not sure how to help with that. "
                "Let me connect you with a representative who can assist."
            )
            action = "needs_human"
            data = {
                "reason": "unknown_intent",
                "raw_text": request.user_text,
            }

        # Add missing fields to response if needs human
        if action == "needs_human" and result is not None and hasattr(result, "missing_fields"):
            if result.missing_fields:
                speak += f" I'll need the following information: {', '.join(result.missing_fields)}."
                data["missing_fields"] = result.missing_fields

        return VapiToolResponse(
            speak=speak,
            action=action,
            data=data,
        )

    except Exception as e:
        logger.exception(f"Error in Vapi tool route: {e}")
        return VapiToolResponse(
            speak="I'm sorry, I encountered an error. Let me connect you with a representative.",
            action="error",
            data={"error": str(e)},
        )

