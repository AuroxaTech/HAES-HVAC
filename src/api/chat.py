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


class ChatPreQualificationRequest(BaseModel):
    """Request schema for pre-qualification form."""
    session_id: str
    name: str
    email: str
    phone: str
    service_needed: str
    address: str | None = None
    zip_code: str | None = None
    problem_description: str | None = None
    property_type: str | None = None


class ChatPreQualificationResponse(BaseModel):
    """Response schema for pre-qualification form."""
    success: bool
    message: str
    session_id: str
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/pre-qualification", response_model=ChatPreQualificationResponse)
async def chat_pre_qualification(request: ChatPreQualificationRequest) -> ChatPreQualificationResponse:
    """
    Handle pre-qualification form submission from chat widget.
    
    Validates required fields and creates a lead in Odoo.
    This endpoint is called when the user submits the pre-qualification form.
    """
    logger.info(f"Chat pre-qualification: session_id={request.session_id}")
    
    try:
        # Validate required fields (Pydantic already does this, but we can add custom validation)
        if not request.name or not request.name.strip():
            return ChatPreQualificationResponse(
                success=False,
                message="Name is required",
                session_id=request.session_id,
                data={"missing_field": "name"},
            )
        
        if not request.email or not request.email.strip():
            return ChatPreQualificationResponse(
                success=False,
                message="Email is required",
                session_id=request.session_id,
                data={"missing_field": "email"},
            )
        
        if not request.phone or not request.phone.strip():
            return ChatPreQualificationResponse(
                success=False,
                message="Phone is required",
                session_id=request.session_id,
                data={"missing_field": "phone"},
            )
        
        if not request.service_needed or not request.service_needed.strip():
            return ChatPreQualificationResponse(
                success=False,
                message="Service needed is required",
                session_id=request.session_id,
                data={"missing_field": "service_needed"},
            )
        
        # Basic email validation
        if "@" not in request.email or "." not in request.email.split("@")[-1]:
            return ChatPreQualificationResponse(
                success=False,
                message="Please provide a valid email address",
                session_id=request.session_id,
                data={"invalid_field": "email"},
            )
        
        # Basic phone validation (at least 10 digits)
        phone_digits = "".join(filter(str.isdigit, request.phone))
        if len(phone_digits) < 10:
            return ChatPreQualificationResponse(
                success=False,
                message="Please provide a valid phone number",
                session_id=request.session_id,
                data={"invalid_field": "phone"},
            )
        
        # Create lead in Odoo using the chat message flow
        # We'll create a simplified lead creation here
        try:
            from src.hael.schema import Entity, Channel, Intent, Brain, UrgencyLevel
            from src.integrations.odoo_leads import create_lead_service
            from src.utils.request_id import generate_request_id
            
            # Build entity from pre-qualification form
            entities = Entity(
                full_name=request.name.strip(),
                phone=request.phone.strip(),
                email=request.email.strip(),
                address=request.address.strip() if request.address else None,
                zip_code=request.zip_code.strip() if request.zip_code else None,
                problem_description=request.problem_description or request.service_needed,
                property_type=request.property_type,
            )
            
            # Create lead
            lead_service = await create_lead_service()
            
            call_id = f"chat_{request.session_id}_{generate_request_id()}"
            lead_result = await lead_service.upsert_service_lead(
                call_id=call_id,
                entities=entities,
                urgency=UrgencyLevel.MEDIUM,  # Default to medium for pre-qualification
                is_emergency=False,
                raw_text=f"Pre-qualification: {request.service_needed}",
                request_id=generate_request_id(),
                channel="chat",
            )
            
            lead_id = lead_result.get("lead_id") if lead_result else None
            
            # Send notification
            try:
                from src.integrations.email_notifications import send_new_lead_notification
                from src.config.settings import get_settings
                
                settings = get_settings()
                odoo_base_url = settings.ODOO_BASE_URL or "https://hvacrfinest.odoo.com"
                odoo_url = f"{odoo_base_url}/web#id={lead_id}&model=crm.lead&view_type=form" if lead_id else None
                
                await send_new_lead_notification(
                    customer_name=request.name,
                    phone=request.phone,
                    email=request.email,
                    address=request.address,
                    service_type=request.service_needed,
                    priority_label="Medium",
                    assigned_technician=None,  # Will be assigned later
                    lead_id=lead_id,
                    odoo_url=odoo_url,
                )
            except Exception as notify_err:
                logger.warning(f"Failed to send pre-qualification lead notification: {notify_err}")
            
            return ChatPreQualificationResponse(
                success=True,
                message="Thank you! We've received your information and will contact you shortly.",
                session_id=request.session_id,
                data={
                    "lead_id": lead_id,
                    "lead_created": True,
                },
            )
            
        except Exception as lead_err:
            logger.error(f"Failed to create lead from pre-qualification: {lead_err}")
            # Still return success to user, but log the error
            return ChatPreQualificationResponse(
                success=True,
                message="Thank you! We've received your information. A representative will contact you shortly.",
                session_id=request.session_id,
                data={
                    "lead_created": False,
                    "error": "Lead creation failed, but information captured",
                },
            )
    
    except Exception as e:
        logger.exception(f"Error processing pre-qualification: {e}")
        return ChatPreQualificationResponse(
            success=False,
            message="I'm sorry, something went wrong. Please try again or contact us directly.",
            session_id=request.session_id,
            data={"error": str(e)},
        )


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """
    Process a chat message and return a response.

    This endpoint is called by the website chat widget.
    It runs the same HAEL pipeline as voice but returns
    a text-formatted response.
    """
    logger.info(f"Chat message: session_id={request.session_id}")

    # Check if after hours
    from src.vapi.tools.utils.check_business_hours import is_business_hours
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    is_after_hours = not is_business_hours()
    
    # If after hours and this is a new conversation (no previous context), show offline message
    if is_after_hours and not request.metadata.get("conversation_started"):
        # Calculate next business day
        now = datetime.now(ZoneInfo("America/Chicago"))
        next_day = now
        while next_day.weekday() >= 5 or (next_day.weekday() < 5 and next_day.hour >= 17):
            next_day = next_day + timedelta(days=1)
            if next_day.weekday() >= 5:
                # Skip weekends
                days_until_monday = (7 - next_day.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_day = next_day + timedelta(days=days_until_monday)
            next_day = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
            if next_day.weekday() < 5:
                break
        
        offline_message = (
            f"Our team is currently offline (8am-5pm CST, Monday-Friday). "
            f"We'll respond to your message on {next_day.strftime('%A, %B %d')} during business hours. "
            f"Please leave your contact information and we'll get back to you!"
        )
        
        return ChatMessageResponse(
            reply_text=offline_message,
            action="needs_human",
            data={
                "after_hours": True,
                "next_business_day": next_day.isoformat(),
                "hide_live_handoff": True,  # Flag for frontend to hide handoff option
                "offline_mode": True,
            },
            session_id=request.session_id,
        )

    # Check if user wants to speak with someone (live handoff request)
    user_text_lower = request.user_text.lower()
    handoff_keywords = [
        "speak with", "talk to", "speak to", "talk with",
        "human", "person", "representative", "agent",
        "someone", "someone else", "real person",
        "transfer", "handoff", "connect me",
    ]
    wants_handoff = any(keyword in user_text_lower for keyword in handoff_keywords)
    
    # If user wants handoff and it's business hours, offer live handoff
    if wants_handoff and not is_after_hours:
        # Create handoff notification/task for customer service
        try:
            from src.integrations.email_notifications import create_email_service_from_settings
            from src.config.settings import get_settings
            from src.utils.request_id import generate_request_id
            
            settings = get_settings()
            email_service = create_email_service_from_settings()
            
            if email_service:
                # Get chat context from request metadata
                chat_context = {
                    "session_id": request.session_id,
                    "messages": request.metadata.get("chat_history", []),
                    "user_text": request.user_text,
                    "timestamp": datetime.now(ZoneInfo("America/Chicago")).isoformat(),
                }
                
                # Send notification to customer service team
                subject = f"Chat Handoff Request - Session {request.session_id}"
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #1976d2; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .context-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>HVAC-R Finest</h1>
                            <h2>Chat Handoff Request</h2>
                        </div>
                        <div class="content">
                            <p>A customer has requested to speak with a representative.</p>
                            <div class="context-box">
                                <h3>Chat Context</h3>
                                <p><strong>Session ID:</strong> {request.session_id}</p>
                                <p><strong>Customer Message:</strong> {request.user_text}</p>
                                <p><strong>Timestamp:</strong> {chat_context['timestamp']}</p>
                            </div>
                            <p>Please take over this chat conversation.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                text_body = f"""
Chat Handoff Request

A customer has requested to speak with a representative.

Session ID: {request.session_id}
Customer Message: {request.user_text}
Timestamp: {chat_context['timestamp']}

Please take over this chat conversation.
                """
                
                # Send to customer service email (use info@ as default)
                recipients = []
                if settings.DISPATCH_EMAIL:
                    recipients.append(settings.DISPATCH_EMAIL)
                recipients.append("info@hvacrfinest.com")
                
                for recipient in recipients:
                    try:
                        email_service.send_email(
                            to=[recipient],
                            subject=subject,
                            body_html=html_body,
                            body_text=text_body,
                        )
                        logger.info(f"Sent chat handoff notification to {recipient}")
                    except Exception as email_err:
                        logger.warning(f"Failed to send handoff notification to {recipient}: {email_err}")
                
        except Exception as notify_err:
            logger.warning(f"Failed to send handoff notification: {notify_err}")
        
        # Return handoff response
        handoff_message = (
            "I'd be happy to connect you with our customer service team. "
            "One of our representatives will be with you shortly. "
            "They have access to our conversation history and will be able to assist you further."
        )
        
        return ChatMessageResponse(
            reply_text=handoff_message,
            action="needs_human",
            data={
                "live_handoff_requested": True,
                "handoff_initiated": True,
                "session_id": request.session_id,
                "chat_context_passed": True,
                "customer_service_notified": True,
            },
            session_id=request.session_id,
        )
    
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
        
        # Handle after-hours: create lead for callback if after hours
        if is_after_hours and result is not None and action == "completed":
            # Extract customer info from result to create callback lead
            try:
                from src.hael.schema import Entity, UrgencyLevel
                from src.integrations.odoo_leads import create_lead_service
                from src.utils.request_id import generate_request_id
                from src.db.models import Job
                from src.db.session import get_session_factory
                
                # Extract entities from command
                entities = command.entities
                
                # Create callback lead
                lead_service = await create_lead_service()
                
                call_id = f"chat_callback_{request.session_id}_{generate_request_id()}"
                lead_result = await lead_service.upsert_service_lead(
                    call_id=call_id,
                    entities=entities,
                    urgency=UrgencyLevel.MEDIUM,
                    is_emergency=False,
                    raw_text=f"After-hours chat: {request.user_text}",
                    request_id=generate_request_id(),
                    channel="chat",
                )
                
                lead_id = lead_result.get("lead_id") if lead_result else None
                
                # Schedule callback for next business day
                session_factory = get_session_factory()
                session = session_factory()
                try:
                    # Calculate next business day at 8 AM
                    now = datetime.now(ZoneInfo("America/Chicago"))
                    next_day = now
                    while next_day.weekday() >= 5 or (next_day.weekday() < 5 and next_day.hour >= 17):
                        next_day = next_day + timedelta(days=1)
                        if next_day.weekday() >= 5:
                            days_until_monday = (7 - next_day.weekday()) % 7
                            if days_until_monday == 0:
                                days_until_monday = 7
                            next_day = next_day + timedelta(days=days_until_monday)
                        next_day = next_day.replace(hour=8, minute=0, second=0, microsecond=0)
                        if next_day.weekday() < 5:
                            break
                    
                    # Create callback job
                    callback_job = Job(
                        run_at=next_day,
                        type="chat_callback",
                        payload_json={
                            "lead_id": lead_id,
                            "session_id": request.session_id,
                            "customer_name": entities.full_name,
                            "phone": entities.phone,
                            "email": entities.email,
                            "message": request.user_text,
                        },
                        correlation_id=f"chat_callback_{request.session_id}",
                        max_attempts=3,
                    )
                    session.add(callback_job)
                    session.commit()
                    logger.info(f"Scheduled callback job for chat session {request.session_id} on {next_day}")
                except Exception as job_err:
                    logger.error(f"Failed to schedule callback job: {job_err}")
                finally:
                    session.close()
                
                # Update reply to include callback confirmation
                reply = (
                    f"{reply}\n\n"
                    f"Since we're currently outside business hours (8am-5pm CST, Monday-Friday), "
                    f"we've created a callback task and will contact you on {next_day.strftime('%A, %B %d')} during business hours."
                )
                data["callback_scheduled"] = True
                data["callback_date"] = next_day.isoformat()
                data["hide_live_handoff"] = True  # Flag for frontend
                
            except Exception as callback_err:
                logger.warning(f"Failed to create after-hours callback: {callback_err}")
        
        # Send lead notification if lead was created (for chat leads)
        if result is not None and action == "completed":
            # Check if lead was created (from OPS brain typically)
            if routing.brain == Brain.OPS and hasattr(result, "work_order") and result.work_order:
                try:
                    from src.integrations.email_notifications import send_new_lead_notification
                    from src.config.settings import get_settings
                    
                    work_order = result.work_order
                    settings = get_settings()
                    odoo_base_url = settings.ODOO_BASE_URL or "https://hvacrfinest.odoo.com"
                    
                    # Try to get lead_id from data if available
                    lead_id = data.get("lead_id") if data else None
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
                except Exception as notify_err:
                    logger.warning(f"Failed to send chat lead notification: {notify_err}")

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

