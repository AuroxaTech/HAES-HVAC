"""
HAES HVAC - OPS Brain Handlers

Main entry point for OPS brain command handling.
"""

import logging
from datetime import datetime

from src.hael.schema import HaelCommand, Intent, UrgencyLevel
from src.brains.ops.schema import (
    OpsResult,
    OpsStatus,
    ServicePriority,
    ServiceRequest,
    TechnicianAssignment,
    WorkOrderData,
    WorkOrderStatus,
)
from src.brains.ops.emergency_rules import qualify_emergency
from src.brains.ops.service_catalog import infer_service_type_from_description
from src.brains.ops.tech_roster import assign_technician

logger = logging.getLogger(__name__)

# Supported OPS intents
OPS_INTENTS = {
    Intent.SERVICE_REQUEST,
    Intent.SCHEDULE_APPOINTMENT,
    Intent.RESCHEDULE_APPOINTMENT,
    Intent.CANCEL_APPOINTMENT,
    Intent.STATUS_UPDATE_REQUEST,
}


def handle_ops_command(command: HaelCommand) -> OpsResult:
    """
    Handle an OPS brain command.
    
    This is the main entry point for all OPS operations.
    
    Args:
        command: HAEL command to process
        
    Returns:
        OpsResult with operation outcome
    """
    logger.info(f"OPS brain handling command: {command.intent.value}")
    
    # Check if intent is supported
    if command.intent not in OPS_INTENTS:
        return OpsResult(
            status=OpsStatus.UNSUPPORTED_INTENT,
            message=f"Intent '{command.intent.value}' is not handled by OPS brain",
            requires_human=False,
        )
    
    # Check if HAEL says requires human
    if command.requires_human:
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="HAEL indicated human intervention required",
            requires_human=True,
            missing_fields=command.missing_fields,
        )
    
    # Route to specific handler
    try:
        if command.intent == Intent.SERVICE_REQUEST:
            return _handle_service_request(command)
        elif command.intent == Intent.SCHEDULE_APPOINTMENT:
            return _handle_schedule_appointment(command)
        elif command.intent == Intent.RESCHEDULE_APPOINTMENT:
            return _handle_reschedule_appointment(command)
        elif command.intent == Intent.CANCEL_APPOINTMENT:
            return _handle_cancel_appointment(command)
        elif command.intent == Intent.STATUS_UPDATE_REQUEST:
            return _handle_status_update(command)
        else:
            return OpsResult(
                status=OpsStatus.ERROR,
                message=f"Unhandled intent: {command.intent.value}",
                requires_human=True,
            )
    except Exception as e:
        logger.exception(f"Error handling OPS command: {e}")
        return OpsResult(
            status=OpsStatus.ERROR,
            message=f"Internal error: {str(e)}",
            requires_human=True,
        )


def _handle_service_request(command: HaelCommand) -> OpsResult:
    """Handle a new service request."""
    entities = command.entities
    
    # Validate required fields
    missing = []
    if not (entities.phone or entities.email or entities.full_name):
        missing.append("identity (phone, email, or name)")
    if not (entities.address or entities.zip_code):
        missing.append("location (address or zip_code)")
    if not entities.problem_description:
        missing.append("problem_description")
    
    if missing:
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Missing required information for service request",
            requires_human=True,
            missing_fields=missing,
            suggested_action="Please provide: " + ", ".join(missing),
        )
    
    # Qualify emergency
    emergency = qualify_emergency(
        problem_description=entities.problem_description or "",
        urgency_level=entities.urgency_level,
        temperature_mentioned=entities.temperature_mentioned,
    )
    
    # Infer service type
    service_type = infer_service_type_from_description(
        entities.problem_description or ""
    )
    
    # Determine priority
    if emergency.is_emergency:
        priority = ServicePriority.EMERGENCY
    elif entities.urgency_level == UrgencyLevel.HIGH:
        priority = ServicePriority.URGENT
    elif entities.urgency_level == UrgencyLevel.MEDIUM:
        priority = ServicePriority.HIGH
    else:
        priority = ServicePriority.NORMAL
    
    # Determine if commercial
    is_commercial = entities.property_type == "commercial"
    
    # Assign technician
    technician = assign_technician(
        zip_code=entities.zip_code,
        is_emergency=emergency.is_emergency,
        is_commercial=is_commercial,
    )
    
    tech_assignment = None
    if technician:
        tech_assignment = TechnicianAssignment(
            technician_id=technician.id,
            technician_name=technician.name,
            skill_level=technician.skill_level.value,
            phone=technician.phone,
        )
    
    # Build work order data
    work_order = WorkOrderData(
        customer_name=entities.full_name,
        customer_phone=entities.phone,
        customer_email=entities.email,
        address=entities.address,
        zip_code=entities.zip_code,
        problem_description=entities.problem_description,
        service_type=service_type.code,
        priority=priority,
        status=WorkOrderStatus.PENDING_SCHEDULE,
        technician=tech_assignment,
        created_at=datetime.utcnow(),
    )
    
    # Determine if we need human for technician assignment
    if not technician:
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="No technician available for this service area",
            requires_human=True,
            work_order=work_order,
            suggested_action="Manual technician assignment required",
        )
    
    message = f"Service request created - Priority: {priority.value}"
    if emergency.is_emergency:
        message = f"EMERGENCY: {emergency.reason}. " + message
    
    return OpsResult(
        status=OpsStatus.SUCCESS,
        message=message,
        requires_human=False,
        work_order=work_order,
        data={
            "is_emergency": emergency.is_emergency,
            "emergency_reason": emergency.reason if emergency.is_emergency else None,
            "service_type": service_type.name,
            "estimated_duration_min": service_type.duration_minutes_min,
            "estimated_duration_max": service_type.duration_minutes_max,
        },
    )


def _handle_schedule_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment scheduling request."""
    # Similar to service request but focused on scheduling
    entities = command.entities
    
    # Validate identity
    if not (entities.phone or entities.email):
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to schedule",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    # For MVP, we return that scheduling was captured
    # Actual Odoo integration would create calendar event
    return OpsResult(
        status=OpsStatus.SUCCESS,
        message="Scheduling request captured. A representative will confirm the appointment.",
        requires_human=False,
        data={
            "contact_phone": entities.phone,
            "contact_email": entities.email,
            "preferred_times": entities.preferred_time_windows,
        },
    )


def _handle_reschedule_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment reschedule request."""
    entities = command.entities
    
    # Need identity to lookup existing appointment
    if not (entities.phone or entities.email):
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to find your appointment",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    # For MVP, indicate reschedule captured
    return OpsResult(
        status=OpsStatus.SUCCESS,
        message="Reschedule request received. A representative will contact you to confirm the new time.",
        requires_human=False,
        data={
            "contact_phone": entities.phone,
            "contact_email": entities.email,
        },
    )


def _handle_cancel_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment cancellation request."""
    entities = command.entities
    
    # Need identity to lookup existing appointment
    if not (entities.phone or entities.email):
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to find your appointment",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    # For MVP, indicate cancellation captured
    return OpsResult(
        status=OpsStatus.SUCCESS,
        message="Cancellation request received. Your appointment will be cancelled and you will receive confirmation.",
        requires_human=False,
        data={
            "contact_phone": entities.phone,
            "contact_email": entities.email,
        },
    )


def _handle_status_update(command: HaelCommand) -> OpsResult:
    """Handle status inquiry request."""
    entities = command.entities
    
    # Need identity to lookup
    if not (entities.phone or entities.email):
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to look up your service status",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    # For MVP, indicate lookup will happen
    return OpsResult(
        status=OpsStatus.SUCCESS,
        message="Looking up your service status. A representative will provide an update shortly.",
        requires_human=False,
        data={
            "contact_phone": entities.phone,
            "contact_email": entities.email,
        },
    )

