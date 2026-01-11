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


async def handle_ops_command(command: HaelCommand) -> OpsResult:
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
            return await _handle_schedule_appointment(command)
        elif command.intent == Intent.RESCHEDULE_APPOINTMENT:
            return await _handle_reschedule_appointment(command)
        elif command.intent == Intent.CANCEL_APPOINTMENT:
            return await _handle_cancel_appointment(command)
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
    
    # Build technician assignment data
    tech_data = None
    if technician:
        tech_data = {
            "id": technician.id,
            "name": technician.name,
            "phone": technician.phone,
            "skill_level": technician.skill_level.value,
        }
    
    # Emergency ETA window (default: 1.5 - 3 hours for emergency, 4-8 hours for urgent)
    eta_window = None
    priority_label = priority.value
    if emergency.is_emergency:
        eta_window = {"hours_min": 1.5, "hours_max": 3.0}
        priority_label = "CRITICAL"
    elif priority == ServicePriority.URGENT:
        eta_window = {"hours_min": 4.0, "hours_max": 8.0}
    
    message = f"Service request created - Priority: {priority_label}"
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
            "priority_label": priority_label,
            "eta_window_hours_min": eta_window["hours_min"] if eta_window else None,
            "eta_window_hours_max": eta_window["hours_max"] if eta_window else None,
            "service_type": service_type.name,
            "estimated_duration_min": service_type.duration_minutes_min,
            "estimated_duration_max": service_type.duration_minutes_max,
            "assigned_technician": tech_data,
        },
    )


async def _handle_schedule_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment scheduling request."""
    from datetime import timedelta
    from src.integrations.odoo_appointments import create_appointment_service
    from src.integrations.odoo_leads import create_lead_service
    from src.brains.ops.service_catalog import infer_service_type_from_description
    
    entities = command.entities
    
    # Validate required fields
    missing = []
    if not (entities.phone or entities.email):
        missing.append("phone or email")
    
    if missing:
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to schedule",
            requires_human=True,
            missing_fields=missing,
        )
    
    try:
        # Create appointment service
        appointment_service = await create_appointment_service()
        
        # Look for existing partner (for linking)
        lead_service = await create_lead_service()
        partner_id = await lead_service.ensure_partner(
            phone=entities.phone,
            email=entities.email,
            name=entities.full_name,
            address=entities.address,
            city=entities.city,
            zip_code=entities.zip_code,
        )
        
        # Infer service type and duration
        problem_desc = entities.problem_description or "General service"
        service_type = infer_service_type_from_description(problem_desc)
        duration_minutes = service_type.duration_minutes_max  # Use max duration for safety
        
        # Try to find existing lead for linking (simplified - will be linked after appointment creation if needed)
        lead_id = None
        
        # Determine technician assignment
        tech = None
        tech_id = None
        if entities.zip_code:
            from src.brains.ops.tech_roster import assign_technician
            tech = assign_technician(
                zip_code=entities.zip_code,
                is_emergency=False,
                is_commercial=entities.property_type == "commercial",
            )
            if tech:
                tech_id = tech.id
        
        # Find available slot
        from datetime import datetime, timedelta
        now = datetime.now()
        preferred_start = now + timedelta(hours=2)  # Default: 2 hours from now
        
        # Try to parse preferred time if provided
        if entities.preferred_time_windows:
            # Use first preferred window (simplified - could be enhanced)
            preferred_start = now + timedelta(hours=4)  # Default fallback
        
        # Find next available slot
        slot = await appointment_service.find_next_available_slot(
            tech_id=tech_id or "junior",  # Default to junior if no tech assigned
            after=preferred_start,
            duration_minutes=duration_minutes,
        )
        
        if not slot:
            # No slot found - return needs human with suggestion
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="No available appointments found. A representative will contact you to schedule.",
                requires_human=True,
                suggested_action="Contact customer to find suitable time",
            )
        
        # Build appointment name
        customer_name = entities.full_name or entities.phone or "Customer"
        service_name = service_type.name
        appointment_name = f"{service_name} - {customer_name}"
        
        # Create calendar event in Odoo
        event_id = await appointment_service.create_appointment(
            name=appointment_name,
            start=slot.start,
            stop=slot.end,
            partner_id=partner_id,
            tech_id=tech_id,
            description=problem_desc,
            location=entities.address,
            lead_id=lead_id,
        )
        
        if not event_id:
            # Failed to create in Odoo - return needs human but with captured info
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="Scheduling request received. A representative will confirm the appointment.",
                requires_human=True,
                data={
                    "contact_phone": entities.phone,
                    "contact_email": entities.email,
                    "preferred_time": preferred_start.isoformat(),
                    "service_type": service_type.name,
                },
            )
        
        # Build response
        tech_assignment = None
        if tech:
            tech_assignment = TechnicianAssignment(
                technician_id=tech.id,
                technician_name=tech.name,
                skill_level=tech.skill_level.value,
                phone=tech.phone,
            )
        
        # Format appointment time for message
        appointment_time_str = slot.start.strftime("%A, %B %d at %I:%M %p")
        
        message = f"Appointment scheduled for {appointment_time_str}. {service_name} visit confirmed."
        
        return OpsResult(
            status=OpsStatus.SUCCESS,
            message=message,
            requires_human=False,
            data={
                "appointment_id": event_id,
                "scheduled_time": slot.start.isoformat(),
                "scheduled_time_end": slot.end.isoformat(),
                "service_type": service_type.name,
                "duration_minutes": duration_minutes,
                "assigned_technician": {
                    "id": tech.id,
                    "name": tech.name,
                    "phone": tech.phone,
                } if tech else None,
                "partner_id": partner_id,
                "lead_id": lead_id,
            },
        )
        
    except Exception as e:
        logger.exception(f"Error scheduling appointment: {e}")
        return OpsResult(
            status=OpsStatus.ERROR,
            message="Scheduling request received. A representative will contact you to confirm.",
            requires_human=True,
            data={
                "contact_phone": entities.phone,
                "contact_email": entities.email,
                "error": str(e),
            },
        )


async def _handle_reschedule_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment reschedule request."""
    from datetime import timedelta
    from src.integrations.odoo_appointments import create_appointment_service
    
    entities = command.entities
    
    # Need identity to lookup existing appointment
    if not (entities.phone or entities.email):
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to find your appointment",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    try:
        appointment_service = await create_appointment_service()
        
        # Find existing appointment
        from datetime import datetime, timedelta
        now = datetime.now()
        appointments = await appointment_service.find_appointment_by_contact(
            phone=entities.phone,
            email=entities.email,
            date_from=now - timedelta(days=30),
            date_to=now + timedelta(days=90),
        )
        
        if not appointments:
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="No existing appointment found. Would you like to schedule a new appointment?",
                requires_human=True,
                data={
                    "contact_phone": entities.phone,
                    "contact_email": entities.email,
                },
            )
        
        # Use most recent upcoming appointment
        upcoming_appointments = [a for a in appointments if datetime.fromisoformat(a["start"].replace("Z", "+00:00")) > now]
        if not upcoming_appointments:
            upcoming_appointments = appointments[:1]  # Use most recent
        
        appointment = upcoming_appointments[0]
        event_id = appointment["id"]
        
        # Parse existing appointment time
        existing_start = datetime.fromisoformat(appointment["start"].replace("Z", "+00:00"))
        if existing_start.tzinfo:
            existing_start = existing_start.replace(tzinfo=None)
        existing_stop = datetime.fromisoformat(appointment["stop"].replace("Z", "+00:00"))
        if existing_stop.tzinfo:
            existing_stop = existing_stop.replace(tzinfo=None)
        
        duration_minutes = int((existing_stop - existing_start).total_seconds() / 60)
        
        # Get new preferred time (default: same time next day or 4 hours from now)
        preferred_start = max(existing_start + timedelta(days=1), now + timedelta(hours=4))
        if entities.preferred_time_windows:
            # Use first preferred window (simplified)
            preferred_start = now + timedelta(hours=4)
        
        # Get technician user_id from existing appointment if available
        tech_id = None
        existing_user_id = appointment.get("user_id")
        if existing_user_id and isinstance(existing_user_id, list) and len(existing_user_id) > 1:
            # Odoo returns user_id as [id, name]
            user_id = existing_user_id[0]
            # Try to map back to tech_id
            from src.config.settings import get_settings
            import json
            settings = get_settings()
            try:
                tech_user_map = json.loads(settings.ODOO_TECH_USER_IDS_JSON)
                for tid, uid in tech_user_map.items():
                    if int(uid) == user_id:
                        tech_id = tid
                        break
            except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                pass
        
        # Find available slot for reschedule
        slot = await appointment_service.find_next_available_slot(
            tech_id=tech_id or "junior",
            after=preferred_start,
            duration_minutes=duration_minutes,
        )
        
        if not slot:
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="No available slots found for rescheduling. A representative will contact you.",
                requires_human=True,
                data={
                    "existing_appointment_id": event_id,
                    "contact_phone": entities.phone,
                },
            )
        
        # Update the appointment
        success = await appointment_service.update_appointment(
            event_id=event_id,
            start=slot.start,
            stop=slot.end,
            tech_id=tech_id,
        )
        
        if not success:
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="Reschedule request received. A representative will contact you to confirm the new time.",
                requires_human=True,
                data={
                    "existing_appointment_id": event_id,
                    "contact_phone": entities.phone,
                },
            )
        
        # Format new appointment time
        new_time_str = slot.start.strftime("%A, %B %d at %I:%M %p")
        
        return OpsResult(
            status=OpsStatus.SUCCESS,
            message=f"Appointment rescheduled to {new_time_str}. Confirmation sent.",
            requires_human=False,
            data={
                "appointment_id": event_id,
                "scheduled_time": slot.start.isoformat(),
                "scheduled_time_end": slot.end.isoformat(),
                "previous_time": existing_start.isoformat(),
            },
        )
        
    except Exception as e:
        logger.exception(f"Error rescheduling appointment: {e}")
        return OpsResult(
            status=OpsStatus.ERROR,
            message="Reschedule request received. A representative will contact you to confirm.",
            requires_human=True,
            data={
                "contact_phone": entities.phone,
                "error": str(e),
            },
        )


async def _handle_cancel_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment cancellation request."""
    from src.integrations.odoo_appointments import create_appointment_service
    
    entities = command.entities
    
    # Need identity to lookup existing appointment
    if not (entities.phone or entities.email):
        return OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message="Need contact information to find your appointment",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    try:
        appointment_service = await create_appointment_service()
        
        # Find existing appointment
        from datetime import datetime, timedelta
        now = datetime.now()
        appointments = await appointment_service.find_appointment_by_contact(
            phone=entities.phone,
            email=entities.email,
            date_from=now - timedelta(days=30),
            date_to=now + timedelta(days=90),
        )
        
        if not appointments:
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="No existing appointment found to cancel.",
                requires_human=True,
                data={
                    "contact_phone": entities.phone,
                    "contact_email": entities.email,
                },
            )
        
        # Use most recent upcoming appointment
        upcoming_appointments = [a for a in appointments if datetime.fromisoformat(a["start"].replace("Z", "+00:00")) > now]
        if not upcoming_appointments:
            upcoming_appointments = appointments[:1]  # Use most recent
        
        appointment = upcoming_appointments[0]
        event_id = appointment["id"]
        lead_id = appointment.get("res_id") if appointment.get("res_model") == "crm.lead" else None
        
        # Cancel the appointment
        success = await appointment_service.cancel_appointment(event_id=event_id)
        
        if not success:
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message="Cancellation request received. A representative will process your cancellation.",
                requires_human=True,
                data={
                    "appointment_id": event_id,
                    "contact_phone": entities.phone,
                },
            )
        
        # Optionally update linked lead status (simplified - could be enhanced)
        if lead_id:
            try:
                # Could update lead stage to "cancelled" or "lost" here
                # For now, just log it
                logger.info(f"Appointment {event_id} cancelled, linked to lead {lead_id}")
            except Exception as e:
                logger.warning(f"Failed to update lead {lead_id} after cancellation: {e}")
        
        return OpsResult(
            status=OpsStatus.SUCCESS,
            message="Your appointment has been cancelled. You will receive a confirmation shortly.",
            requires_human=False,
            data={
                "appointment_id": event_id,
                "cancelled": True,
                "lead_id": lead_id,
            },
        )
        
    except Exception as e:
        logger.exception(f"Error cancelling appointment: {e}")
        return OpsResult(
            status=OpsStatus.ERROR,
            message="Cancellation request received. A representative will process your cancellation.",
            requires_human=True,
            data={
                "contact_phone": entities.phone,
                "error": str(e),
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

