"""
HAES HVAC - Schedule Appointment Tool

Direct Vapi tool for scheduling appointments.
"""

import logging
from typing import Any
from datetime import datetime

from src.vapi.tools.base import BaseToolHandler, ToolResponse
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

logger = logging.getLogger(__name__)


async def handle_schedule_appointment(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle schedule_appointment tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - email (optional): Email address
        - address (required): Service address
        - service_type (optional): Service type
        - preferred_time_windows (optional): List of preferred time windows
        - problem_description (optional): Problem description
        - property_type (optional): "residential", "commercial", "property_management"
    """
    handler = BaseToolHandler("schedule_appointment")
    
    # Validate required parameters
    required = ["customer_name", "phone", "address"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        # Intent-First Rule: Don't ask for details in the same response as acknowledging intent
        return handler.format_needs_human_response(
            "I can help you schedule an appointment.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you schedule an appointment.",
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
    
    # Validate service area
    address = parameters.get("address", "").strip()
    zip_code = parameters.get("zip_code")
    
    is_within, area_error = is_within_service_area(address, zip_code)
    if not is_within and area_error:
        return ToolResponse(
            speak=f"{area_error} We'd be happy to take your contact information for when we expand to your area.",
            action="needs_human",
            data={
                "out_of_service_area": True,
                "distance_error": area_error,
            },
        )
    
    # Check business hours and weekend
    now = datetime.now()
    is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
    is_after_hours = not is_business_hours()
    
    # Build premium messaging
    premium_messages = []
    if is_weekend:
        premium_messages.append("All weekends are booked out. If an opening becomes available, we'll reach out. To lock you in, we have availability during the week.")
    elif is_after_hours:
        premium_messages.append("We're currently outside business hours. Weekend appointments may have additional premiums.")
    
    # Build Entity
    preferred_windows = parameters.get("preferred_time_windows", [])
    if isinstance(preferred_windows, str):
        preferred_windows = [preferred_windows]
    
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=phone,
        email=handler.normalize_email(parameters.get("email")),
        address=address,
        zip_code=zip_code or parameters.get("zip_code"),
        problem_description=parameters.get("problem_description") or parameters.get("service_type") or "General service",
        preferred_time_windows=preferred_windows,
        property_type=parameters.get("property_type"),
    )
    
    # Build chosen_slot_start: use explicit param or preferred_date + preferred_time (for Vapi tools that only have preferred_date/preferred_time)
    chosen_slot_start = parameters.get("chosen_slot_start")
    if not chosen_slot_start and parameters.get("preferred_date") and parameters.get("preferred_time"):
        pd = str(parameters["preferred_date"]).strip()
        pt = str(parameters["preferred_time"]).strip()
        if len(pt) <= 5 and ":" in pt:
            pt = pt + ":00"  # 10:00 -> 10:00:00
        chosen_slot_start = f"{pd}T{pt}" if pt else None

    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or parameters.get("problem_description", ""),
        intent=Intent.SCHEDULE_APPOINTMENT,
        brain=Brain.OPS,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
            "chosen_slot_start": chosen_slot_start,
            "_returning_customer": (
                {"partner_id": parameters["confirmed_partner_id"]}
                if parameters.get("confirmed_partner_id") is not None
                else parameters.get("_returning_customer")
            ),
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
                "I encountered an error scheduling your appointment. Please try again or contact us directly.",
            )
        
        # Format success response
        response_data = result.data or {}
        response_data["request_id"] = request_id
        
        # Schedule reminder SMS 2 hours before appointment
        if result.data and result.data.get("appointment_id") and result.data.get("scheduled_time"):
            try:
                from src.db.session import get_session_factory
                from src.utils.appointment_reminders import schedule_appointment_reminder
                # datetime is already imported at the top of the file
                
                appointment_id = result.data["appointment_id"]
                scheduled_time_str = result.data["scheduled_time"]
                # Parse datetime and ensure it's timezone-aware
                if scheduled_time_str.endswith("Z"):
                    scheduled_time = datetime.fromisoformat(scheduled_time_str.replace("Z", "+00:00"))
                elif "+" in scheduled_time_str or scheduled_time_str.count("-") > 2:
                    # Already has timezone info
                    scheduled_time = datetime.fromisoformat(scheduled_time_str)
                else:
                    # Naive datetime, assume local timezone (CST/CDT)
                    from datetime import timezone, timedelta
                    cst = timezone(timedelta(hours=-6))  # CST is UTC-6
                    scheduled_time = datetime.fromisoformat(scheduled_time_str).replace(tzinfo=cst)
                
                # Get database session
                session_factory = get_session_factory()
                db = session_factory()
                try:
                    # Format appointment date/time for SMS and email
                    appointment_date = scheduled_time.strftime("%A, %B %d")
                    appointment_time = scheduled_time.strftime("%I:%M %p")
                    
                    # Get technician name and service type
                    tech_info = result.data.get("assigned_technician", {})
                    tech_name = tech_info.get("name") if tech_info else None
                    service_type = result.data.get("service_type")
                    customer_name = parameters.get("customer_name")

                    # Send immediate confirmation SMS to customer
                    try:
                        from src.integrations.twilio_sms import send_service_confirmation_sms
                        sms_result = await send_service_confirmation_sms(
                            to_phone=phone,
                            customer_name=customer_name,
                            appointment_date=appointment_date,
                            appointment_time=appointment_time,
                            tech_name=tech_name,
                            service_type=service_type,
                        )
                        if sms_result.get("status") == "sent":
                            logger.info(f"Sent new appointment confirmation SMS to {phone}")
                            response_data["confirmation_sms_sent"] = True
                    except Exception as sms_err:
                        logger.warning(f"Failed to send appointment confirmation SMS: {sms_err}")

                    # Send immediate confirmation email to customer (if email provided)
                    customer_email = handler.normalize_email(parameters.get("email")) if parameters.get("email") else None
                    if customer_email:
                        try:
                            from src.integrations.email_notifications import send_service_confirmation_email
                            email_result = await send_service_confirmation_email(
                                to_email=customer_email,
                                customer_name=customer_name,
                                is_same_day=False,
                                appointment_date=f"{appointment_date} at {appointment_time}",
                            )
                            if email_result.get("status") == "sent":
                                logger.info(f"Sent new appointment confirmation email to {customer_email}")
                                response_data["confirmation_email_sent"] = True
                        except Exception as email_err:
                            logger.warning(f"Failed to send appointment confirmation email: {email_err}")
                    
                    # Schedule reminder
                    job_id = schedule_appointment_reminder(
                        db=db,
                        appointment_id=appointment_id,
                        appointment_datetime=scheduled_time,
                        customer_phone=phone,
                        customer_name=parameters.get("customer_name"),
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        tech_name=tech_name,
                        service_type=result.data.get("service_type"),
                    )
                    
                    if job_id:
                        logger.info(f"Scheduled reminder SMS job {job_id} for appointment {appointment_id}")
                        response_data["reminder_scheduled"] = True
                    
                    db.commit()
                except Exception as e:
                    logger.warning(f"Failed to schedule reminder SMS: {e}")
                    db.rollback()
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Error scheduling reminder SMS: {e}")
        
        # Enhance message with business hours/weekend info
        enhanced_message = result.message
        
        # Add premium messaging if applicable
        if premium_messages:
            enhanced_message += " " + " ".join(premium_messages)
        
        # Add business hours/weekend flags to response data
        response_data["is_weekend"] = is_weekend
        response_data["is_after_hours"] = is_after_hours
        response_data["premium_applies"] = is_weekend or is_after_hours
        
        return handler.format_success_response(
            enhanced_message,
            data=response_data,
        )
    
    except Exception as e:
        return handler.format_error_response(e)
