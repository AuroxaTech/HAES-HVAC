"""
HAES HVAC - Twilio SMS Integration

Sends SMS notifications via Twilio REST API using httpx (no SDK dependency).
Supports dry-run mode and test number override for safe staging testing.
"""

import base64
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Twilio API base URL
TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class TwilioSMSError(Exception):
    """Exception raised when SMS sending fails."""
    pass


class TwilioSMSClient:
    """
    Twilio SMS client using httpx.
    
    Supports:
    - Sending SMS via REST API
    - Dry-run mode (logs instead of sending)
    - Test number override for staging
    """
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        dry_run: bool = False,
        test_to_number: str | None = None,
    ):
        """
        Initialize the client.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: From phone number (Twilio number)
            dry_run: If True, log instead of sending
            test_to_number: Override recipient number for testing
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.dry_run = dry_run
        self.test_to_number = test_to_number
        
        # Build auth header
        credentials = f"{account_sid}:{auth_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"
    
    @property
    def messages_url(self) -> str:
        """Get the Messages endpoint URL."""
        return f"{TWILIO_API_BASE}/Accounts/{self.account_sid}/Messages.json"
    
    async def send_sms(
        self,
        to: str,
        body: str,
        status_callback: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number (E.164 format)
            body: Message body (max 1600 chars)
            status_callback: Optional webhook URL for delivery status
            
        Returns:
            Dict with message_sid and status on success
            
        Raises:
            TwilioSMSError: If sending fails
        """
        # Override to number for testing
        actual_to = self.test_to_number if self.test_to_number else to
        
        # Dry run mode
        if self.dry_run:
            logger.info(f"[DRY RUN] SMS to {actual_to}: {body}")
            return {
                "message_sid": "dry_run_sid",
                "status": "dry_run",
                "to": actual_to,
                "body_preview": body[:50],
            }
        
        # Build request payload
        payload = {
            "To": actual_to,
            "From": self.from_number,
            "Body": body,
        }
        if status_callback:
            payload["StatusCallback"] = status_callback
        
        # Send request
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.messages_url,
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    content=urlencode(payload),
                    timeout=30.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"SMS sent: {data.get('sid')} to {actual_to}")
                    return {
                        "message_sid": data.get("sid"),
                        "status": data.get("status"),
                        "to": actual_to,
                    }
                else:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("message", response.text)
                    logger.error(f"Twilio SMS failed: {response.status_code} - {error_msg}")
                    raise TwilioSMSError(f"SMS failed: {response.status_code} - {error_msg}")
                    
            except httpx.RequestError as e:
                logger.error(f"Twilio request error: {e}")
                raise TwilioSMSError(f"Request error: {e}")


def create_twilio_client_from_settings() -> TwilioSMSClient | None:
    """
    Create a Twilio SMS client from settings.
    
    Returns:
        TwilioSMSClient if configured, None if credentials missing
    """
    settings = get_settings()
    
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials not configured, SMS disabled")
        return None
    
    if not settings.TWILIO_PHONE_NUMBER:
        logger.warning("Twilio phone number not configured, SMS disabled")
        return None
    
    return TwilioSMSClient(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        from_number=settings.TWILIO_PHONE_NUMBER,
        dry_run=settings.TWILIO_DRY_RUN,
        test_to_number=settings.TWILIO_TEST_TO_NUMBER or None,
    )


# =============================================================================
# SMS Message Templates
# =============================================================================


def build_emergency_confirmation_sms(
    customer_name: str | None,
    tech_name: str | None,
    eta_hours_min: float,
    eta_hours_max: float,
    total_fee: float,
) -> str:
    """
    Build emergency service confirmation SMS.
    
    Args:
        customer_name: Customer name (for greeting)
        tech_name: Assigned technician name
        eta_hours_min: Minimum ETA in hours
        eta_hours_max: Maximum ETA in hours
        total_fee: Base diagnostic fee
        
    Returns:
        SMS message body
    """
    greeting = f"Hi {customer_name}, " if customer_name else ""
    tech_info = f"Tech {tech_name}" if tech_name else "A technician"
    
    return (
        f"HVAC-R Finest: {greeting}Emergency request received! "
        f"{tech_info} has been assigned. "
        f"ETA: {eta_hours_min:.1f}-{eta_hours_max:.1f} hours. "
        f"Base diagnostic: ${total_fee:.2f}. "
        f"We'll call before arrival. Reply STOP to opt out."
    )


def build_service_confirmation_sms(
    customer_name: str | None,
    appointment_date: str | None = None,
    appointment_time: str | None = None,
    tech_name: str | None = None,
    service_type: str | None = None,
    is_same_day: bool = False,
) -> str:
    """
    Build standard service/appointment confirmation SMS.
    
    Args:
        customer_name: Customer name
        appointment_date: Appointment date (e.g., "Tuesday, January 14")
        appointment_time: Appointment time (e.g., "2:00 PM")
        tech_name: Assigned technician name
        service_type: Type of service
        is_same_day: Whether same-day service was requested
        
    Returns:
        SMS message body
    """
    greeting = f"Hi {customer_name}, " if customer_name else ""
    
    # Build appointment details if provided
    appointment_info = ""
    if appointment_date and appointment_time:
        appointment_info = f"Your appointment is scheduled for {appointment_date} at {appointment_time}."
        if tech_name:
            appointment_info += f" Technician: {tech_name}."
    elif is_same_day:
        appointment_info = "We'll reach out today to confirm your appointment."
    else:
        appointment_info = "We'll reach out soon to confirm your appointment."
    
    service_info = f" Service: {service_type}." if service_type else ""
    
    return (
        f"HVAC-R Finest: {greeting}{appointment_info}{service_info} "
        f"Reply CONFIRM or CANCEL. Questions? Call (972) 372-4458. Reply STOP to opt out."
    )


def build_reschedule_confirmation_sms(
    customer_name: str | None,
    new_time_str: str,
    tech_name: str | None,
) -> str:
    """
    Build appointment reschedule confirmation SMS.
    
    Args:
        customer_name: Customer name
        new_time_str: Formatted new appointment time (e.g., "Tuesday, January 14 at 2:00 PM")
        tech_name: Assigned technician name
        
    Returns:
        SMS message body
    """
    greeting = f"Hi {customer_name}, " if customer_name else ""
    tech_info = f" with {tech_name}" if tech_name else ""
    
    return (
        f"HVAC-R Finest: {greeting}Your appointment has been rescheduled to {new_time_str}{tech_info}. "
        f"Reply CONFIRM or call (972) 372-4458 if you need to change it. Reply STOP to opt out."
    )


# =============================================================================
# Convenience Functions
# =============================================================================


async def send_emergency_sms(
    to_phone: str,
    customer_name: str | None,
    tech_name: str | None,
    eta_hours_min: float,
    eta_hours_max: float,
    total_fee: float,
) -> dict[str, Any]:
    """
    Send emergency service confirmation SMS.
    
    Handles client creation and error handling gracefully.
    
    Returns:
        Dict with status and message_sid on success, or error info
    """
    settings = get_settings()
    
    # Check feature flag
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping SMS")
        return {"status": "disabled", "reason": "feature_flag"}
    
    # Create client
    client = create_twilio_client_from_settings()
    if not client:
        return {"status": "disabled", "reason": "not_configured"}
    
    # Build message
    body = build_emergency_confirmation_sms(
        customer_name=customer_name,
        tech_name=tech_name,
        eta_hours_min=eta_hours_min,
        eta_hours_max=eta_hours_max,
        total_fee=total_fee,
    )
    
    # Send
    try:
        result = await client.send_sms(to=to_phone, body=body)
        return {"status": "sent", **result}
    except TwilioSMSError as e:
        logger.error(f"Failed to send emergency SMS: {e}")
        return {"status": "failed", "error": str(e)}


def build_incomplete_call_sms() -> str:
    """
    Build SMS message for incomplete/dropped calls.
    
    Returns:
        SMS message body
    """
    return (
        "HVAC-R Finest: We lost connection, please call back at (972) 372-4458. "
        "We'd love to help! Reply STOP to opt out."
    )


async def send_incomplete_call_sms(
    to_phone: str,
) -> dict[str, Any]:
    """
    Send SMS fallback for incomplete/dropped calls.
    
    Returns:
        Dict with status and message_sid on success, or error info
    """
    settings = get_settings()
    
    # Check feature flag
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping incomplete call SMS")
        return {"status": "disabled", "reason": "feature_flag"}
    
    # Create client
    client = create_twilio_client_from_settings()
    if not client:
        return {"status": "disabled", "reason": "not_configured"}
    
    # Build message
    body = build_incomplete_call_sms()
    
    # Send
    try:
        result = await client.send_sms(to=to_phone, body=body)
        logger.info(f"Sent incomplete call SMS to {to_phone}")
        return {"status": "sent", **result}
    except TwilioSMSError as e:
        logger.error(f"Failed to send incomplete call SMS: {e}")
        return {"status": "failed", "error": str(e)}


def build_appointment_reminder_sms(
    customer_name: str | None,
    appointment_date: str | None = None,
    appointment_time: str | None = None,
    tech_name: str | None = None,
    service_type: str | None = None,
) -> str:
    """
    Build appointment reminder SMS (sent 2 hours before appointment).
    
    Args:
        customer_name: Customer name
        appointment_date: Appointment date (e.g., "Tuesday, January 14")
        appointment_time: Appointment time (e.g., "2:00 PM")
        tech_name: Assigned technician name
        service_type: Type of service
        
    Returns:
        SMS message body
    """
    greeting = f"Hi {customer_name}, " if customer_name else ""
    
    appointment_info = ""
    if appointment_date and appointment_time:
        appointment_info = f"Your HVACR FINEST appointment is in 2 hours ({appointment_date} at {appointment_time})."
    else:
        appointment_info = "Your HVACR FINEST appointment is in 2 hours."
    
    tech_info = f" Technician: {tech_name}." if tech_name else ""
    service_info = f" Service: {service_type}." if service_type else ""
    
    return (
        f"HVAC-R Finest: {greeting}{appointment_info}{tech_info}{service_info} "
        f"Reply to reschedule or call (972) 372-4458. Reply STOP to opt out."
    )


async def send_appointment_reminder_sms(
    to_phone: str,
    customer_name: str | None,
    appointment_date: str | None = None,
    appointment_time: str | None = None,
    tech_name: str | None = None,
    service_type: str | None = None,
) -> dict[str, Any]:
    """
    Send appointment reminder SMS (2 hours before appointment).
    
    Returns:
        Dict with status and message_sid on success, or error info
    """
    settings = get_settings()
    
    # Check feature flag
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping reminder SMS")
        return {"status": "disabled", "reason": "feature_flag"}
    
    # Create client
    client = create_twilio_client_from_settings()
    if not client:
        return {"status": "disabled", "reason": "not_configured"}
    
    # Build message
    body = build_appointment_reminder_sms(
        customer_name=customer_name,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        tech_name=tech_name,
        service_type=service_type,
    )
    
    # Send
    try:
        result = await client.send_sms(to=to_phone, body=body)
        logger.info(f"Sent appointment reminder SMS to {to_phone}")
        return {"status": "sent", **result}
    except TwilioSMSError as e:
        logger.error(f"Failed to send appointment reminder SMS: {e}")
        return {"status": "failed", "error": str(e)}


async def send_service_confirmation_sms(
    to_phone: str,
    customer_name: str | None,
    appointment_date: str | None = None,
    appointment_time: str | None = None,
    tech_name: str | None = None,
    service_type: str | None = None,
    is_same_day: bool = False,
) -> dict[str, Any]:
    """
    Send standard service/appointment confirmation SMS.
    
    This function should be called immediately after appointment creation.
    
    Args:
        to_phone: Customer phone number
        customer_name: Customer name
        appointment_date: Appointment date (e.g., "Tuesday, January 14")
        appointment_time: Appointment time (e.g., "2:00 PM")
        tech_name: Assigned technician name
        service_type: Type of service
        is_same_day: Whether same-day service was requested
    
    Returns:
        Dict with status and message_sid on success, or error info
    """
    settings = get_settings()
    
    # Feature flag check (reuse emergency flag for now)
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping SMS")
        return {"status": "disabled", "reason": "feature_flag"}
    
    client = create_twilio_client_from_settings()
    if not client:
        return {"status": "disabled", "reason": "not_configured"}
    
    body = build_service_confirmation_sms(
        customer_name=customer_name,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        tech_name=tech_name,
        service_type=service_type,
        is_same_day=is_same_day,
    )
    
    try:
        result = await client.send_sms(to=to_phone, body=body)
        logger.info(f"Sent appointment confirmation SMS to {to_phone} for appointment on {appointment_date or 'TBD'}")
        return {"status": "sent", **result}
    except TwilioSMSError as e:
        logger.error(f"Failed to send service SMS: {e}")
        return {"status": "failed", "error": str(e)}


def build_reschedule_confirmation_sms(
    customer_name: str | None,
    new_time_str: str,
    tech_name: str | None,
) -> str:
    """
    Build appointment reschedule confirmation SMS.
    
    Args:
        customer_name: Customer name
        new_time_str: Formatted new appointment time (e.g., "Tuesday, January 14 at 2:00 PM")
        tech_name: Assigned technician name
        
    Returns:
        SMS message body
    """
    greeting = f"Hi {customer_name}, " if customer_name else ""
    tech_info = f" with {tech_name}" if tech_name else ""
    
    return (
        f"HVAC-R Finest: {greeting}Your appointment has been rescheduled to {new_time_str}{tech_info}. "
        f"Reply CONFIRM or call (972) 372-4458 if you need to change it. Reply STOP to opt out."
    )


async def send_reschedule_confirmation_sms(
    to_phone: str,
    customer_name: str | None,
    new_time_str: str,
    tech_name: str | None,
) -> dict[str, Any]:
    """
    Send appointment reschedule confirmation SMS.
    
    Returns:
        Dict with status and message_sid on success, or error info
    """
    settings = get_settings()
    
    # Feature flag check
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping SMS")
        return {"status": "disabled", "reason": "feature_flag"}
    
    client = create_twilio_client_from_settings()
    if not client:
        return {"status": "disabled", "reason": "not_configured"}
    
    body = build_reschedule_confirmation_sms(
        customer_name=customer_name,
        new_time_str=new_time_str,
        tech_name=tech_name,
    )
    
    try:
        result = await client.send_sms(to=to_phone, body=body)
        return {"status": "sent", **result}
    except TwilioSMSError as e:
        logger.error(f"Failed to send reschedule SMS: {e}")
        return {"status": "failed", "error": str(e)}


def build_membership_enrollment_sms(
    customer_name: str | None,
    plan_name: str,
    annual_price: float,
    payment_link: str,
) -> str:
    """
    Build SMS message for membership enrollment with contract and payment link.
    
    Returns:
        SMS message body
    """
    greeting = f"Hi {customer_name}," if customer_name else "Hello,"
    
    return (
        f"{greeting} Thank you for enrolling in {plan_name} with HVAC-R Finest! "
        f"Annual cost: ${annual_price:.0f}. "
        f"VIP benefits include priority scheduling, discounted rates, annual tune-ups, and extended warranty. "
        f"Complete enrollment: {payment_link} "
        f"Reply STOP to opt out."
    )
