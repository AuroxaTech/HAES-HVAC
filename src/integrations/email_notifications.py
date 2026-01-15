"""
HAES HVAC - Email Notification Service

Sends email notifications via SMTP using Python's built-in smtplib.
Supports dry-run mode and test email override for safe staging testing.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Exception raised when email sending fails."""
    pass


class EmailNotificationService:
    """
    Email notification service using SMTP.
    
    Supports:
    - Sending HTML/text emails via SMTP
    - Dry-run mode (logs instead of sending)
    - Test email override for staging
    - TLS/STARTTLS encryption
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True,
        dry_run: bool = False,
        test_to_email: str | None = None,
    ):
        """
        Initialize the email service.
        
        Args:
            host: SMTP server hostname
            port: SMTP server port (usually 587 for STARTTLS, 465 for SSL)
            username: SMTP username
            password: SMTP password
            from_email: From email address
            use_tls: Use STARTTLS (for port 587) or SSL (for port 465)
            dry_run: If True, log instead of sending
            test_to_email: Override recipient email for testing
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
        self.dry_run = dry_run
        self.test_to_email = test_to_email
    
    def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email message.
        
        Args:
            to: Recipient email address(es) (string or list of strings)
            subject: Email subject line
            body_html: HTML body (preferred if provided)
            body_text: Plain text body (fallback if no HTML)
            reply_to: Optional Reply-To header
            
        Returns:
            Dict with status and message_id on success
            
        Raises:
            EmailError: If sending fails
        """
        # Override recipient for testing
        actual_to = self.test_to_email if self.test_to_email else to
        if isinstance(actual_to, str):
            actual_to = [actual_to]
        
        # Ensure at least one body format
        if not body_html and not body_text:
            body_text = ""  # Empty email
        
        # Dry run mode
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Email to {', '.join(actual_to)}: "
                f"Subject: {subject}\n"
                f"Body preview: {(body_html or body_text)[:100]}..."
            )
            return {
                "status": "dry_run",
                "to": actual_to,
                "subject": subject,
                "message_id": "dry_run_message_id",
            }
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_email
        msg["To"] = ", ".join(actual_to)
        msg["Subject"] = subject
        
        if reply_to:
            msg["Reply-To"] = reply_to
        
        # Add body parts
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))
        
        # Send via SMTP
        try:
            if self.use_tls and self.port == 587:
                # STARTTLS (most common)
                server = smtplib.SMTP(self.host, self.port, timeout=30)
                server.starttls()
            elif self.port == 465:
                # SSL
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                # Plain SMTP (not recommended)
                server = smtplib.SMTP(self.host, self.port, timeout=30)
                if self.use_tls:
                    server.starttls()
            
            # Authenticate
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Send message
            text = msg.as_string()
            server.sendmail(self.from_email, actual_to, text)
            server.quit()
            
            logger.info(f"Email sent: '{subject}' to {', '.join(actual_to)}")
            return {
                "status": "sent",
                "to": actual_to,
                "subject": subject,
                "message_id": msg["Message-ID"] if "Message-ID" in msg else "sent",
            }
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            raise EmailError(f"SMTP error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise EmailError(f"Email send failed: {e}")


def create_email_service_from_settings() -> EmailNotificationService | None:
    """
    Create an EmailNotificationService from settings.
    
    Returns:
        EmailNotificationService if configured, None if credentials missing
    """
    settings = get_settings()
    
    if not settings.SMTP_HOST:
        logger.warning("SMTP_HOST not configured, email disabled")
        return None
    
    if not settings.SMTP_FROM_EMAIL:
        logger.warning("SMTP_FROM_EMAIL not configured, email disabled")
        return None
    
    return EmailNotificationService(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        from_email=settings.SMTP_FROM_EMAIL,
        use_tls=settings.SMTP_USE_TLS,
        dry_run=settings.SMTP_DRY_RUN,
        test_to_email=settings.SMTP_TEST_TO_EMAIL or None,
    )


# =============================================================================
# Email Message Templates
# =============================================================================


def build_emergency_notification_email(
    customer_name: str | None,
    tech_name: str | None,
    eta_hours_min: float,
    eta_hours_max: float,
    total_fee: float,
    lead_id: int | None = None,
    address: str | None = None,
    phone: str | None = None,
) -> tuple[str, str]:
    """
    Build emergency service notification email (HTML + text versions).
    
    Returns:
        Tuple of (html_body, text_body)
    """
    greeting = f"Hi {customer_name}," if customer_name else "Hello,"
    tech_info = f"Technician {tech_name}" if tech_name else "A technician"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #d32f2f; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .emergency {{ background-color: #ffebee; border-left: 4px solid #d32f2f; padding: 15px; margin: 15px 0; }}
            .info-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>HVAC-R Finest</h1>
                <h2>🚨 Emergency Service Request</h2>
            </div>
            <div class="content">
                <p>{greeting}</p>
                
                <div class="emergency">
                    <h3>Emergency Service Confirmation</h3>
                    <p>Your emergency service request has been received and prioritized.</p>
                </div>
                
                <div class="info-box">
                    <h3>Service Details</h3>
                    <p><strong>Assigned Technician:</strong> {tech_info}</p>
                    <p><strong>Estimated Arrival:</strong> {eta_hours_min:.1f} to {eta_hours_max:.1f} hours</p>
                    <p><strong>Base Diagnostic Fee:</strong> ${total_fee:.2f} (includes emergency premiums)</p>
                    {"<p><strong>Service Address:</strong> " + address + "</p>" if address else ""}
                    {"<p><strong>Contact Phone:</strong> " + phone + "</p>" if phone else ""}
                    {"<p><strong>Lead ID:</strong> #" + str(lead_id) + "</p>" if lead_id else ""}
                </div>
                
                <div class="info-box">
                    <h3>What to Expect</h3>
                    <ul>
                        <li>Our technician will call you before arrival</li>
                        <li>Please ensure someone is available at the service address</li>
                        <li>Final repair costs will depend on the specific issue found</li>
                    </ul>
                </div>
                
                <p>If you have any questions or need to update your request, please call us at <strong>(972) 372-4458</strong>.</p>
            </div>
            <div class="footer">
                <p>HVAC-R Finest | Licensed & Insured</p>
                <p>This is an automated confirmation email. Please do not reply directly to this message.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    HVAC-R Finest - Emergency Service Request Confirmation
    
    {greeting}
    
    Your emergency service request has been received and prioritized.
    
    SERVICE DETAILS:
    - Assigned Technician: {tech_info}
    - Estimated Arrival: {eta_hours_min:.1f} to {eta_hours_max:.1f} hours
    - Base Diagnostic Fee: ${total_fee:.2f} (includes emergency premiums)
    {f"- Service Address: {address}" if address else ""}
    {f"- Contact Phone: {phone}" if phone else ""}
    {f"- Lead ID: #{lead_id}" if lead_id else ""}
    
    WHAT TO EXPECT:
    - Our technician will call you before arrival
    - Please ensure someone is available at the service address
    - Final repair costs will depend on the specific issue found
    
    Questions? Call (972) 372-4458
    
    ---
    HVAC-R Finest | Licensed & Insured
    This is an automated confirmation email.
    """
    
    return html_body.strip(), text_body.strip()


def build_service_confirmation_email(
    customer_name: str | None,
    is_same_day: bool = False,
    appointment_date: str | None = None,
) -> tuple[str, str]:
    """
    Build standard service confirmation email.
    
    Returns:
        Tuple of (html_body, text_body)
    """
    greeting = f"Hi {customer_name}," if customer_name else "Hello,"
    timing = appointment_date or ("today" if is_same_day else "soon")
    
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
            .info-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>HVAC-R Finest</h1>
                <h2>Service Request Confirmation</h2>
            </div>
            <div class="content">
                <p>{greeting}</p>
                <p>Your service request has been received! We'll reach out {timing} to confirm your appointment details.</p>
                
                <div class="info-box">
                    <h3>Next Steps</h3>
                    <ul>
                        <li>A team member will contact you to confirm appointment time</li>
                        <li>You'll receive a reminder before your scheduled visit</li>
                        <li>If you need to make changes, call us at (972) 372-4458</li>
                    </ul>
                </div>
                
                <p>Thank you for choosing HVAC-R Finest!</p>
            </div>
            <div class="footer">
                <p>HVAC-R Finest | Licensed & Insured</p>
                <p>Questions? Call (972) 372-4458</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    HVAC-R Finest - Service Request Confirmation
    
    {greeting}
    
    Your service request has been received! We'll reach out {timing} to confirm your appointment details.
    
    NEXT STEPS:
    - A team member will contact you to confirm appointment time
    - You'll receive a reminder before your scheduled visit
    - If you need to make changes, call us at (972) 372-4458
    
    Thank you for choosing HVAC-R Finest!
    
    ---
    HVAC-R Finest | Licensed & Insured
    Questions? Call (972) 372-4458
    """
    
    return html_body.strip(), text_body.strip()


# =============================================================================
# Convenience Functions
# =============================================================================


async def send_emergency_email(
    to_email: str,
    customer_name: str | None,
    tech_name: str | None,
    eta_hours_min: float,
    eta_hours_max: float,
    total_fee: float,
    lead_id: int | None = None,
    address: str | None = None,
    phone: str | None = None,
) -> dict[str, Any]:
    """
    Send emergency service confirmation email.
    
    Handles service creation and error handling gracefully.
    
    Returns:
        Dict with status and message_id on success, or error info
    """
    settings = get_settings()
    
    # Check feature flag (reuse emergency SMS flag for now)
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping email")
        return {"status": "disabled", "reason": "feature_flag"}
    
    # Create service
    service = create_email_service_from_settings()
    if not service:
        return {"status": "disabled", "reason": "not_configured"}
    
    # Build message
    html_body, text_body = build_emergency_notification_email(
        customer_name=customer_name,
        tech_name=tech_name,
        eta_hours_min=eta_hours_min,
        eta_hours_max=eta_hours_max,
        total_fee=total_fee,
        lead_id=lead_id,
        address=address,
        phone=phone,
    )
    
    # Send email (synchronous operation - typically fast < 1s, acceptable for async context)
    try:
        result = service.send_email(
            to=to_email,
            subject="🚨 Emergency Service Request - HVAC-R Finest",
            body_html=html_body,
            body_text=text_body,
        )
        return {"status": "sent", **result}
    except EmailError as e:
        logger.error(f"Failed to send emergency email: {e}")
        return {"status": "failed", "error": str(e)}


def build_emergency_staff_notification_email(
    customer_name: str | None,
    address: str | None,
    phone: str | None,
    tech_name: str | None,
    eta_hours_min: float,
    eta_hours_max: float,
    total_fee: float,
    lead_id: int | None = None,
    emergency_reason: str | None = None,
) -> tuple[str, str]:
    """
    Build emergency staff notification email (HTML + text versions).
    
    This email is sent to Dispatch, Linda, and assigned technician.
    
    Returns:
        Tuple of (html_body, text_body)
    """
    customer_info = customer_name or "Unknown"
    tech_info = f"Technician {tech_name}" if tech_name else "Unassigned"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #d32f2f; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .emergency {{ background-color: #ffebee; border-left: 4px solid #d32f2f; padding: 15px; margin: 15px 0; }}
            .info-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚨 EMERGENCY SERVICE REQUEST</h1>
                <h2>HVAC-R Finest</h2>
            </div>
            <div class="content">
                <div class="emergency">
                    <h3>Action Required: Emergency Service Request</h3>
                    {f"<p><strong>Reason:</strong> {emergency_reason}</p>" if emergency_reason else ""}
                </div>
                
                <div class="info-box">
                    <h3>Customer Information</h3>
                    <p><strong>Name:</strong> {customer_info}</p>
                    {f"<p><strong>Address:</strong> {address}</p>" if address else ""}
                    {f"<p><strong>Phone:</strong> {phone}</p>" if phone else ""}
                    {f"<p><strong>Lead ID:</strong> <a href='https://www.hvacrfinest.com/web#id={lead_id}&model=crm.lead&view_type=form'>#{lead_id}</a></p>" if lead_id else ""}
                </div>
                
                <div class="info-box">
                    <h3>Service Details</h3>
                    <p><strong>Assigned Technician:</strong> {tech_info}</p>
                    <p><strong>Estimated Arrival:</strong> {eta_hours_min:.1f} to {eta_hours_max:.1f} hours</p>
                    <p><strong>Base Diagnostic Fee:</strong> ${total_fee:.2f} (includes emergency premiums)</p>
                </div>
                
                <div class="info-box">
                    <h3>Next Steps</h3>
                    <ul>
                        <li>Review customer information and emergency details</li>
                        <li>Confirm technician assignment and ETA</li>
                        <li>Monitor service progress in Odoo CRM</li>
                        <li>Follow up with customer if needed</li>
                    </ul>
                </div>
                
                <p><strong>This is an automated notification from the HAES system.</strong></p>
            </div>
            <div class="footer">
                <p>HVAC-R Finest | Emergency Dispatch System</p>
                <p>Do not reply to this automated message</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    🚨 EMERGENCY SERVICE REQUEST - HVAC-R Finest
    
    Action Required: Emergency Service Request
    
    {f"Reason: {emergency_reason}" if emergency_reason else ""}
    
    CUSTOMER INFORMATION:
    - Name: {customer_info}
    {f"- Address: {address}" if address else ""}
    {f"- Phone: {phone}" if phone else ""}
    {f"- Lead ID: #{lead_id}" if lead_id else ""}
    
    SERVICE DETAILS:
    - Assigned Technician: {tech_info}
    - Estimated Arrival: {eta_hours_min:.1f} to {eta_hours_max:.1f} hours
    - Base Diagnostic Fee: ${total_fee:.2f} (includes emergency premiums)
    
    NEXT STEPS:
    - Review customer information and emergency details
    - Confirm technician assignment and ETA
    - Monitor service progress in Odoo CRM
    - Follow up with customer if needed
    
    This is an automated notification from the HAES system.
    
    ---
    HVAC-R Finest | Emergency Dispatch System
    Do not reply to this automated message
    """
    
    return html_body.strip(), text_body.strip()


async def send_emergency_staff_notification(
    lead_id: int | None,
    customer_name: str | None,
    address: str | None,
    phone: str | None,
    tech_id: str | None,
    tech_name: str | None,
    eta_hours_min: float,
    eta_hours_max: float,
    total_fee: float,
    emergency_reason: str | None = None,
) -> dict[str, Any]:
    """
    Send emergency notification emails to Dispatch, Linda, and assigned technician.
    
    Returns:
        Dict with status and sent emails info
    """
    settings = get_settings()
    
    # Check if email is configured
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.debug("SMTP not configured, skipping staff email notifications")
        return {"status": "disabled", "reason": "not_configured"}
    
    # Create email service
    try:
        service = create_email_service_from_settings()
        if not service:
            return {"status": "disabled", "reason": "not_configured"}
    except Exception as e:
        logger.warning(f"Failed to create email service: {e}")
        return {"status": "error", "error": str(e)}
    
    # Build message
    html_body, text_body = build_emergency_staff_notification_email(
        customer_name=customer_name,
        address=address,
        phone=phone,
        tech_name=tech_name,
        eta_hours_min=eta_hours_min,
        eta_hours_max=eta_hours_max,
        total_fee=total_fee,
        lead_id=lead_id,
        emergency_reason=emergency_reason,
    )
    
    # Collect recipients
    recipients = []
    sent_results = {}
    
    # Add Dispatch email
    if settings.DISPATCH_EMAIL:
        recipients.append(("Dispatch", settings.DISPATCH_EMAIL))
    
    # Add Linda email
    if settings.LINDA_EMAIL:
        recipients.append(("Linda", settings.LINDA_EMAIL))
    
    # Add assigned technician email
    if tech_id and settings.TECH_EMAILS_JSON:
        try:
            import json
            tech_emails = json.loads(settings.TECH_EMAILS_JSON)
            if tech_id.lower() in tech_emails:
                recipients.append((tech_name or tech_id, tech_emails[tech_id.lower()]))
        except json.JSONDecodeError:
            logger.warning("Failed to parse TECH_EMAILS_JSON")
    
    if not recipients:
        logger.warning("No staff email recipients configured for emergency notifications")
        return {"status": "skipped", "reason": "no_recipients"}
    
    # Send emails
    subject = f"🚨 Emergency Service Request - {customer_name or 'Customer'}"
    for name, email in recipients:
        try:
            result = service.send_email(
                to=email,
                subject=subject,
                body_html=html_body,
                body_text=text_body,
            )
            sent_results[name] = {
                "email": email,
                "status": result.get("status", "unknown"),
                "message_id": result.get("message_id"),
            }
            logger.info(f"Sent emergency notification email to {name} ({email})")
        except Exception as e:
            logger.error(f"Failed to send email to {name} ({email}): {e}")
            sent_results[name] = {
                "email": email,
                "status": "error",
                "error": str(e),
            }
    
    return {
        "status": "sent" if any(r.get("status") == "sent" or r.get("status") == "dry_run" for r in sent_results.values()) else "partial",
        "recipients": sent_results,
    }


async def send_service_confirmation_email(
    to_email: str,
    customer_name: str | None,
    is_same_day: bool = False,
    appointment_date: str | None = None,
) -> dict[str, Any]:
    """
    Send standard service confirmation email.
    
    Returns:
        Dict with status and message_id on success, or error info
    """
    settings = get_settings()
    
    # Feature flag check
    if not settings.FEATURE_EMERGENCY_SMS:
        logger.debug("FEATURE_EMERGENCY_SMS disabled, skipping email")
        return {"status": "disabled", "reason": "feature_flag"}
    
    service = create_email_service_from_settings()
    if not service:
        return {"status": "disabled", "reason": "not_configured"}
    
    html_body, text_body = build_service_confirmation_email(
        customer_name=customer_name,
        is_same_day=is_same_day,
        appointment_date=appointment_date,
    )
    
    # Send email (synchronous operation - typically fast < 1s, acceptable for async context)
    try:
        result = service.send_email(
            to=to_email,
            subject="Service Request Confirmation - HVAC-R Finest",
            body_html=html_body,
            body_text=text_body,
        )
        return {"status": "sent", **result}
    except EmailError as e:
        logger.error(f"Failed to send service email: {e}")
        return {"status": "failed", "error": str(e)}


def build_new_lead_notification_email(
    customer_name: str | None,
    phone: str | None,
    email: str | None,
    address: str | None,
    service_type: str | None,
    priority_label: str | None,
    assigned_technician: str | None,
    lead_id: int | None = None,
    odoo_url: str | None = None,
) -> tuple[str, str]:
    """
    Build new lead notification email (HTML + text versions).
    
    This email is sent to Junior, Linda, Dispatch Team, and info@hvacrfinest.com.
    
    Returns:
        Tuple of (html_body, text_body)
    """
    customer_info = customer_name or "Unknown"
    lead_link = f"https://www.hvacrfinest.com/web#id={lead_id}&model=crm.lead&view_type=form" if lead_id and not odoo_url else (odoo_url or f"Lead ID: #{lead_id}" if lead_id else "N/A")
    
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
            .info-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .priority-high {{ background-color: #fff3cd; border-left: 4px solid #ffc107; }}
            .priority-emergency {{ background-color: #ffebee; border-left: 4px solid #d32f2f; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            .button {{ display: inline-block; padding: 10px 20px; background-color: #1976d2; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>HVAC-R Finest</h1>
                <h2>New Lead Notification</h2>
            </div>
            <div class="content">
                <p>A new lead has been created in the system.</p>
                
                <div class="info-box {'priority-emergency' if priority_label and 'emergency' in priority_label.lower() else 'priority-high' if priority_label and 'high' in priority_label.lower() else ''}">
                    <h3>Customer Information</h3>
                    <p><strong>Name:</strong> {customer_info}</p>
                    {f"<p><strong>Phone:</strong> {phone}</p>" if phone else ""}
                    {f"<p><strong>Email:</strong> {email}</p>" if email else ""}
                    {f"<p><strong>Address:</strong> {address}</p>" if address else ""}
                </div>
                
                <div class="info-box">
                    <h3>Service Details</h3>
                    {f"<p><strong>Service Type:</strong> {service_type}</p>" if service_type else ""}
                    {f"<p><strong>Priority:</strong> {priority_label}</p>" if priority_label else ""}
                    {f"<p><strong>Assigned Technician:</strong> {assigned_technician}</p>" if assigned_technician else "<p><strong>Assigned Technician:</strong> Unassigned</p>"}
                </div>
                
                <div class="info-box">
                    <h3>Odoo Lead</h3>
                    {f'<p><strong>Lead ID:</strong> <a href="{lead_link}">#{lead_id}</a></p>' if lead_id else ""}
                    {f'<p><a href="{lead_link}" class="button">View Lead in Odoo</a></p>' if lead_id else ""}
                </div>
                
                <p><strong>This is an automated notification from the HAES system.</strong></p>
            </div>
            <div class="footer">
                <p>HVAC-R Finest | Lead Management System</p>
                <p>Do not reply to this automated message</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    New Lead Notification - HVAC-R Finest
    
    A new lead has been created in the system.
    
    CUSTOMER INFORMATION:
    - Name: {customer_info}
    {f"- Phone: {phone}" if phone else ""}
    {f"- Email: {email}" if email else ""}
    {f"- Address: {address}" if address else ""}
    
    SERVICE DETAILS:
    {f"- Service Type: {service_type}" if service_type else ""}
    {f"- Priority: {priority_label}" if priority_label else ""}
    {f"- Assigned Technician: {assigned_technician}" if assigned_technician else "- Assigned Technician: Unassigned"}
    
    ODOO LEAD:
    {f"- Lead ID: #{lead_id}" if lead_id else ""}
    {f"- Link: {lead_link}" if lead_id else ""}
    
    This is an automated notification from the HAES system.
    
    ---
    HVAC-R Finest | Lead Management System
    Do not reply to this automated message
    """
    
    return html_body.strip(), text_body.strip()


async def send_new_lead_notification(
    customer_name: str | None,
    phone: str | None,
    email: str | None,
    address: str | None,
    service_type: str | None = None,
    priority_label: str | None = None,
    assigned_technician: str | None = None,
    lead_id: int | None = None,
    odoo_url: str | None = None,
) -> dict[str, Any]:
    """
    Send new lead notification emails to Junior, Linda, Dispatch Team, and info@hvacrfinest.com.
    
    Args:
        customer_name: Customer name
        phone: Customer phone number
        email: Customer email address
        address: Service address
        service_type: Type of service requested
        priority_label: Priority level (e.g., "Emergency", "High", "Medium", "Low")
        assigned_technician: Name of assigned technician
        lead_id: Odoo lead ID
        odoo_url: Optional custom Odoo URL (if not provided, will be generated from lead_id)
    
    Returns:
        Dict with status and sent emails info
    """
    settings = get_settings()
    
    # Check if email is configured
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.debug("SMTP not configured, skipping lead email notifications")
        return {"status": "disabled", "reason": "not_configured"}
    
    # Create email service
    try:
        service = create_email_service_from_settings()
        if not service:
            return {"status": "disabled", "reason": "not_configured"}
    except Exception as e:
        logger.warning(f"Failed to create email service: {e}")
        return {"status": "error", "error": str(e)}
    
    # Build message
    html_body, text_body = build_new_lead_notification_email(
        customer_name=customer_name,
        phone=phone,
        email=email,
        address=address,
        service_type=service_type,
        priority_label=priority_label,
        assigned_technician=assigned_technician,
        lead_id=lead_id,
        odoo_url=odoo_url,
    )
    
    # Collect recipients
    recipients = []
    sent_results = {}
    
    # Add Junior email
    if settings.JUNIOR_EMAIL:
        recipients.append(("Junior", settings.JUNIOR_EMAIL))
    elif hasattr(settings, "OWNER_EMAIL") and settings.OWNER_EMAIL:
        recipients.append(("Junior", settings.OWNER_EMAIL))
    
    # Add Linda email
    if settings.LINDA_EMAIL:
        recipients.append(("Linda", settings.LINDA_EMAIL))
    
    # Add Dispatch email
    if settings.DISPATCH_EMAIL:
        recipients.append(("Dispatch Team", settings.DISPATCH_EMAIL))
    
    # Add info@hvacrfinest.com
    recipients.append(("Info", "info@hvacrfinest.com"))
    
    if not recipients:
        logger.warning("No email recipients configured for lead notifications")
        return {"status": "skipped", "reason": "no_recipients"}
    
    # Send emails
    subject = f"New Lead: {customer_name or 'Customer'} - {service_type or 'Service Request'}"
    for name, email_addr in recipients:
        try:
            result = service.send_email(
                to=email_addr,
                subject=subject,
                body_html=html_body,
                body_text=text_body,
            )
            sent_results[name] = {
                "email": email_addr,
                "status": result.get("status", "unknown"),
                "message_id": result.get("message_id"),
            }
            logger.info(f"Sent new lead notification email to {name} ({email_addr})")
        except Exception as e:
            logger.error(f"Failed to send email to {name} ({email_addr}): {e}")
            sent_results[name] = {
                "email": email_addr,
                "status": "error",
                "error": str(e),
            }
    
    return {
        "status": "sent" if any(r.get("status") == "sent" or r.get("status") == "dry_run" for r in sent_results.values()) else "partial",
        "recipients": sent_results,
    }


def build_membership_enrollment_email(
    customer_name: str | None,
    plan_name: str,
    annual_price: float,
    payment_link: str,
    vip_benefits: str,
) -> tuple[str, str, str]:
    """
    Build membership enrollment email (subject, HTML, text).
    
    Returns:
        Tuple of (subject, html_body, text_body)
    """
    greeting = f"Hi {customer_name}," if customer_name else "Hello,"
    subject = f"HVAC-R Finest {plan_name} Enrollment - Payment Required"
    
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
            .info-box {{ background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #1976d2; color: white; text-decoration: none; border-radius: 5px; margin: 15px 0; }}
            .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>HVAC-R Finest</h1>
                <h2>Membership Enrollment</h2>
            </div>
            <div class="content">
                <p>{greeting}</p>
                
                <div class="info-box">
                    <h3>{plan_name}</h3>
                    <p><strong>Annual Cost:</strong> ${annual_price:.0f}</p>
                    <p><strong>VIP Benefits:</strong> {vip_benefits}</p>
                </div>
                
                <p>To complete your enrollment, please click the button below to make your payment:</p>
                
                <p style="text-align: center;">
                    <a href="{payment_link}" class="button">Complete Enrollment & Pay</a>
                </p>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #1976d2;">{payment_link}</p>
                
                <p>Once payment is received, you'll receive a confirmation email with your membership details.</p>
                
                <p>Thank you for choosing HVAC-R Finest!</p>
            </div>
            <div class="footer">
                <p>HVAC-R Finest LLC<br>
                (972) 372-4458<br>
                info@hvacrfinest.com</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
{greeting}

Thank you for enrolling in {plan_name} with HVAC-R Finest!

Plan Details:
- Plan: {plan_name}
- Annual Cost: ${annual_price:.0f}
- VIP Benefits: {vip_benefits}

To complete your enrollment, please visit:
{payment_link}

Once payment is received, you'll receive a confirmation email with your membership details.

Thank you for choosing HVAC-R Finest!

HVAC-R Finest LLC
(972) 372-4458
info@hvacrfinest.com
    """
    
    return subject, html_body, text_body
