"""
HAES HVAC - Vapi Webhooks

Webhook handlers for Vapi call lifecycle events.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class VapiWebhookPayload(BaseModel):
    """Vapi webhook payload schema."""
    call_id: str | None = None
    event_type: str | None = None
    timestamp: datetime | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class VapiWebhookResponse(BaseModel):
    """Response for Vapi webhooks."""
    status: str = "ok"


@router.post("/vapi", response_model=VapiWebhookResponse)
async def vapi_webhook(request: Request) -> VapiWebhookResponse:
    """
    Handle Vapi call lifecycle webhooks.

    Events:
    - call_started: New call initiated
    - call_ended: Call completed
    - transcript: Transcript update
    - tool_called: Tool was invoked
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Extract event info
    call_id = body.get("call_id") or body.get("callId")
    event_type = body.get("event_type") or body.get("type") or "unknown"
    timestamp = datetime.utcnow()

    logger.info(f"Vapi webhook: event={event_type}, call_id={call_id}")

    # Log different event types
    if event_type in ["call_started", "call-started"]:
        logger.info(f"Call started: {call_id}")
        # Could store call start in audit_log

    elif event_type in ["call_ended", "call-ended"]:
        logger.info(f"Call ended: {call_id}")
        # Could store call end and transcript summary

    elif event_type in ["transcript", "transcript_update"]:
        transcript = body.get("transcript", "")
        logger.debug(f"Transcript update for {call_id}: {transcript[:100]}...")

    elif event_type in ["tool_called", "tool-called"]:
        tool_name = body.get("tool", {}).get("name", "unknown")
        logger.info(f"Tool called: {tool_name} for call {call_id}")

    # Note: Webhook verification would be done here if VAPI_WEBHOOK_SECRET is configured
    # For now, we just log and acknowledge

    return VapiWebhookResponse(status="ok")


@router.get("/vapi/health")
async def webhook_health() -> dict:
    """Health check for webhook endpoint."""
    return {
        "status": "ok",
        "endpoint": "/webhooks/vapi",
        "ready": True,
    }

