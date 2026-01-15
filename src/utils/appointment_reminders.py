"""
HAES HVAC - Appointment Reminder Scheduling

Schedules SMS reminders 2 hours before appointments.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.db.models import Job
from src.integrations.twilio_sms import send_appointment_reminder_sms

logger = logging.getLogger(__name__)


def schedule_appointment_reminder(
    db: Session,
    appointment_id: int,
    appointment_datetime: datetime,
    customer_phone: str,
    customer_name: str | None = None,
    appointment_date: str | None = None,
    appointment_time: str | None = None,
    tech_name: str | None = None,
    service_type: str | None = None,
) -> int:
    """
    Schedule an SMS reminder to be sent 2 hours before the appointment.
    
    Args:
        db: Database session
        appointment_id: Odoo appointment/event ID
        appointment_datetime: Appointment datetime (timezone-aware)
        customer_phone: Customer phone number
        customer_name: Customer name
        appointment_date: Formatted appointment date (e.g., "Tuesday, January 14")
        appointment_time: Formatted appointment time (e.g., "2:00 PM")
        tech_name: Assigned technician name
        service_type: Type of service
        
    Returns:
        Job ID
    """
    # Calculate reminder time (2 hours before appointment)
    reminder_time = appointment_datetime - timedelta(hours=2)
    
    # Don't schedule if reminder time is in the past
    now = datetime.now(timezone.utc)
    if reminder_time < now:
        logger.warning(
            f"Appointment {appointment_id} is less than 2 hours away, "
            f"not scheduling reminder"
        )
        return 0
    
    # Create job payload
    payload = {
        "appointment_id": appointment_id,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "tech_name": tech_name,
        "service_type": service_type,
    }
    
    # Create job
    job = Job(
        type="send_appointment_reminder_sms",
        payload_json=payload,
        run_at=reminder_time,
        status="queued",
        correlation_id=f"appointment_{appointment_id}",
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    logger.info(
        f"Scheduled reminder SMS for appointment {appointment_id} "
        f"at {reminder_time} (2 hours before {appointment_datetime})"
    )
    
    return job.id


async def process_appointment_reminder_job(job: Job) -> dict[str, any]:
    """
    Process an appointment reminder job.
    
    This function is called by the job processor to send the reminder SMS.
    
    Args:
        job: Job record with payload containing appointment details
        
    Returns:
        Dict with status and result
    """
    payload = job.payload_json
    
    try:
        result = await send_appointment_reminder_sms(
            to_phone=payload["customer_phone"],
            customer_name=payload.get("customer_name"),
            appointment_date=payload.get("appointment_date"),
            appointment_time=payload.get("appointment_time"),
            tech_name=payload.get("tech_name"),
            service_type=payload.get("service_type"),
        )
        
        if result.get("status") == "sent":
            logger.info(
                f"Successfully sent reminder SMS for appointment {payload['appointment_id']}"
            )
            return {"status": "success", "result": result}
        else:
            logger.warning(
                f"Failed to send reminder SMS for appointment {payload['appointment_id']}: "
                f"{result.get('error', 'Unknown error')}"
            )
            return {"status": "failed", "error": result.get("error", "Unknown error")}
    except Exception as e:
        logger.exception(f"Error processing appointment reminder job {job.id}: {e}")
        return {"status": "error", "error": str(e)}
