"""
HAES HVAC - Send Notification Tool

Send both SMS and email notifications in one tool call.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.integrations.twilio_sms import create_twilio_client_from_settings
from src.integrations.email_notifications import create_email_service_from_settings

logger = logging.getLogger(__name__)


def _is_success_status(status: str | None) -> bool:
    return status in {"sent", "dry_run"}


def _build_notification_html(customer_name: str, message: str) -> str:
    greeting = f"Hi {customer_name}," if customer_name else "Hello,"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: Arial, sans-serif; color: #222; line-height: 1.5; }}
        .card {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <p>{greeting}</p>
        <p>{message}</p>
        <p>Thank you,<br>HVAC-R Finest</p>
      </div>
    </body>
    </html>
    """.strip()


async def handle_send_notification(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle send_notification tool call.

    Parameters:
        - customer_name (optional): Friendly recipient name for message intro
        - phone (required): Recipient phone number for SMS
        - email (required): Recipient email address
        - message (required): Shared message content for both SMS and email text
        - email_subject (optional): Email subject line
    """
    handler = BaseToolHandler("send_notification")

    required = ["phone", "email", "message"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    if not is_valid:
        return handler.format_needs_human_response(
            "I can send both SMS and email notifications once I have the missing details.",
            missing_fields=missing,
            intent_acknowledged=False,
        )

    phone = handler.normalize_phone(parameters.get("phone"))
    email = handler.normalize_email(parameters.get("email"))
    if not phone or not email:
        invalid_fields: list[str] = []
        if not phone:
            invalid_fields.append("phone")
        if not email:
            invalid_fields.append("email")
        return handler.format_needs_human_response(
            "I can send notifications, but I need valid phone and email details.",
            missing_fields=invalid_fields,
            intent_acknowledged=False,
        )

    customer_name = (parameters.get("customer_name") or "").strip()
    base_message = str(parameters.get("message") or "").strip()
    email_subject = (
        str(parameters.get("email_subject")).strip()
        if parameters.get("email_subject")
        else "HVAC-R Finest Notification"
    )

    sms_body = f"Hi {customer_name}, {base_message}" if customer_name else base_message
    email_text = sms_body
    email_html = _build_notification_html(customer_name=customer_name, message=base_message)

    sms_result: dict[str, Any] = {"status": "disabled", "reason": "not_configured"}
    email_result: dict[str, Any] = {"status": "disabled", "reason": "not_configured"}

    try:
        sms_client = create_twilio_client_from_settings()
        if sms_client:
            sms_result = await sms_client.send_sms(to=phone, body=sms_body)
        else:
            logger.warning("send_notification: Twilio client is not configured")
    except Exception as sms_err:
        logger.error(f"send_notification: SMS send failed: {sms_err}")
        sms_result = {"status": "failed", "error": str(sms_err)}

    try:
        email_service = create_email_service_from_settings()
        if email_service:
            email_result = email_service.send_email(
                to=email,
                subject=email_subject,
                body_html=email_html,
                body_text=email_text,
            )
        else:
            logger.warning("send_notification: Email service is not configured")
    except Exception as email_err:
        logger.error(f"send_notification: email send failed: {email_err}")
        email_result = {"status": "failed", "error": str(email_err)}

    sms_ok = _is_success_status(sms_result.get("status"))
    email_ok = _is_success_status(email_result.get("status"))

    response_data = {
        "phone": phone,
        "email": email,
        "sms": sms_result,
        "email_result": email_result,
    }

    if sms_ok and email_ok:
        return handler.format_success_response(
            "Notification sent successfully by SMS and email.",
            data=response_data,
        )

    if sms_ok or email_ok:
        return handler.format_needs_human_response(
            "I sent one notification channel, but the other channel needs follow-up.",
            data=response_data,
            intent_acknowledged=True,
        )

    return ToolResponse(
        speak="I could not send the notification right now. Please try again or have a representative follow up.",
        action="error",
        data=response_data,
    )
