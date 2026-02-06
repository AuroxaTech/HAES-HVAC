"""
HAES HVAC - Create Service Request Tool

Direct Vapi tool for creating service requests (emergency or standard).
"""

import asyncio
import logging
from typing import Any
from datetime import datetime

from src.vapi.tools.base import BaseToolHandler, ToolResponse, handle_tool_call_with_base
from src.hael.schema import (
    Channel,
    Entity,
    HaelCommand,
    Intent,
    UrgencyLevel,
    Brain,
)
from src.brains.ops import handle_ops_command
from src.brains.ops.schema import OpsStatus
from src.utils.request_id import generate_request_id
from src.vapi.tools.utils.service_area import is_within_service_area
from src.vapi.tools.utils.check_business_hours import is_business_hours
from src.integrations.odoo_leads import create_lead_service

logger = logging.getLogger(__name__)


async def handle_create_service_request(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle create_service_request tool call.
    
    Parameters:
        - customer_name (optional): Customer name
        - phone (required): Phone number
        - email (optional): Email address
        - address (required): Service address
        - issue_description (required): Problem description
        - urgency (optional): "emergency", "high", "medium", "low"
        - system_type (optional): HVAC system type
        - indoor_temperature_f (optional): Indoor temperature for emergency qualification
        - property_type (optional): "residential", "commercial", "property_management"
        - is_warranty (optional): Boolean, true if warranty claim
        - previous_service_id (optional): Previous service ID for warranty claims
        - previous_technician_id (optional): Previous technician ID for warranty claims
    """
    handler = BaseToolHandler("create_service_request")
    
    # Validate required parameters
    required = ["phone", "address", "issue_description"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        # Intent-First Rule: Don't ask for details in the same response as acknowledging intent
        # The AI should acknowledge intent first, then ask for missing fields one at a time
        # Just indicate what's needed without asking directly
        return handler.format_needs_human_response(
            "I can help you create a service request.",
            missing_fields=missing,
            intent_acknowledged=False,  # AI needs to acknowledge intent first
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you create a service request.",
            missing_fields=["phone"],
            intent_acknowledged=False,
        )
    
    # Check for duplicate call (recent call or existing appointment)
    duplicate_info = await handler.check_duplicate_call(phone, call_id)
    if duplicate_info and duplicate_info.get("is_duplicate"):
        # Return friendly message referencing existing appointment
        message = duplicate_info.get("message", "Welcome back! I see you just called. Would you like to modify your appointment?")
        return ToolResponse(
            speak=message,
            action="needs_human",
            data={
                "is_duplicate_call": True,
                "existing_appointment": duplicate_info.get("existing_appointment"),
                "recent_call_hours_ago": duplicate_info.get("recent_call_hours_ago"),
            },
        )
    
    # Validate service area (35-mile radius)
    address = parameters.get("address", "").strip()
    zip_code = parameters.get("zip_code")
    
    is_within, area_error = is_within_service_area(address, zip_code)
    if not is_within and area_error:
        # Out of service area - return polite rejection
        return ToolResponse(
            speak=f"{area_error} We'd be happy to take your contact information for when we expand to your area.",
            action="needs_human",
            data={
                "out_of_service_area": True,
                "distance_error": area_error,
            },
        )
    
    # Build Entity from parameters
    urgency_str = parameters.get("urgency", "unknown").lower()
    
    # Check business hours and weekend
    now = datetime.now()
    is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
    is_after_hours = not is_business_hours()
    
    # Build premium messaging
    premium_messages = []
    if is_weekend:
        premium_messages.append("All weekends are booked out. If an opening becomes available, we'll reach out. To lock you in, we have availability during the week.")
    elif is_after_hours:
        premium_messages.append("We're currently outside business hours. After-hours service may be available with additional premiums.")
    
    # Emergency calls get priority regardless of time
    is_emergency = urgency_str == "emergency"
    if is_emergency and (is_weekend or is_after_hours):
        premium_messages.append("Since this is an emergency, we'll prioritize getting a technician out to you.")
    urgency_level = UrgencyLevel.UNKNOWN
    if urgency_str == "emergency":
        urgency_level = UrgencyLevel.EMERGENCY
    elif urgency_str == "high":
        urgency_level = UrgencyLevel.HIGH
    elif urgency_str == "medium":
        urgency_level = UrgencyLevel.MEDIUM
    elif urgency_str == "low":
        urgency_level = UrgencyLevel.LOW
    
    # Handle temperature for emergency qualification
    temperature_mentioned = None
    if parameters.get("indoor_temperature_f"):
        try:
            temperature_mentioned = int(parameters["indoor_temperature_f"])
        except (ValueError, TypeError):
            pass
    
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=phone,
        email=handler.normalize_email(parameters.get("email")),
        address=address,
        zip_code=zip_code or parameters.get("zip_code"),
        problem_description=parameters.get("issue_description"),
        system_type=parameters.get("system_type"),
        urgency_level=urgency_level,
        property_type=parameters.get("property_type"),
        temperature_mentioned=temperature_mentioned,
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or parameters.get("issue_description", ""),
        intent=Intent.SERVICE_REQUEST,
        brain=Brain.OPS,
        entities=entities,
        confidence=0.9,  # High confidence since tool was explicitly called
        requires_human=False,
        missing_fields=[],
        idempotency_key="",  # Will be generated by handler
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
            "is_warranty": parameters.get("is_warranty", False),
            "previous_service_id": parameters.get("previous_service_id"),
            "previous_technician_id": parameters.get("previous_technician_id"),
        },
    )
    
    # Handle warranty claims if specified
    if parameters.get("is_warranty"):
        # TODO: Enhance _handle_service_request to handle warranty
        # For now, pass warranty info in metadata
        handler.logger.info(
            f"Warranty claim detected: previous_service_id={parameters.get('previous_service_id')}, "
            f"previous_technician_id={parameters.get('previous_technician_id')}"
        )
    
    # Call OPS brain handler
    try:
        handler.logger.info(f"Calling handle_ops_command for service request: phone={phone}, address={address[:50]}")
        result = await handle_ops_command(command)
        handler.logger.info(f"handle_ops_command completed: status={result.status}, requires_human={result.requires_human}")
        
        # Check if needs human
        if result.requires_human or result.status == OpsStatus.NEEDS_HUMAN:
            return handler.format_needs_human_response(
                result.message,
                missing_fields=getattr(result, "missing_fields", None),
                data=result.data or {},
            )
        
        # Check for errors
        if result.status == OpsStatus.ERROR:
            return handler.format_error_response(
                Exception(result.message),
                "I encountered an error processing your service request. Please try again or contact us directly.",
            )
        
        # Success - create lead in Odoo with error handling
        # Use timeout to ensure we respond within 25 seconds (Vapi timeout is 30s)
        lead_id = None
        try:
            from src.utils.odoo_error_handler import OdooErrorHandler
            from src.db.session import get_session_factory
            
            session_factory = get_session_factory()
            session = session_factory()
            
            try:
                odoo_client = handler.get_odoo_client()
                lead_service = await create_lead_service()
                
                # Extract work order data
                work_order = result.work_order
                if work_order:
                    # Build lead data
                    lead_data = {
                        "name": work_order.customer_name or "Service Request",
                        "contact_name": work_order.customer_name,
                        "phone": work_order.customer_phone,
                        "email_from": work_order.customer_email,
                        "street": work_order.address,
                        "zip": work_order.zip_code,
                        "description": work_order.problem_description,
                    }
                    
                    # Add warranty info if applicable
                    if parameters.get("is_warranty"):
                        lead_data["description"] = (
                            f"[WARRANTY CLAIM]\n{lead_data.get('description', '')}\n"
                            f"Previous Service ID: {parameters.get('previous_service_id', 'N/A')}\n"
                            f"Previous Technician ID: {parameters.get('previous_technician_id', 'N/A')}"
                        )
                    
                    # Create/update lead with timeout (15 seconds max)
                    # Determine channel from command
                    channel_str = "voice" if command.channel == Channel.VOICE else "chat"
                    
                    structured_params = {}
                    if parameters.get("lead_source"):
                        structured_params["lead_source"] = parameters.get("lead_source")
                    if parameters.get("confirmed_partner_id") is not None:
                        structured_params["_returning_customer"] = {"partner_id": parameters["confirmed_partner_id"]}
                    elif parameters.get("_returning_customer"):
                        structured_params["_returning_customer"] = parameters.get("_returning_customer")
                    if parameters.get("caller_type"):
                        structured_params["caller_type"] = parameters.get("caller_type")
                    try:
                        lead_id = await asyncio.wait_for(
                            lead_service.upsert_service_lead(
                                call_id=call_id or request_id,
                                entities=entities,  # Pass entities instead of individual fields
                                urgency=urgency_level,
                                is_emergency=result.data.get("is_emergency", False),
                                emergency_reason=result.data.get("emergency_reason"),
                                raw_text=conversation_context or parameters.get("issue_description", ""),
                                request_id=request_id,
                                channel=channel_str,
                                structured_params=structured_params or None,
                            ),
                            timeout=15.0,  # 15 second timeout for Odoo call
                        )
                        handler.logger.info(f"Created Odoo lead {lead_id} for service request")
                    except asyncio.TimeoutError:
                        handler.logger.warning("Odoo lead creation timed out after 15s, continuing without lead_id")
                        # Continue without lead_id - fail-closed approach
                        lead_id = None
                    
                    # Send lead notification emails (fire-and-forget to avoid timeout)
                    # Use asyncio.create_task to run in background
                    if lead_id:  # Only send if lead was created
                        try:
                            from src.integrations.email_notifications import send_new_lead_notification
                            from src.config.settings import get_settings
                            
                            async def send_notification_background():
                                try:
                                    settings = get_settings()
                                    odoo_base_url = settings.ODOO_BASE_URL or "https://hvacrfinest.odoo.com"
                                    odoo_url = f"{odoo_base_url}/web#id={lead_id}&model=crm.lead&view_type=form" if lead_id else None
                                    
                                    await send_new_lead_notification(
                                        customer_name=work_order.customer_name,
                                        phone=work_order.customer_phone,
                                        email=work_order.customer_email,
                                        address=work_order.address,
                                        service_type=work_order.service_type,
                                        priority_label=work_order.priority.value if work_order.priority else None,
                                        assigned_technician=work_order.technician.technician_name if work_order.technician else None,
                                        lead_id=lead_id,
                                        odoo_url=odoo_url,
                                    )
                                except Exception as bg_err:
                                    handler.logger.warning(f"Background email notification failed: {bg_err}")
                            
                            # Start background task (don't await - fire and forget)
                            asyncio.create_task(send_notification_background())
                        except Exception as notify_err:
                            handler.logger.warning(f"Failed to start email notification task: {notify_err}")
            except Exception as e:
                # Check if it's an Odoo error and handle gracefully
                from src.utils.errors import OdooAuthError, OdooRPCError, OdooTransportError
                from src.utils.odoo_error_handler import OdooErrorHandler
                
                if isinstance(e, (OdooAuthError, OdooRPCError, OdooTransportError)):
                    # Odoo error - use graceful degradation
                    error_result = await OdooErrorHandler.handle_odoo_error(
                        error=e,
                        operation="create_service_request_lead",
                        data={
                            "customer_name": parameters.get("customer_name"),
                            "phone": phone,
                            "address": address,
                            "issue_description": parameters.get("issue_description"),
                        },
                        session=session,
                    )
                    handler.logger.warning(f"Odoo error handled gracefully: {error_result}")
                    # Return user-friendly message
                    return handler.format_needs_human_response(
                        error_result["user_message"],
                        data={
                            "odoo_error": True,
                            "data_captured": error_result["data_captured"],
                        },
                    )
                else:
                    # Other error - log and continue
                    handler.logger.warning(f"Failed to create Odoo lead: {e}")
                    # Continue anyway - lead creation failure shouldn't block response
            finally:
                session.close()
        except Exception as e:
            # Check if it's an Odoo error in the outer try block
            from src.utils.errors import OdooAuthError, OdooRPCError, OdooTransportError
            from src.utils.odoo_error_handler import OdooErrorHandler
            from src.db.session import get_session_factory
            
            if isinstance(e, (OdooAuthError, OdooRPCError, OdooTransportError)):
                session_factory = get_session_factory()
                session = session_factory()
                try:
                    error_result = await OdooErrorHandler.handle_odoo_error(
                        error=e,
                        operation="create_service_request",
                        data={
                            "customer_name": parameters.get("customer_name"),
                            "phone": phone,
                            "address": address,
                            "issue_description": parameters.get("issue_description"),
                        },
                        session=session,
                    )
                    return handler.format_needs_human_response(
                        error_result["user_message"],
                        data={
                            "odoo_error": True,
                            "data_captured": error_result["data_captured"],
                        },
                    )
                finally:
                    session.close()
        
        # Format success response
        response_data = result.data or {}
        response_data["request_id"] = request_id
        
        # Add lead_id if it was created (even if None due to timeout)
        if lead_id:
            response_data["lead_id"] = lead_id
        
        # Add warranty terms if warranty claim
        if parameters.get("is_warranty"):
            response_data["warranty_terms"] = {
                "repairs": "30-day labor warranty",
                "equipment": "1-year labor warranty",
            }
        
        # Enhance message with business hours/weekend info and warranty terms
        enhanced_message = result.message
        
        # Add premium messaging if applicable
        if premium_messages:
            enhanced_message += " " + " ".join(premium_messages)
        
        # Add warranty terms to message if warranty claim
        if parameters.get("is_warranty"):
            enhanced_message += " As a warranty claim, this service includes: Repairs - 30-day labor warranty, Equipment - 1-year labor warranty. The diagnostic fee will be waived."
        
        # Add business hours/weekend flags to response data
        response_data["is_weekend"] = is_weekend
        response_data["is_after_hours"] = is_after_hours
        response_data["premium_applies"] = is_weekend or is_after_hours
        
        return handler.format_success_response(
            enhanced_message,
            data=response_data,
        )
    
    except Exception as e:
        handler.logger.exception(f"Error in create_service_request tool: {e}")
        return handler.format_error_response(e)
