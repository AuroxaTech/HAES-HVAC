"""
HAES HVAC - Odoo Error Handling Utilities

Provides graceful degradation when Odoo API is unavailable:
- Local data capture
- Emergency notifications
- Retry queue
- User-friendly messaging
"""

import logging
from typing import Any
from datetime import datetime

from src.utils.errors import OdooAuthError, OdooRPCError, OdooTransportError
from src.db.models import Job
from src.integrations.email_notifications import create_email_service_from_settings
from src.integrations.twilio_sms import send_emergency_sms
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class OdooErrorHandler:
    """Handles Odoo API errors with graceful degradation."""
    
    @staticmethod
    async def handle_odoo_error(
        error: Exception,
        operation: str,
        data: dict[str, Any] | None = None,
        session: Any = None,
    ) -> dict[str, Any]:
        """
        Handle Odoo API errors with graceful degradation.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation (e.g., "create_lead")
            data: Data that was being processed
            session: Database session for storing data locally
            
        Returns:
            Dict with error handling result:
            {
                "handled": bool,
                "user_message": str,
                "data_captured": bool,
                "retry_queued": bool,
            }
        """
        is_odoo_error = isinstance(
            error, (OdooAuthError, OdooRPCError, OdooTransportError)
        )
        
        if not is_odoo_error:
            # Not an Odoo error, re-raise
            raise error
        
        logger.error(f"Odoo error in {operation}: {error}")
        
        # Capture data locally if session provided
        data_captured = False
        if session and data:
            try:
                # Store in a local queue/job for retry
                retry_job = Job(
                    run_at=datetime.now(),
                    type="odoo_retry",
                    payload_json={
                        "operation": operation,
                        "data": data,
                        "error": str(error),
                        "retry_count": 0,
                    },
                    correlation_id=f"odoo_retry_{operation}_{datetime.now().isoformat()}",
                    max_attempts=3,
                )
                session.add(retry_job)
                session.commit()
                data_captured = True
                logger.info(f"Captured data locally for {operation}, queued for retry")
            except Exception as capture_err:
                logger.error(f"Failed to capture data locally: {capture_err}")
        
        # Send emergency notification to tech team
        try:
            settings = get_settings()
            tech_team_emails = [
                settings.ODOO_ADMIN_EMAIL or "admin@hvacrfinest.com",
            ]
            
            error_message = f"""
Odoo API Error Detected

Operation: {operation}
Error Type: {type(error).__name__}
Error Message: {str(error)}
Time: {datetime.now().isoformat()}

The system has captured the data locally and queued it for retry.
Please investigate the Odoo connection immediately.
"""
            
            email_service = create_email_service_from_settings()
            if email_service:
                try:
                    email_service.send_email(
                        to=tech_team_emails,
                        subject="URGENT: Odoo API Error",
                        body_text=error_message,
                        body_html=f"<pre>{error_message}</pre>",
                    )
                except Exception as email_err:
                    logger.warning(f"Failed to send emergency email: {email_err}")
            
            # Also send SMS to critical contacts if available
            try:
                if hasattr(settings, 'JUNIOR_PHONE') and settings.JUNIOR_PHONE:
                    await send_emergency_sms(
                        to_phone=settings.JUNIOR_PHONE,
                        customer_name="System Alert",
                        tech_name="System",
                        eta_hours_min=0,
                        eta_hours_max=0,
                        total_fee=0,
                    )
            except Exception:
                pass  # SMS is optional
            
        except Exception as notify_err:
            logger.error(f"Failed to send emergency notification: {notify_err}")
        
        # Return user-friendly message
        user_message = (
            "I'm experiencing a technical issue, but I've captured your information. "
            "You'll receive a confirmation within 30 minutes. "
            "If you need immediate assistance, please call us directly at (972) 372-4458."
        )
        
        return {
            "handled": True,
            "user_message": user_message,
            "data_captured": data_captured,
            "retry_queued": data_captured,
            "error_type": type(error).__name__,
        }
    
    @staticmethod
    async def wrap_odoo_operation(
        operation: callable,
        operation_name: str,
        data: dict[str, Any] | None = None,
        session: Any = None,
        *args,
        **kwargs,
    ) -> Any:
        """
        Wrap an Odoo operation with error handling.
        
        Args:
            operation: The async function to execute
            operation_name: Name of the operation for logging
            data: Data being processed (for local capture)
            session: Database session for local storage
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            Result of the operation, or error handling result if Odoo fails
        """
        try:
            return await operation(*args, **kwargs)
        except (OdooAuthError, OdooRPCError, OdooTransportError) as e:
            error_result = await OdooErrorHandler.handle_odoo_error(
                error=e,
                operation=operation_name,
                data=data,
                session=session,
            )
            # Return a result that indicates graceful degradation
            return {
                "_odoo_error": True,
                "_error_handled": True,
                **error_result,
            }
