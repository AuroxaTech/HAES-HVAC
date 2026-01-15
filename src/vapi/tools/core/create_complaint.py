"""
HAES HVAC - Create Complaint Tool

Direct Vapi tool for creating complaint/escalation tickets.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.integrations.odoo import create_odoo_client_from_settings
from src.integrations.email_notifications import (
    create_email_service_from_settings,
    build_emergency_staff_notification_email,
)
from src.integrations.twilio_sms import (
    create_twilio_client_from_settings,
)
from src.config.settings import get_settings
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)

# Prohibited phrases that must NOT be used
PROHIBITED_PHRASES = [
    "we'll fix it for free",
    "we caused that",
    "we will reimburse you",
    "we are responsible for damages",
    "i promise",
    "we guarantee",
    "it's free",
    "that will definitely fix it",
    "it's probably nothing",
    "you don't need a technician",
]


async def handle_create_complaint(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle create_complaint tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - email (optional): Email address
        - complaint_details (required): Complaint details
        - service_date (optional): Date of service
        - service_id (optional): Service ID
    """
    handler = BaseToolHandler("create_complaint")
    
    # Validate required parameters
    required = ["customer_name", "phone", "complaint_details"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you document your complaint.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you document your complaint.",
            missing_fields=["phone"],
            intent_acknowledged=False,
        )
    
    try:
        # Create escalation ticket in Odoo
        odoo_client = handler.get_odoo_client()
        await odoo_client.authenticate()
        
        # Create a CRM lead with escalation tag and URGENT priority
        lead_data = {
            "name": f"🚨 URGENT: Complaint/Escalation - {parameters.get('customer_name')}",
            "contact_name": parameters.get("customer_name"),
            "phone": phone,
            "email_from": handler.normalize_email(parameters.get("email")),
            "description": (
                f"🚨 URGENT COMPLAINT/ESCALATION\n\n"
                f"Customer: {parameters.get('customer_name')}\n"
                f"Phone: {phone}\n"
                f"Email: {parameters.get('email', 'Not provided')}\n"
                f"Service Date: {parameters.get('service_date', 'Not specified')}\n"
                f"Service ID: {parameters.get('service_id', 'Not specified')}\n\n"
                f"Complaint Details:\n{parameters.get('complaint_details')}"
            ),
            "priority": "1",  # URGENT priority (1 = highest)
        }
        
        lead_id = await odoo_client.create("crm.lead", lead_data)
        
        # Try to add "Escalation" or "Complaint" tag
        try:
            tags = await odoo_client.search_read(
                "crm.tag",
                [("name", "in", ["Escalation", "Complaint", "URGENT"])],
                fields=["id"],
                limit=1,
            )
            if tags:
                await odoo_client.write("crm.lead", [lead_id], {
                    "tag_ids": [(6, 0, [tags[0]["id"]])]
                })
        except Exception as e:
            handler.logger.warning(f"Failed to add escalation tag: {e}")
        
        handler.logger.info(f"Created escalation ticket {lead_id} with URGENT priority")
        
        # Send immediate notifications to management
        settings = get_settings()
        complaint_details = parameters.get("complaint_details", "")
        customer_name = parameters.get("customer_name", "Customer")
        
        # Build email notification
        email_subject = f"🚨 URGENT: Customer Complaint - {customer_name}"
        email_body_html = (
            f"<h2 style='color: #d32f2f;'>🚨 URGENT: Customer Complaint/Escalation</h2>"
            f"<div style='background-color: #ffebee; border-left: 4px solid #d32f2f; padding: 15px; margin: 15px 0;'>"
            f"<p><strong>Customer:</strong> {customer_name}</p>"
            f"<p><strong>Phone:</strong> {phone}</p>"
            f"<p><strong>Email:</strong> {parameters.get('email', 'Not provided')}</p>"
            f"<p><strong>Service Date:</strong> {parameters.get('service_date', 'Not specified')}</p>"
            f"<p><strong>Service ID:</strong> {parameters.get('service_id', 'Not specified')}</p>"
            f"</div>"
            f"<h3>Complaint Details:</h3>"
            f"<p>{complaint_details}</p>"
            f"<p><strong>Odoo Lead ID:</strong> <a href='https://www.hvacrfinest.com/web#id={lead_id}&model=crm.lead&view_type=form'>#{lead_id}</a></p>"
            f"<p><strong>Priority:</strong> URGENT</p>"
        )
        email_body_text = (
            f"URGENT: Customer Complaint/Escalation\n\n"
            f"Customer: {customer_name}\n"
            f"Phone: {phone}\n"
            f"Email: {parameters.get('email', 'Not provided')}\n"
            f"Service Date: {parameters.get('service_date', 'Not specified')}\n"
            f"Service ID: {parameters.get('service_id', 'Not specified')}\n\n"
            f"Complaint Details:\n{complaint_details}\n\n"
            f"Odoo Lead ID: {lead_id}\n"
            f"Priority: URGENT"
        )
        
        # Send emails to Junior and Linda
        email_service = create_email_service_from_settings()
        if email_service:
            recipients = []
            if settings.DISPATCH_EMAIL:
                recipients.append(("Dispatch/Junior", settings.DISPATCH_EMAIL))
            if settings.LINDA_EMAIL:
                recipients.append(("Linda", settings.LINDA_EMAIL))
            
            for name, email_addr in recipients:
                try:
                    email_service.send_email(
                        to=email_addr,
                        subject=email_subject,
                        body_html=email_body_html,
                        body_text=email_body_text,
                    )
                    handler.logger.info(f"Sent complaint email to {name} ({email_addr})")
                except Exception as e:
                    handler.logger.error(f"Failed to send complaint email to {name}: {e}")
        else:
            handler.logger.warning("Email service not configured, skipping email notifications")
        
        # Send SMS to Junior and Linda (if phone numbers available in settings)
        sms_client = create_twilio_client_from_settings()
        if sms_client:
            sms_body = (
                f"🚨 URGENT: Customer complaint from {customer_name}. "
                f"Phone: {phone}. "
                f"Lead ID: {lead_id}. "
                f"Please review in Odoo immediately."
            )
            
            # Try to get phone numbers from settings (may need to be added)
            # For now, we'll log that SMS should be sent but phone numbers need to be configured
            # In production, add JUNIOR_PHONE and LINDA_PHONE to settings
            if hasattr(settings, "JUNIOR_PHONE") and settings.JUNIOR_PHONE:
                try:
                    await sms_client.send_sms(to=settings.JUNIOR_PHONE, body=sms_body)
                    handler.logger.info(f"Sent complaint SMS to Junior ({settings.JUNIOR_PHONE})")
                except Exception as e:
                    handler.logger.error(f"Failed to send complaint SMS to Junior: {e}")
            
            if hasattr(settings, "LINDA_PHONE") and settings.LINDA_PHONE:
                try:
                    await sms_client.send_sms(to=settings.LINDA_PHONE, body=sms_body)
                    handler.logger.info(f"Sent complaint SMS to Linda ({settings.LINDA_PHONE})")
                except Exception as e:
                    handler.logger.error(f"Failed to send complaint SMS to Linda: {e}")
        else:
            handler.logger.warning("SMS service not configured, skipping SMS notifications")
        
        # Format professional response (avoiding prohibited phrases)
        message = (
            "I understand you're frustrated, and I'm documenting this complaint. "
            "Our management team will contact you within 24 hours to address your concerns. "
            "Would you like me to have someone call you back today?"
        )
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "escalation_ticket_id": lead_id,
                "management_contact_timeline": "24 hours",
                "callback_offered": True,
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
