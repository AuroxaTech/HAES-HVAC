"""
HAES HVAC - Vapi Webhooks

Webhook handlers for Vapi call lifecycle events.
Writes to audit_log for KPI tracking.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from src.utils.request_id import generate_request_id
from src.utils.audit import log_vapi_webhook
from src.db.session import get_session_factory

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

    # Log different event types and write to audit_log
    audit_event_type = None
    summary = None
    duration_seconds = None
    ended_reason = None
    
    if event_type in ["call_started", "call-started"]:
        logger.info(f"Call started: {call_id}")
        audit_event_type = "call_started"

    elif event_type in ["call_ended", "call-ended"]:
        logger.info(f"Call ended: {call_id}")
        audit_event_type = "call_ended"
        summary = body.get("summary", "")
        duration_seconds = body.get("durationSeconds")
        ended_reason = body.get("endedReason", "")

    elif event_type in ["transcript", "transcript_update"]:
        transcript = body.get("transcript", "")
        logger.debug(f"Transcript update for {call_id}: {transcript[:100]}...")
        # Don't audit every transcript update - too noisy

    elif event_type in ["tool_called", "tool-called"]:
        tool_name = body.get("tool", {}).get("name", "unknown")
        logger.info(f"Tool called: {tool_name} for call {call_id}")
        # Tool calls are audited in vapi_server.py, not here

    # Write to audit_log for trackable events
    if audit_event_type and call_id:
        try:
            session_factory = get_session_factory()
            session = session_factory()
            try:
                log_vapi_webhook(
                    session=session,
                    call_id=call_id,
                    event_type=audit_event_type,
                    event_data=body,
                    summary=summary,
                    duration_seconds=duration_seconds,
                    ended_reason=ended_reason,
                )
            finally:
                session.close()
        except Exception as audit_err:
            logger.warning(f"Failed to audit webhook event: {audit_err}")

    return VapiWebhookResponse(status="ok")


@router.get("/vapi/health")
async def webhook_health() -> dict:
    """Health check for webhook endpoint."""
    return {
        "status": "ok",
        "endpoint": "/webhooks/vapi",
        "ready": True,
    }

