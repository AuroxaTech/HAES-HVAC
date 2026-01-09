"""
HAES HVAC - Vapi Server URL Endpoint

Implements the Vapi Server URL contract for tool-calls and transfer-destination-request.
This is the production integration point for Vapi voice calls.

Server URL message types handled:
- tool-calls: Execute hael_route tool and return results
- transfer-destination-request: Return transfer destination based on business hours
- end-of-call-report: Log call summary to audit log
- status-update: Log status changes
"""

import json
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, HTTPException
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
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vapi", tags=["vapi-server"])

# Business hours configuration
BUSINESS_TZ = ZoneInfo("America/Chicago")
BUSINESS_HOURS_START = 8  # 8 AM
BUSINESS_HOURS_END = 17   # 5 PM (17:00)
TRANSFER_NUMBER = "+19723724458"


# ============================================================================
# Request/Response Models
# ============================================================================

class VapiServerRequest(BaseModel):
    """Generic Vapi Server URL request wrapper."""
    message: dict[str, Any]


class ToolCallResult(BaseModel):
    """Single tool call result."""
    toolCallId: str
    result: str  # JSON-stringified result


class VapiToolCallsResponse(BaseModel):
    """Response for tool-calls message type."""
    results: list[ToolCallResult]


class TransferDestinationNumber(BaseModel):
    """Phone number transfer destination."""
    type: str = "number"
    number: str
    message: str = ""


class VapiTransferResponse(BaseModel):
    """Response for transfer-destination-request message type."""
    destination: TransferDestinationNumber | None = None
    message: dict[str, Any] | None = None
    error: str | None = None


# ============================================================================
# Business Hours Logic
# ============================================================================

def is_business_hours() -> bool:
    """
    Check if current time is within business hours.
    
    Business hours: 8 AM - 5 PM America/Chicago, Monday-Friday.
    Returns False on weekends.
    """
    now = datetime.now(BUSINESS_TZ)
    
    # Check weekday (0=Monday, 6=Sunday)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check time
    return BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END


def get_transfer_destination() -> VapiTransferResponse:
    """
    Get transfer destination based on business hours.
    
    During business hours: Return phone number for transfer.
    After hours: Return error with callback message.
    """
    if is_business_hours():
        return VapiTransferResponse(
            destination=TransferDestinationNumber(
                type="number",
                number=TRANSFER_NUMBER,
                message="Please hold while I connect you with one of our team members."
            )
        )
    else:
        return VapiTransferResponse(
            error="after_hours",
            message={
                "type": "request-complete",
                "content": (
                    "Our office is currently closed. Our business hours are 8 AM to 5 PM "
                    "Central Time, Monday through Friday. I can collect your information "
                    "and have someone call you back first thing in the morning. "
                    "May I have your name and callback number?"
                )
            }
        )


# ============================================================================
# Tool Execution
# ============================================================================

def execute_hael_route(
    user_text: str,
    conversation_context: str | None,
    tool_call_id: str,
    call_id: str | None,
) -> dict[str, Any]:
    """
    Execute the hael_route tool through the HAES pipeline.
    
    Returns a dict with speak, action, and data.
    """
    request_id = generate_request_id()
    
    try:
        # Extract intent and entities
        extractor = RuleBasedExtractor()
        extraction = extractor.extract(user_text)
        
        # Route to brain
        routing = route_command(extraction)
        
        # Build command
        command = build_hael_command(
            request_id=request_id,
            channel=Channel.VOICE,
            raw_text=user_text,
            extraction=extraction,
            routing=routing,
            metadata={
                "call_id": call_id,
                "tool_call_id": tool_call_id,
                "conversation_context": conversation_context,
            },
        )
        
        # Route to brain handler
        result = None
        if routing.brain == Brain.OPS:
            result = handle_ops_command(command)
        elif routing.brain == Brain.CORE:
            result = handle_core_command(command)
        elif routing.brain == Brain.REVENUE:
            result = handle_revenue_command(command)
        elif routing.brain == Brain.PEOPLE:
            result = handle_people_command(command)
        
        if result is not None:
            speak = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data
            
            # Add missing fields if needs human
            if action == "needs_human" and hasattr(result, "missing_fields") and result.missing_fields:
                speak += f" I'll need the following information: {', '.join(result.missing_fields)}."
                data["missing_fields"] = result.missing_fields
        else:
            # Unknown brain - needs human
            speak = (
                "I'm not sure how to help with that specific request. "
                "Let me connect you with a representative who can assist."
            )
            action = "needs_human"
            data = {
                "reason": "unknown_intent",
                "raw_text": user_text,
            }
        
        return {
            "speak": speak,
            "action": action,
            "data": data,
            "request_id": request_id,
        }
        
    except Exception as e:
        logger.exception(f"Error executing hael_route: {e}")
        return {
            "speak": "I'm sorry, I encountered an error. Let me connect you with a representative.",
            "action": "error",
            "data": {"error": str(e)},
            "request_id": request_id,
        }


# ============================================================================
# Main Server URL Endpoint
# ============================================================================

@router.post("/server")
async def vapi_server_url(request: Request) -> dict[str, Any]:
    """
    Vapi Server URL endpoint.
    
    Handles all Vapi server messages:
    - tool-calls: Execute tools and return results
    - transfer-destination-request: Return transfer destination
    - end-of-call-report: Log call summary
    - status-update: Log status changes
    
    Signature verification is handled by WebhookVerificationMiddleware.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    message = body.get("message", {})
    message_type = message.get("type", "unknown")
    call_obj = message.get("call", {})
    call_id = call_obj.get("id")
    
    logger.info(f"Vapi server message: type={message_type}, call_id={call_id}")
    
    # -------------------------------------------------------------------------
    # Handle tool-calls
    # -------------------------------------------------------------------------
    if message_type == "tool-calls":
        tool_call_list = message.get("toolCallList", [])
        tool_with_list = message.get("toolWithToolCallList", [])
        
        # Prefer toolWithToolCallList if available
        if tool_with_list:
            results = []
            for item in tool_with_list:
                tool_name = item.get("name", "")
                tool_call = item.get("toolCall", {})
                tool_call_id = tool_call.get("id", "")
                parameters = tool_call.get("parameters", {})
                
                if tool_name == "hael_route":
                    user_text = parameters.get("user_text", "")
                    conversation_context = parameters.get("conversation_context")
                    
                    result = execute_hael_route(
                        user_text=user_text,
                        conversation_context=conversation_context,
                        tool_call_id=tool_call_id,
                        call_id=call_id,
                    )
                    
                    results.append(ToolCallResult(
                        toolCallId=tool_call_id,
                        result=json.dumps(result),
                    ))
                else:
                    # Unknown tool
                    results.append(ToolCallResult(
                        toolCallId=tool_call_id,
                        result=json.dumps({
                            "speak": "I don't recognize that action. Let me help you another way.",
                            "action": "error",
                            "data": {"error": f"Unknown tool: {tool_name}"},
                        }),
                    ))
            
            return {"results": [r.model_dump() for r in results]}
        
        # Fallback to toolCallList
        elif tool_call_list:
            results = []
            for tool_call in tool_call_list:
                tool_call_id = tool_call.get("id", "")
                tool_name = tool_call.get("name", "")
                parameters = tool_call.get("parameters", {})
                
                if tool_name == "hael_route":
                    user_text = parameters.get("user_text", "")
                    conversation_context = parameters.get("conversation_context")
                    
                    result = execute_hael_route(
                        user_text=user_text,
                        conversation_context=conversation_context,
                        tool_call_id=tool_call_id,
                        call_id=call_id,
                    )
                    
                    results.append(ToolCallResult(
                        toolCallId=tool_call_id,
                        result=json.dumps(result),
                    ))
                else:
                    results.append(ToolCallResult(
                        toolCallId=tool_call_id,
                        result=json.dumps({
                            "speak": "I don't recognize that action.",
                            "action": "error",
                            "data": {"error": f"Unknown tool: {tool_name}"},
                        }),
                    ))
            
            return {"results": [r.model_dump() for r in results]}
        
        # No tool calls found
        return {"results": []}
    
    # -------------------------------------------------------------------------
    # Handle transfer-destination-request
    # -------------------------------------------------------------------------
    elif message_type in ["transfer-destination-request", "handoff-destination-request"]:
        response = get_transfer_destination()
        
        if response.destination:
            return {
                "destination": response.destination.model_dump(),
            }
        else:
            return {
                "error": response.error,
                "message": response.message,
            }
    
    # -------------------------------------------------------------------------
    # Handle end-of-call-report
    # -------------------------------------------------------------------------
    elif message_type == "end-of-call-report":
        # Log call summary for analytics
        summary = message.get("summary", "")
        duration = message.get("durationSeconds", 0)
        ended_reason = message.get("endedReason", "")
        
        logger.info(
            f"Call ended: call_id={call_id}, duration={duration}s, "
            f"reason={ended_reason}, summary={summary[:100]}..."
        )
        
        # TODO: Store in audit_log for KPI reporting
        
        return {"status": "ok"}
    
    # -------------------------------------------------------------------------
    # Handle status-update
    # -------------------------------------------------------------------------
    elif message_type == "status-update":
        status = message.get("status", "")
        logger.info(f"Call status update: call_id={call_id}, status={status}")
        return {"status": "ok"}
    
    # -------------------------------------------------------------------------
    # Handle transcript updates
    # -------------------------------------------------------------------------
    elif message_type == "transcript":
        # Just acknowledge - don't need to process
        return {"status": "ok"}
    
    # -------------------------------------------------------------------------
    # Handle conversation-update
    # -------------------------------------------------------------------------
    elif message_type == "conversation-update":
        # Just acknowledge
        return {"status": "ok"}
    
    # -------------------------------------------------------------------------
    # Unknown message type
    # -------------------------------------------------------------------------
    else:
        logger.warning(f"Unknown Vapi message type: {message_type}")
        return {"status": "ok"}


@router.get("/server/health")
async def vapi_server_health() -> dict[str, Any]:
    """Health check for Vapi Server URL endpoint."""
    return {
        "status": "ok",
        "endpoint": "/vapi/server",
        "business_hours": is_business_hours(),
        "transfer_number": TRANSFER_NUMBER,
        "timezone": str(BUSINESS_TZ),
    }
