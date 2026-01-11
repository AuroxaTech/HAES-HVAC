"""
HAES HVAC - Chat API Endpoints

Website chat integration endpoints.
"""

import hashlib
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
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    """Request schema for chat messages."""
    request_id: str = Field(default_factory=generate_request_id)
    session_id: str
    user_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    """Response schema for chat messages."""
    reply_text: str
    action: str  # completed, needs_human, unsupported, error
    data: dict[str, Any] = Field(default_factory=dict)
    session_id: str


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """
    Process a chat message and return a response.

    This endpoint is called by the website chat widget.
    It runs the same HAEL pipeline as voice but returns
    a text-formatted response.
    """
    logger.info(f"Chat message: session_id={request.session_id}")

    try:
        # Extract intent and entities
        extractor = RuleBasedExtractor()
        extraction = extractor.extract(request.user_text)

        # Route to brain
        routing = route_command(extraction)

        # Build command
        command = build_hael_command(
            request_id=request.request_id,
            channel=Channel.CHAT,
            raw_text=request.user_text,
            extraction=extraction,
            routing=routing,
            metadata={
                "session_id": request.session_id,
                **request.metadata,
            },
        )

        # Route to brain handler
        if routing.brain == Brain.OPS:
            result = await handle_ops_command(command)
            reply = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        elif routing.brain == Brain.CORE:
            result = handle_core_command(command)
            reply = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        elif routing.brain == Brain.REVENUE:
            result = handle_revenue_command(command)
            reply = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        elif routing.brain == Brain.PEOPLE:
            result = handle_people_command(command)
            reply = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data

        else:
            # Unknown brain - needs human
            result = None
            reply = (
                "I'm not sure how to help with that request. "
                "Would you like me to connect you with a representative?"
            )
            action = "needs_human"
            data = {
                "reason": "unknown_intent",
            }

        # Add missing fields info for chat
        if action == "needs_human" and result is not None and hasattr(result, "missing_fields"):
            if result.missing_fields:
                reply += f"\n\nTo proceed, I'll need: {', '.join(result.missing_fields)}"
                data["missing_fields"] = result.missing_fields

        return ChatMessageResponse(
            reply_text=reply,
            action=action,
            data=data,
            session_id=request.session_id,
        )

    except Exception as e:
        logger.exception(f"Error processing chat message: {e}")
        return ChatMessageResponse(
            reply_text="I'm sorry, something went wrong. Please try again or contact us directly.",
            action="error",
            data={"error": str(e)},
            session_id=request.session_id,
        )

