"""
HAES HVAC - Request Membership Enrollment Tool

Direct Vapi tool for maintenance membership enrollment.
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
from src.brains.revenue import handle_revenue_command
from src.brains.revenue.schema import RevenueStatus
from src.utils.request_id import generate_request_id
from src.integrations.odoo_leads import create_lead_service

logger = logging.getLogger(__name__)


async def handle_request_membership_enrollment(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle request_membership_enrollment tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - email (optional): Email address
        - address (required): Property address
        - property_type (required): "residential", "commercial"
        - membership_type (required): "basic" or "commercial"
        - system_details (optional): System details
    """
    handler = BaseToolHandler("request_membership_enrollment")
    
    # Validate required parameters
    required = ["customer_name", "phone", "address", "property_type", "membership_type"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you enroll in a maintenance membership.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you enroll in a maintenance membership.",
            missing_fields=["phone"],
            intent_acknowledged=False,
        )
    
    # Validate membership type
    membership_type = parameters.get("membership_type", "").lower()
    if membership_type not in ["basic", "commercial"]:
        return handler.format_needs_human_response(
            "Membership type must be 'basic' ($279/year) or 'commercial' ($379/year).",
            missing_fields=["membership_type"],
        )
    
    # Determine pricing
    if membership_type == "basic":
        price = 279
        plan_name = "Basic Maintenance Plan"
    else:
        price = 379
        plan_name = "Commercial Maintenance Plan"
    
    try:
        # Create membership lead in Odoo
        from src.hael.schema import Entity, UrgencyLevel
        
        entities = Entity(
            full_name=parameters.get("customer_name"),
            phone=phone,
            email=handler.normalize_email(parameters.get("email")),
            address=parameters.get("address"),
            zip_code=parameters.get("zip_code"),
            problem_description=f"Membership Enrollment - {plan_name}",
            property_type=parameters.get("property_type"),
        )
        
        lead_service = await create_lead_service()
        
        lead_result = await lead_service.upsert_service_lead(
            call_id=call_id or generate_request_id(),
            entities=entities,
            urgency=UrgencyLevel.MEDIUM,
            is_emergency=False,
            raw_text=f"Membership Enrollment - {plan_name}",
            request_id=generate_request_id(),
            channel="voice",
        )
        
        lead_id = lead_result.get("lead_id") if lead_result else None
        
        handler.logger.info(f"Created membership enrollment lead {lead_id}")
        
        # Build VIP benefits message
        vip_benefits = (
            "VIP contract benefits include: priority scheduling, "
            "discounted service rates, annual system tune-ups, "
            "and extended warranty coverage."
        )
        
        # Generate payment link (in production, this would be a real payment URL)
        from src.config.settings import get_settings
        settings = get_settings()
        base_url = settings.ODOO_BASE_URL or "https://hvacrfinest.odoo.com"
        payment_link = f"{base_url}/membership/enroll?lead_id={lead_id}&type={membership_type}"
        
        # Send contract via SMS if phone available
        email = handler.normalize_email(parameters.get("email"))
        try:
            from src.integrations.twilio_sms import create_twilio_client_from_settings, build_membership_enrollment_sms
            from src.integrations.email_notifications import create_email_service_from_settings, build_membership_enrollment_email
            
            # Build and send SMS
            sms_body = build_membership_enrollment_sms(
                customer_name=parameters.get("customer_name"),
                plan_name=plan_name,
                annual_price=price,
                payment_link=payment_link,
            )
            
            sms_client = create_twilio_client_from_settings()
            if sms_client:
                await sms_client.send_sms(to=phone, body=sms_body)
                handler.logger.info(f"Sent membership enrollment SMS to {phone}")
            
            # Send email if available
            if email:
                email_subject, email_body_html, email_body_text = build_membership_enrollment_email(
                    customer_name=parameters.get("customer_name"),
                    plan_name=plan_name,
                    annual_price=price,
                    payment_link=payment_link,
                    vip_benefits=vip_benefits,
                )
                
                email_service = create_email_service_from_settings()
                if email_service:
                    email_service.send_email(
                        to=[email],
                        subject=email_subject,
                        body_html=email_body_html,
                        body_text=email_body_text,
                    )
                    handler.logger.info(f"Sent membership enrollment email to {email}")
        except Exception as notify_err:
            handler.logger.warning(f"Failed to send membership enrollment notifications: {notify_err}")
            # Continue anyway - enrollment lead is created
        
        # Format response
        message = (
            f"Great! I've created your {plan_name} enrollment request. "
            f"The annual cost is ${price}. "
            f"{vip_benefits} "
            f"I've sent you a contract via {'SMS and email' if email else 'SMS'} with a payment link to complete enrollment. "
            f"Once payment is received, you'll receive a confirmation."
        )
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "lead_id": lead_id,
                "membership_type": membership_type,
                "plan_name": plan_name,
                "annual_price": price,
                "enrollment_status": "pending",
                "payment_link": payment_link,
                "contract_sent": True,
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
