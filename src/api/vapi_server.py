"""
HAES HVAC - Vapi Server URL Endpoint

Implements the Vapi Server URL contract for tool-calls and transfer-destination-request.
This is the production integration point for Vapi voice calls.

Server URL message types handled:
- tool-calls: Execute hael_route tool and return results
- transfer-destination-request: Return transfer destination based on business hours
- end-of-call-report: Log call summary to audit log
- status-update: Log status changes

Key behavior:
- Service requests create/update a CRM lead in Odoo
- One lead per call_id (idempotent)
- Fail-closed: if Odoo fails, still respond but flag for human follow-up
"""

import json
import logging
import re
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
from src.hael.schema import Intent, UrgencyLevel
from src.brains.ops import handle_ops_command
from src.brains.core import handle_core_command
from src.brains.core.handlers import calculate_service_pricing
from src.brains.revenue import handle_revenue_command
from src.brains.people import handle_people_command
from src.utils.request_id import generate_request_id
from src.utils.idempotency import IdempotencyChecker, generate_key_hash
from src.utils.audit import log_vapi_tool_call, log_vapi_webhook
from src.db.session import get_session_factory
from src.config.settings import get_settings

# Import tool registration to ensure tools are registered
import src.vapi.tools.register_tools  # noqa: F401

# Idempotency scope for Vapi tool calls
VAPI_TOOL_SCOPE = "vapi_tool"

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


def is_after_hours_or_weekend() -> tuple[bool, bool]:
    """
    Check if current time is after business hours or on a weekend.
    
    Returns:
        Tuple of (is_after_hours, is_weekend)
    """
    now = datetime.now(BUSINESS_TZ)
    
    is_weekend = now.weekday() >= 5  # Saturday or Sunday
    
    # After hours: before 8 AM or 6 PM or later (we use 6 PM for after-hours premium)
    is_after_hours = now.hour < BUSINESS_HOURS_START or now.hour >= 18  # 6 PM
    
    return is_after_hours, is_weekend


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

# Urgency string to UrgencyLevel mapping
URGENCY_MAP = {
    "emergency": UrgencyLevel.EMERGENCY,
    "today": UrgencyLevel.HIGH,
    "this_week": UrgencyLevel.MEDIUM,
    "flexible": UrgencyLevel.LOW,
}

# Request type to Intent mapping
REQUEST_TYPE_INTENT_MAP = {
    "service_request": Intent.SERVICE_REQUEST,
    "quote_request": Intent.QUOTE_REQUEST,
    "schedule_appointment": Intent.SCHEDULE_APPOINTMENT,
    "reschedule_appointment": Intent.RESCHEDULE_APPOINTMENT,
    "cancel_appointment": Intent.CANCEL_APPOINTMENT,
    "status_check": Intent.STATUS_UPDATE_REQUEST,
    "billing_inquiry": Intent.BILLING_INQUIRY,
    "general_inquiry": Intent.UNKNOWN,
}

# Intents that should create/update a CRM lead in Odoo
LEAD_CREATING_INTENTS = {
    Intent.SERVICE_REQUEST,
    Intent.QUOTE_REQUEST,
    Intent.SCHEDULE_APPOINTMENT,
}


async def execute_hael_route(
    parameters: dict[str, Any],
    tool_call_id: str,
    call_id: str | None,
) -> dict[str, Any]:
    """
    Execute the hael_route tool through the HAES pipeline.
    
    Accepts structured parameters from Vapi:
    - request_type: service_request, quote_request, etc.
    - customer_name: Customer's full name
    - phone: Phone number
    - email: Email (optional)
    - address: Full service address
    - issue_description: Problem description
    - urgency: emergency, today, this_week, flexible
    - property_type: residential, commercial
    
    Key behavior:
    - For service/quote/schedule requests: creates/updates CRM lead in Odoo
    - Returns crm_lead_id in data on success
    - Fail-closed: if Odoo fails, returns needs_human with captured info
    
    Returns a dict with speak, action, data, and request_id.
    """
    request_id = generate_request_id()
    odoo_result = None
    
    try:
        # Extract structured parameters
        request_type = parameters.get("request_type", "service_request")
        customer_name = parameters.get("customer_name", "")
        phone = parameters.get("phone", "")
        email = parameters.get("email", "")
        address = parameters.get("address", "")
        issue_description = parameters.get("issue_description", "")
        urgency = parameters.get("urgency", "flexible")
        property_type = parameters.get("property_type", "residential")
        system_type = parameters.get("system_type", "")
        indoor_temperature_f = parameters.get("indoor_temperature_f")
        # Quote-specific fields
        square_footage = parameters.get("square_footage")
        system_age_years = parameters.get("system_age_years")
        budget_range = parameters.get("budget_range")
        timeline = parameters.get("timeline")
        
        # Also support legacy user_text/conversation_context format
        user_text = parameters.get("user_text", "")
        conversation_context = parameters.get("conversation_context", "")
        
        logger.info(f"hael_route params: type={request_type}, name={customer_name}, phone={phone}, address={address}, system={system_type}, indoor_temp={indoor_temperature_f}")
        
        # Build a rich text representation for the extractor
        text_parts = []
        
        if issue_description:
            text_parts.append(issue_description)
        if user_text:
            text_parts.append(user_text)
        if customer_name:
            text_parts.append(f"Customer: {customer_name}")
        if phone:
            text_parts.append(f"Phone: {phone}")
        if email:
            text_parts.append(f"Email: {email}")
        if address:
            text_parts.append(f"Address: {address}")
        if urgency:
            text_parts.append(f"Urgency: {urgency}")
        if property_type:
            text_parts.append(f"Property: {property_type}")
        if square_footage:
            text_parts.append(f"Square footage: {square_footage} square feet")
        if system_age_years:
            text_parts.append(f"System age: {system_age_years} years old")
        if budget_range:
            text_parts.append(f"Budget: {budget_range}")
        if timeline:
            text_parts.append(f"Timeline: {timeline}")
        if conversation_context:
            text_parts.append(f"Context: {conversation_context}")
        
        full_text = ". ".join(text_parts) if text_parts else "general inquiry"
        
        # Extract intent and entities
        extractor = RuleBasedExtractor()
        extraction = extractor.extract(full_text)
        
        # Override entities with structured data (more reliable than extraction)
        if customer_name:
            extraction.entities.full_name = customer_name
        if phone:
            # Normalize phone format
            clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
            extraction.entities.phone = clean_phone
        if email:
            extraction.entities.email = email
        if address:
            extraction.entities.address = address
            # Try to extract ZIP and city from address
            zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', address)
            if zip_match:
                extraction.entities.zip_code = zip_match.group(1)
            # Try to extract city (simple heuristic: word before state abbreviation or ZIP)
            city_match = re.search(r',\s*([A-Za-z\s]+),?\s*[A-Z]{2}', address)
            if city_match:
                extraction.entities.city = city_match.group(1).strip()
        if issue_description:
            extraction.entities.problem_description = issue_description
        if property_type:
            extraction.entities.property_type = property_type
        if system_type:
            extraction.entities.system_type = system_type
        if indoor_temperature_f is not None:
            # Ensure it's an integer
            try:
                extraction.entities.temperature_mentioned = int(indoor_temperature_f)
            except (ValueError, TypeError):
                pass
        # Quote-specific fields
        if square_footage is not None:
            try:
                extraction.entities.square_footage = int(square_footage)
            except (ValueError, TypeError):
                pass
        if system_age_years is not None:
            try:
                extraction.entities.system_age_years = int(system_age_years)
            except (ValueError, TypeError):
                pass
        if budget_range:
            extraction.entities.budget_range = budget_range
        if timeline:
            extraction.entities.timeline = timeline
        
        # Map urgency to UrgencyLevel
        extraction.entities.urgency_level = URGENCY_MAP.get(urgency, UrgencyLevel.MEDIUM)
        
        # Map request_type to Intent if not already determined
        if request_type in REQUEST_TYPE_INTENT_MAP:
            extraction.intent = REQUEST_TYPE_INTENT_MAP[request_type]
            # When intent is explicitly provided via request_type, set high confidence
            extraction.confidence = 0.9
        
        # Route to brain
        routing = route_command(extraction)
        
        # Build command
        command = build_hael_command(
            request_id=request_id,
            channel=Channel.VOICE,
            raw_text=full_text,
            extraction=extraction,
            routing=routing,
            metadata={
                "call_id": call_id,
                "tool_call_id": tool_call_id,
                "structured_params": parameters,
            },
        )
        
        # Route to brain handler
        result = None
        if routing.brain == Brain.OPS:
            result = await handle_ops_command(command)
        elif routing.brain == Brain.CORE:
            result = handle_core_command(command)
        elif routing.brain == Brain.REVENUE:
            result = handle_revenue_command(command)
        elif routing.brain == Brain.PEOPLE:
            result = handle_people_command(command)
        
        # Determine response from brain result
        if result is not None:
            speak = result.message
            action = "completed" if result.status.value == "success" else "needs_human"
            data = result.data.copy() if result.data else {}
            
            # Add missing fields if needs human
            if action == "needs_human" and hasattr(result, "missing_fields") and result.missing_fields:
                speak += f" I'll need the following information: {', '.join(result.missing_fields)}."
                data["missing_fields"] = result.missing_fields
            
            is_emergency = data.get("is_emergency", False)
            emergency_reason = data.get("emergency_reason")
            
            # ---------------------------------------------------------------------
            # Compute pricing for service requests (especially emergencies)
            # ---------------------------------------------------------------------
            if extraction.intent == Intent.SERVICE_REQUEST and action == "completed":
                is_after_hours, is_weekend = is_after_hours_or_weekend()
                
                pricing = calculate_service_pricing(
                    tier=None,  # Default to Retail
                    is_emergency=is_emergency,
                    is_after_hours=is_after_hours,
                    is_weekend=is_weekend,
                )
                
                # Add pricing to response data
                data["pricing"] = {
                    "tier": pricing.tier.value,
                    "diagnostic_fee": pricing.diagnostic_fee,
                    "emergency_premium": pricing.emergency_premium,
                    "after_hours_premium": pricing.after_hours_premium,
                    "weekend_premium": pricing.weekend_premium,
                    "total_base_fee": pricing.total_base_fee,
                    "notes": pricing.notes,
                }
                
                # Add ETA + pricing info to speak for emergencies
                if is_emergency:
                    eta_min = data.get("eta_window_hours_min", 1.5)
                    eta_max = data.get("eta_window_hours_max", 3.0)
                    tech_name = None
                    if data.get("assigned_technician"):
                        tech_name = data["assigned_technician"].get("name")
                    
                    # Build enhanced speak message
                    speak_parts = [speak]
                    
                    # Add tech assignment
                    if tech_name:
                        speak_parts.append(f"Technician {tech_name} has been assigned.")
                    
                    # Add ETA
                    speak_parts.append(f"We can have a technician there within {eta_min} to {eta_max} hours.")
                    
                    # Add pricing disclaimer
                    speak_parts.append(
                        f"The base diagnostic fee for today will be ${pricing.total_base_fee:.2f}, "
                        f"which includes any applicable premiums. Final repair costs will depend on the issue."
                    )
                    
                    speak = " ".join(speak_parts)
            
            # ---------------------------------------------------------------------
            # Handle appointment scheduling/rescheduling/cancellation results
            # ---------------------------------------------------------------------
            if extraction.intent in (Intent.SCHEDULE_APPOINTMENT, Intent.RESCHEDULE_APPOINTMENT, Intent.CANCEL_APPOINTMENT) and action == "completed":
                # Appointment operations already include appointment details in data
                appointment_id = data.get("appointment_id")
                scheduled_time = data.get("scheduled_time")
                technician_name = None
                if data.get("assigned_technician"):
                    technician_name = data["assigned_technician"].get("name")
                
                # Include appointment info in response
                if appointment_id:
                    data["appointment"] = {
                        "id": appointment_id,
                        "scheduled_time": scheduled_time,
                        "scheduled_time_end": data.get("scheduled_time_end"),
                        "technician_name": technician_name,
                    }
                
                # If appointment was created/rescheduled, try to link to lead if one exists
                if appointment_id and extraction.intent in (Intent.SCHEDULE_APPOINTMENT, Intent.RESCHEDULE_APPOINTMENT):
                    # Check if we'll create a lead below
                    # Link will be handled after lead creation
                    pass
        else:
            # Unknown brain - needs human
            speak = (
                "I'm not sure how to help with that specific request. "
                "Let me connect you with a representative who can assist."
            )
            action = "needs_human"
            data = {"reason": "unknown_intent"}
            is_emergency = False
            emergency_reason = None
        
        # ---------------------------------------------------------------------
        # Create/Update CRM Lead in Odoo (for lead-creating intents)
        # ---------------------------------------------------------------------
        # Use call_id if available, otherwise fall back to tool_call_id
        lead_ref_id = call_id or tool_call_id
        
        if lead_ref_id and extraction.intent in LEAD_CREATING_INTENTS:
            try:
                from src.integrations.odoo_leads import upsert_lead_for_call
                
                logger.info(f"Creating Odoo lead for ref={lead_ref_id}, intent={extraction.intent}")
                
                # Merge original params with enriched data (tech assignment, pricing, ETA)
                enriched_params = parameters.copy()
                if data.get("assigned_technician"):
                    enriched_params["assigned_technician"] = data["assigned_technician"]
                if data.get("pricing"):
                    enriched_params["pricing"] = data["pricing"]
                if data.get("eta_window_hours_min"):
                    enriched_params["eta_window_hours_min"] = data["eta_window_hours_min"]
                    enriched_params["eta_window_hours_max"] = data.get("eta_window_hours_max")
                
                odoo_result = await upsert_lead_for_call(
                    call_id=lead_ref_id,  # Use call_id or tool_call_id as reference
                    entities=extraction.entities,
                    urgency=extraction.entities.urgency_level,
                    is_emergency=is_emergency,
                    emergency_reason=emergency_reason,
                    raw_text=full_text,
                    structured_params=enriched_params,
                    request_id=request_id,
                )
                
                if odoo_result.get("status") == "success":
                    lead_id = odoo_result.get("lead_id")
                    data["odoo"] = {
                        "crm_lead_id": lead_id,
                        "action": odoo_result.get("action"),  # created or updated
                        "partner_id": odoo_result.get("partner_id"),
                    }
                    logger.info(f"Odoo lead {odoo_result.get('action')}: {lead_id} for ref {lead_ref_id}")
                    
                    # Link appointment to lead if appointment was created
                    if extraction.intent == Intent.SCHEDULE_APPOINTMENT and data.get("appointment_id"):
                        try:
                            from src.integrations.odoo_appointments import create_appointment_service
                            appointment_service = create_appointment_service()
                            await appointment_service.link_appointment_to_lead(
                                event_id=data["appointment_id"],
                                lead_id=lead_id,
                            )
                            logger.info(f"Linked appointment {data['appointment_id']} to lead {lead_id}")
                        except Exception as link_err:
                            logger.warning(f"Failed to link appointment to lead: {link_err}")
                else:
                    # Odoo failed - log but continue (fail-closed)
                    logger.error(f"Odoo lead creation failed: {odoo_result.get('error')}")
                    data["odoo"] = {
                        "crm_lead_id": None,
                        "action": "failed",
                        "error": odoo_result.get("error", "Unknown error"),
                    }
                    # If action was "completed", downgrade to needs_human for follow-up
                    if action == "completed":
                        action = "needs_human"
                        speak = (
                            "I've captured your request. Our team will follow up shortly "
                            "to confirm the details and schedule your service."
                        )
                        
            except Exception as odoo_err:
                logger.exception(f"Odoo lead upsert error: {odoo_err}")
                data["odoo"] = {
                    "crm_lead_id": None,
                    "action": "error",
                    "error": str(odoo_err),
                }
                # Fail-closed: still respond but flag for human
                if action == "completed":
                    action = "needs_human"
                    speak = (
                        "I've captured your request. Our team will follow up shortly "
                        "to confirm the details."
                    )
        else:
            if not lead_ref_id:
                logger.warning("No call_id or tool_call_id available for lead creation")
            elif extraction.intent not in LEAD_CREATING_INTENTS:
                logger.debug(f"Intent {extraction.intent} not in lead-creating intents, skipping Odoo")
        
        # ---------------------------------------------------------------------
        # Send SMS confirmation to customer (for emergencies)
        # ---------------------------------------------------------------------
        if is_emergency and extraction.entities.phone and action == "completed":
            from src.integrations.twilio_sms import send_emergency_sms
            from src.utils.audit import log_event
            from src.config.settings import get_settings
            
            settings = get_settings()
            
            # Only send SMS if feature is enabled
            if settings.FEATURE_EMERGENCY_SMS:
                try:
                    tech_name = None
                    if data.get("assigned_technician"):
                        tech_name = data["assigned_technician"].get("name")
                    
                    eta_min = data.get("eta_window_hours_min", 1.5)
                    eta_max = data.get("eta_window_hours_max", 3.0)
                    total_fee = 0.0
                    if data.get("pricing"):
                        total_fee = data["pricing"].get("total_base_fee", 0)
                    
                    # Send SMS and await result to include in response
                    sms_result = await send_emergency_sms(
                        to_phone=extraction.entities.phone,
                        customer_name=extraction.entities.full_name,
                        tech_name=tech_name,
                        eta_hours_min=eta_min,
                        eta_hours_max=eta_max,
                        total_fee=total_fee,
                    )
                    
                    logger.info(f"Emergency SMS result: {sms_result}")
                    data["sms"] = sms_result
                    
                    # Log to audit
                    try:
                        log_event(
                            request_id=request_id,
                            channel="sms",
                            intent="emergency_confirmation",
                            brain="ops",
                            command_json={"to": extraction.entities.phone},
                            odoo_result_json=sms_result,
                            status=sms_result.get("status", "unknown"),
                        )
                    except Exception as audit_err:
                        logger.warning(f"Failed to log SMS audit: {audit_err}")
                except Exception as sms_err:
                    logger.error(f"Emergency SMS error: {sms_err}")
                    data["sms"] = {"status": "error", "error": str(sms_err)}
            else:
                logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping SMS")
                data["sms"] = {"status": "disabled", "reason": "feature_flag_disabled"}
        
        # ---------------------------------------------------------------------
        # Send email notifications to Dispatch, Linda, and assigned technician
        # ---------------------------------------------------------------------
        if is_emergency and action == "completed" and data.get("odoo", {}).get("crm_lead_id"):
            from src.integrations.email_notifications import send_emergency_staff_notification
            from src.utils.audit import log_event
            
            try:
                lead_id = data["odoo"].get("crm_lead_id")
                tech_id = None
                tech_name = None
                if data.get("assigned_technician"):
                    tech_id = data["assigned_technician"].get("id")
                    tech_name = data["assigned_technician"].get("name")
                
                # Send staff notifications (await so errors are caught)
                staff_email_result = await send_emergency_staff_notification(
                    lead_id=lead_id,
                    customer_name=extraction.entities.full_name,
                    address=extraction.entities.address,
                    phone=extraction.entities.phone,
                    tech_id=tech_id,
                    tech_name=tech_name,
                    eta_hours_min=data.get("eta_window_hours_min", 1.5),
                    eta_hours_max=data.get("eta_window_hours_max", 3.0),
                    total_fee=data.get("pricing", {}).get("total_base_fee", 0),
                    emergency_reason=emergency_reason,
                )
                
                logger.info(f"Emergency staff email notifications result: {staff_email_result}")
                data["staff_notifications"] = staff_email_result
                
                # Log to audit
                try:
                    log_event(
                        request_id=request_id,
                        channel="email",
                        intent="emergency_staff_notification",
                        brain="ops",
                        command_json={"lead_id": lead_id},
                        odoo_result_json=staff_email_result,
                        status=staff_email_result.get("status", "unknown"),
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to log email audit: {audit_err}")
            except Exception as email_err:
                logger.error(f"Emergency staff email error: {email_err}")
                data["staff_notifications"] = {"status": "error", "error": str(email_err)}
        
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
    
    # Extract call_id from multiple possible locations
    # Vapi sometimes puts it in message.call.id, sometimes in message.callId
    call_obj = message.get("call", {})
    call_id = (
        call_obj.get("id") or
        message.get("callId") or
        message.get("call_id") or
        body.get("callId") or
        body.get("call_id") or
        body.get("call", {}).get("id")
    )
    
    logger.info(f"Vapi server message: type={message_type}, call_id={call_id}")
    
    # -------------------------------------------------------------------------
    # Handle tool-calls
    # -------------------------------------------------------------------------
    if message_type == "tool-calls":
        tool_call_list = message.get("toolCallList", [])
        tool_with_list = message.get("toolWithToolCallList", [])
        
        # Debug: log the raw structure
        logger.info(f"tool-calls payload: toolCallList={json.dumps(tool_call_list)[:500]}, toolWithToolCallList={json.dumps(tool_with_list)[:500]}")
        
        # Helper to extract tool name and parameters from various Vapi formats
        def extract_tool_info(item: dict) -> tuple[str, str, dict]:
            """Extract (tool_name, tool_call_id, parameters) from various Vapi formats."""
            tool_name = ""
            tool_call_id = ""
            parameters = {}
            
            # Format 1: toolWithToolCallList - {"name": "...", "toolCall": {"id": "...", "parameters": {...}}}
            tool_call = item.get("toolCall", {})
            if tool_call:
                tool_name = item.get("name", "")
                tool_call_id = tool_call.get("id", "")
                parameters = tool_call.get("parameters", {}) or tool_call.get("arguments", {})
                # Also check function nested in toolCall
                func = tool_call.get("function", {})
                if func:
                    tool_name = tool_name or func.get("name", "")
                    parameters = parameters or func.get("parameters", {}) or func.get("arguments", {})
            
            # Format 2: toolCallList - {"id": "...", "function": {"name": "...", "arguments": {...}}}
            func = item.get("function", {})
            if func:
                tool_call_id = tool_call_id or item.get("id", "")
                tool_name = tool_name or func.get("name", "")
                parameters = parameters or func.get("arguments", {}) or func.get("parameters", {})
            
            # Format 3: Simple - {"id": "...", "name": "...", "parameters": {...}}
            tool_call_id = tool_call_id or item.get("id", "")
            tool_name = tool_name or item.get("name", "")
            parameters = parameters or item.get("parameters", {}) or item.get("arguments", {})
            
            logger.info(f"Extracted tool info: name={tool_name}, id={tool_call_id}, params_keys={list(parameters.keys())}")
            return tool_name, tool_call_id, parameters
        
        # Helper to process a single tool call with idempotency + audit
        async def process_tool_call(
            tool_name: str,
            tool_call_id: str,
            parameters: dict,
        ) -> dict[str, Any]:
            """Process a tool call with idempotency checking and audit logging."""
            # Generate idempotency key
            idempotency_key = generate_key_hash(
                VAPI_TOOL_SCOPE,
                [call_id or "", tool_call_id]
            )
            
            # Get database session
            session_factory = get_session_factory()
            session = session_factory()
            
            try:
                # Check idempotency
                checker = IdempotencyChecker(session)
                existing = checker.get_existing(VAPI_TOOL_SCOPE, idempotency_key)
                
                if existing and existing.get("_idempotency_status") != "in_progress":
                    logger.info(f"Idempotency hit for {tool_call_id}, returning cached result")
                    return existing
                
                # Mark as in progress
                if not existing:
                    checker.start(VAPI_TOOL_SCOPE, idempotency_key)
                
                # Extract caller phone from Vapi message
                call_obj = message.get("call", {})
                caller_phone = (
                    call_obj.get("customer", {}).get("number") or
                    call_obj.get("from") or
                    call_obj.get("customerNumber") or
                    message.get("call", {}).get("customer", {}).get("number")
                )
                
                # Identify caller (Layer 1: Hybrid lookup)
                caller_identity = None
                if caller_phone:
                    try:
                        from src.utils.caller_identification import identify_caller
                        caller_identity = await identify_caller(caller_phone)
                        
                        logger.info(
                            f"Caller identified: phone={caller_phone[:5] if len(caller_phone) > 5 else caller_phone}***, "
                            f"role={caller_identity.role.value}, "
                            f"name={caller_identity.name or 'Unknown'}"
                        )
                    except Exception as ident_err:
                        logger.warning(f"Caller identification failed: {ident_err}")
                        # Continue with default customer role
                        from src.utils.caller_identification import CallerIdentity, CallerRole, get_permissions_for_role
                        caller_identity = CallerIdentity(
                            phone=caller_phone or "",
                            role=CallerRole.CUSTOMER,
                            is_active=True,
                            permissions=get_permissions_for_role(CallerRole.CUSTOMER),
                        )
                else:
                    # No phone number - default to customer
                    from src.utils.caller_identification import CallerIdentity, CallerRole, get_permissions_for_role
                    caller_identity = CallerIdentity(
                        phone="",
                        role=CallerRole.CUSTOMER,
                        is_active=True,
                        permissions=get_permissions_for_role(CallerRole.CUSTOMER),
                    )
                
                # Check access (Layer 3: Permission check)
                from src.vapi.tools.base import BaseToolHandler
                handler = BaseToolHandler(tool_name)
                allowed, error_msg = handler.check_access(
                    tool_name=tool_name,
                    caller_role=caller_identity.role.value,
                    caller_is_active=caller_identity.is_active,
                )
                
                if not allowed:
                    logger.warning(
                        f"Access denied: tool={tool_name}, "
                        f"caller_role={caller_identity.role.value}, "
                        f"caller_phone={caller_phone[:5] if caller_phone and len(caller_phone) > 5 else 'N/A'}***"
                    )
                    return {
                        "speak": error_msg or "I'm sorry, you don't have access to this feature.",
                        "action": "error",
                        "data": {
                            "error": "unauthorized",
                            "role": caller_identity.role.value,
                            "tool": tool_name
                        }
                    }
                
                # Add caller context to parameters (for tool handlers to use)
                parameters["_caller_role"] = caller_identity.role.value
                parameters["_caller_id"] = caller_identity.employee_id
                parameters["_caller_name"] = caller_identity.name
                parameters["_caller_phone"] = caller_identity.phone
                
                # Check for wrong number and profanity/abuse detection early
                from src.vapi.tools.base import BaseToolHandler
                base_handler = BaseToolHandler(tool_name)
                conversation_context = parameters.get("conversation_context") or parameters.get("user_text") or ""
                
                # Check for wrong number first
                if base_handler.detect_wrong_number(
                    conversation_context=conversation_context,
                    user_text=parameters.get("user_text"),
                ):
                    # Wrong number detected - respond gracefully, do NOT create lead
                    logger.info(f"Wrong number detected in call {call_id}")
                    
                    # Log as non-actionable
                    try:
                        log_vapi_webhook(
                            session=session,
                            call_id=call_id,
                            event_type="wrong_number",
                            summary="Wrong number/misdial detected",
                        )
                    except Exception:
                        pass
                    
                    return {
                        "speak": "No problem! Have a great day.",
                        "action": "completed",
                        "data": {
                            "wrong_number": True,
                            "non_actionable": True,
                        },
                    }
                
                # Check for profanity/abuse
                if base_handler.detect_profanity_abuse(
                    conversation_context=conversation_context,
                    user_text=parameters.get("user_text"),
                ):
                    # Profanity/abuse detected - respond professionally, offer escalation
                    logger.info(f"Profanity/abuse detected in call {call_id}")
                    
                    # Log for tracking
                    try:
                        log_vapi_webhook(
                            session=session,
                            call_id=call_id,
                            event_type="profanity_abuse",
                            summary="Profanity or abusive language detected",
                        )
                    except Exception:
                        pass
                    
                    return {
                        "speak": (
                            "I understand you're frustrated. Let me help resolve this. "
                            "Would you like me to connect you with a manager who can better assist you?"
                        ),
                        "action": "needs_human",
                        "data": {
                            "profanity_abuse_detected": True,
                            "escalation_offered": True,
                            "professional_response": True,
                        },
                    }
                
                # Check for unclear speech (low confidence)
                confidence = parameters.get("confidence") or parameters.get("speech_confidence")
                retry_count = parameters.get("unclear_retry_count", 0)
                if confidence is not None:
                    unclear_response = base_handler.handle_unclear_speech(
                        confidence=float(confidence),
                        retry_count=int(retry_count),
                    )
                    if unclear_response:
                        # Log unclear speech
                        try:
                            log_vapi_webhook(
                                session=session,
                                call_id=call_id,
                                event_type="unclear_speech",
                                summary=f"Unclear speech detected (confidence: {confidence})",
                            )
                        except Exception:
                            pass
                        
                        return {
                            "speak": unclear_response.speak,
                            "action": unclear_response.action,
                            "data": unclear_response.data,
                        }
                
                # Check for multiple intents (only if this is the first tool call in conversation)
                # Skip if we're already processing a prioritized request
                if not parameters.get("_prioritized_request"):
                    multiple_intents = base_handler.detect_multiple_intents(
                        conversation_context=conversation_context,
                        user_text=parameters.get("user_text"),
                    )
                    if multiple_intents:
                        logger.info(f"Multiple intents detected in call {call_id}: {multiple_intents}")
                        multi_response = base_handler.format_multi_request_response(multiple_intents)
                        return multi_response.to_dict()
                
                # Execute tool
                # Import tool registry and handler
                from src.vapi.tools import get_tool_handler
                from src.vapi.tools.base import handle_tool_call_with_base
                
                # Check if it's a direct tool (not hael_route)
                tool_handler = get_tool_handler(tool_name)
                
                if tool_handler:
                    # Direct tool call
                    result = await handle_tool_call_with_base(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        parameters=parameters,
                        call_id=call_id,
                        conversation_context=parameters.get("conversation_context"),
                    )
                elif tool_name == "hael_route":
                    # Legacy hael_route tool (backward compatibility)
                    result = await execute_hael_route(
                        parameters=parameters,
                        tool_call_id=tool_call_id,
                        call_id=call_id,
                    )
                else:
                    # Unknown tool
                    logger.warning(f"Unknown tool: {tool_name}")
                    result = {
                        "speak": f"I don't recognize the '{tool_name}' tool. Please try again.",
                        "action": "error",
                        "data": {"error": f"Unknown tool: {tool_name}"},
                        "request_id": None,
                    }
                
                # Ensure result is a dict (not ToolResponse or other type)
                if not isinstance(result, dict):
                    logger.warning(f"Tool {tool_name} returned non-dict result: {type(result)}")
                    if hasattr(result, "to_dict"):
                        result = result.to_dict()
                    else:
                        result = {
                            "speak": "I encountered an error processing your request.",
                            "action": "error",
                            "data": {"error": f"Invalid response type: {type(result)}"},
                        }
                
                # Validate result has required fields
                if "speak" not in result:
                    logger.error(f"Tool {tool_name} result missing 'speak' field: {result}")
                    result = {
                        "speak": "I encountered an error processing your request.",
                        "action": "error",
                        "data": {"error": "Missing 'speak' field in response"},
                    }
                
                # Write audit log
                try:
                    odoo_data = result.get("data", {}).get("odoo") if result.get("data") else None
                    log_vapi_tool_call(
                        session=session,
                        request_id=result.get("request_id"),
                        call_id=call_id,
                        tool_call_id=tool_call_id,
                        intent=parameters.get("request_type"),
                        brain=None,  # Could extract from result
                        parameters=parameters,
                        result=result,
                        odoo_result=odoo_data,
                        status="processed" if result.get("action") != "error" else "error",
                        error_message=result.get("data", {}).get("error") if result.get("action") == "error" else None,
                    )
                except Exception as audit_err:
                    logger.warning(f"Failed to write audit log: {audit_err}")
                
                # Complete idempotency
                checker.complete(VAPI_TOOL_SCOPE, idempotency_key, result)
                
                return result
                
            finally:
                session.close()
        
        # Prefer toolWithToolCallList if available
        if tool_with_list:
            results = []
            for item in tool_with_list:
                tool_name, tool_call_id, parameters = extract_tool_info(item)
                
                logger.info(f"Processing tool: name={tool_name}, id={tool_call_id}")
                
                result = await process_tool_call(tool_name, tool_call_id, parameters)
                
                results.append(ToolCallResult(
                    toolCallId=tool_call_id,
                    result=json.dumps(result),
                ))
            
            return {"results": [r.model_dump() for r in results]}
        
        # Fallback to toolCallList
        elif tool_call_list:
            results = []
            for tool_call in tool_call_list:
                tool_call_id = tool_call.get("id", "")
                tool_name = tool_call.get("name", "")
                # Vapi uses "arguments" not "parameters" in toolCallList
                parameters = tool_call.get("parameters", {}) or tool_call.get("arguments", {})
                
                logger.info(f"Processing tool (from toolCallList): name={tool_name}, id={tool_call_id}")
                
                result = await process_tool_call(tool_name, tool_call_id, parameters)
                
                results.append(ToolCallResult(
                    toolCallId=tool_call_id,
                    result=json.dumps(result),
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
        transcript = message.get("transcript", "")
        
        logger.info(
            f"Call ended: call_id={call_id}, duration={duration}s, "
            f"reason={ended_reason}, summary={summary[:100]}..."
        )
        
        # Store in audit_log for KPI reporting
        try:
            session_factory = get_session_factory()
            session = session_factory()
            try:
                log_vapi_webhook(
                    session=session,
                    call_id=call_id,
                    event_type="end-of-call-report",
                    summary=summary,
                    duration_seconds=duration,
                    ended_reason=ended_reason,
                )
            finally:
                session.close()
        except Exception as audit_err:
            logger.warning(f"Failed to audit end-of-call: {audit_err}")
        
        # Detect incomplete calls and send SMS fallback
        incomplete_reasons = [
            "hangup",
            "disconnected",
            "failed",
            "busy",
            "no-answer",
            "canceled",
        ]
        is_incomplete = (
            ended_reason.lower() in incomplete_reasons
            or duration < 30  # Very short calls (< 30 seconds)
            or (duration < 120 and not summary)  # Short calls with no summary
        )
        
        if is_incomplete:
            try:
                # Extract phone number from call data
                call_data = message.get("call", {})
                customer_phone = call_data.get("customer", {}).get("number") or call_data.get("from")
                
                if customer_phone:
                    # Extract partial data from transcript/summary
                    partial_data = {
                        "call_id": call_id,
                        "duration": duration,
                        "ended_reason": ended_reason,
                        "transcript": transcript[:500] if transcript else "",
                        "summary": summary[:500] if summary else "",
                    }
                    
                    # Try to extract customer name and other info from transcript
                    name_match = re.search(r'(?:name|i\'m|this is|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', transcript, re.IGNORECASE)
                    if name_match:
                        partial_data["customer_name"] = name_match.group(1)
                    
                    phone_match = re.search(r'(\+?1?\d{10,11})', transcript)
                    if phone_match and not customer_phone:
                        customer_phone = phone_match.group(1)
                    
                    address_match = re.search(r'(\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Place|Pl)[^,]*,\s*[A-Z][a-z]+\s+[A-Z]{2}\s+\d{5})', transcript, re.IGNORECASE)
                    if address_match:
                        partial_data["address"] = address_match.group(1)
                    
                    # Create partial lead with "Incomplete" status
                    try:
                        from src.integrations.odoo_leads import create_lead_service
                        from src.hael.schema import Entity, Intent
                        from src.utils.request_id import generate_request_id
                        
                        lead_service = await create_lead_service()
                        
                        # Build minimal entity for incomplete lead
                        entities = Entity(
                            full_name=partial_data.get("customer_name"),
                            phone=customer_phone,
                            address=partial_data.get("address"),
                            problem_description=f"Incomplete call - {ended_reason}. Duration: {duration}s. {summary[:200] if summary else ''}",
                        )
                        
                        # Create lead with "Incomplete" tag/status
                        lead_result = await lead_service.upsert_service_lead(
                            entities=entities,
                            urgency_level=None,
                            is_emergency=False,
                            service_type=None,
                            request_id=generate_request_id(),
                            conversation_context=f"Incomplete call: {transcript[:500] if transcript else summary[:500]}",
                            structured_params={
                                "call_status": "Incomplete",
                                "ended_reason": ended_reason,
                                "duration_seconds": duration,
                                "call_id": call_id,
                            },
                        )
                        
                        if lead_result.get("lead_id"):
                            logger.info(f"Created incomplete lead {lead_result['lead_id']} for call {call_id}")
                            
                            # Create callback task in Odoo (as an activity)
                            try:
                                await lead_service.client.create("mail.activity", {
                                    "res_id": lead_result["lead_id"],
                                    "res_model": "crm.lead",
                                    "activity_type_id": await lead_service._get_activity_type_id("Call"),
                                    "summary": f"Callback needed - Incomplete call ({ended_reason})",
                                    "note": f"Call ended prematurely. Duration: {duration}s. Reason: {ended_reason}. Please call customer back.",
                                    "user_id": await lead_service._get_user_id("dispatch"),
                                })
                            except Exception as task_err:
                                logger.warning(f"Failed to create callback task: {task_err}")
                        
                    except Exception as lead_err:
                        logger.warning(f"Failed to create incomplete lead: {lead_err}")
                    
                    # Send SMS fallback
                    try:
                        from src.integrations.twilio_sms import send_incomplete_call_sms
                        sms_result = await send_incomplete_call_sms(to_phone=customer_phone)
                        if sms_result.get("status") == "sent":
                            logger.info(f"Sent incomplete call SMS to {customer_phone}")
                    except Exception as sms_err:
                        logger.warning(f"Failed to send incomplete call SMS: {sms_err}")
                
            except Exception as incomplete_err:
                logger.warning(f"Error handling incomplete call: {incomplete_err}")
        
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
