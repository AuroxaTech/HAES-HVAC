"""
HAES HVAC - OPS Brain Handlers

Main entry point for OPS brain command handling.
"""

import logging
import re
from datetime import datetime, timedelta

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
from src.brains.ops.scheduling_rules import TimeSlot
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
    
    # Check if this is a warranty claim
    is_warranty = command.metadata.get("is_warranty", False)
    previous_technician_id = command.metadata.get("previous_technician_id")
    previous_service_id = command.metadata.get("previous_service_id")
    
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
    
    # Warranty handling: Set priority to 2nd highest if not emergency
    if is_warranty:
        if priority == ServicePriority.EMERGENCY:
            # Keep emergency priority for warranty emergencies
            pass
        elif priority == ServicePriority.URGENT:
            # Already urgent, keep it
            pass
        elif priority == ServicePriority.HIGH:
            # Set to urgent (2nd highest)
            priority = ServicePriority.URGENT
        else:
            # Set to high (2nd highest for normal)
            priority = ServicePriority.HIGH
        logger.info(
            f"Warranty claim detected - priority set to {priority.value}, "
            f"previous_service_id={previous_service_id}, "
            f"previous_technician_id={previous_technician_id}"
        )
    
    # Determine if commercial
    is_commercial = entities.property_type == "commercial"
    
    # Assign technician
    # For warranty claims, try to assign to same technician if previous_technician_id provided
    technician = None
    if is_warranty and previous_technician_id:
        from src.brains.ops.tech_roster import get_technician
        technician = get_technician(previous_technician_id)
        if technician:
            logger.info(f"Warranty claim: Assigning to previous technician {technician.name} ({technician.id})")
        else:
            logger.warning(f"Warranty claim: Previous technician {previous_technician_id} not found, falling back to normal assignment")
    
    # If no technician assigned yet (not warranty or previous tech not found), use normal assignment
    if not technician:
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
    
    # Build response data
    response_data = {
        "is_emergency": emergency.is_emergency,
        "emergency_reason": emergency.reason if emergency.is_emergency else None,
        "priority_label": priority_label,
        "eta_window_hours_min": eta_window["hours_min"] if eta_window else None,
        "eta_window_hours_max": eta_window["hours_max"] if eta_window else None,
        "service_type": service_type.name,
        "estimated_duration_min": service_type.duration_minutes_min,
        "estimated_duration_max": service_type.duration_minutes_max,
        "assigned_technician": tech_data,
    }
    
    # Add warranty information if applicable
    if is_warranty:
        response_data["is_warranty"] = True
        response_data["waive_diagnostic_fee"] = True  # Flag to waive diagnostic fee
        response_data["previous_service_id"] = previous_service_id
        response_data["previous_technician_id"] = previous_technician_id
        if previous_technician_id and technician:
            response_data["same_technician_assigned"] = True
        message += " [Warranty Claim - Diagnostic fee waived]"
    
    return OpsResult(
        status=OpsStatus.SUCCESS,
        message=message,
        requires_human=False,
        work_order=work_order,
        data=response_data,
    )


async def _handle_schedule_appointment(command: HaelCommand) -> OpsResult:
    """Handle appointment scheduling request.
    
    Supports two modes:
    1. Availability check: Only problem_description needed - returns next available slot
    2. Full scheduling: All fields needed - creates appointment in Odoo
    """
    from datetime import timedelta
    from src.integrations.odoo_appointments import create_appointment_service
    from src.integrations.odoo_leads import create_lead_service
    from src.brains.ops.service_catalog import infer_service_type_from_description
    
    entities = command.entities
    
    # Infer service type and duration (always needed for availability check)
    problem_desc = entities.problem_description or "General service"
    service_type = infer_service_type_from_description(problem_desc)
    duration_minutes = service_type.duration_minutes_max  # Use max duration for safety
    
    # Check if we have minimal info (just problem_description) - availability check mode
    has_identity = bool(entities.phone or entities.email or entities.full_name)
    has_location = bool(entities.address or entities.zip_code)
    
    if not (has_identity and has_location):
        # Availability check mode - return next available slot without creating appointment
        try:
            appointment_service = await create_appointment_service()
            
            # Determine technician (default to junior if no zip_code)
            tech_id = "junior"
            if entities.zip_code:
                from src.brains.ops.tech_roster import assign_technician
                tech = assign_technician(
                    zip_code=entities.zip_code,
                    is_emergency=False,
                    is_commercial=entities.property_type == "commercial",
                )
                if tech:
                    tech_id = tech.id
            
            # Find next two available slots (offer customer a choice)
            now = datetime.now()
            preferred_start = now + timedelta(hours=2)  # Default: 2 hours from now

            slots = await appointment_service.find_next_two_available_slots(
                tech_id=tech_id,
                after=preferred_start,
                duration_minutes=duration_minutes,
            )

            if not slots:
                missing_fields = []
                if not has_identity:
                    missing_fields.append("contact information (phone, email, or name)")
                if not has_location:
                    missing_fields.append("service address")
                return OpsResult(
                    status=OpsStatus.NEEDS_HUMAN,
                    message=f"No available slots found. To schedule your {service_type.name.lower()}, I'll need: {', '.join(missing_fields)}.",
                    requires_human=True,
                    missing_fields=missing_fields,
                    data={
                        "availability_check": True,
                        "service_type": service_type.name,
                        "duration_minutes": duration_minutes,
                    },
                )

            # Return one or two slots; prompt asks which works better
            next_available_slots = [
                {"start": s.start.isoformat(), "end": s.end.isoformat(), "technician_id": tech_id}
                for s in slots
            ]
            slot_time_strs = [s.start.strftime("%A, %B %d at %I:%M %p") for s in slots]
            if len(slot_time_strs) == 2:
                message = f"I can schedule your {service_type.name.lower()}. I have {slot_time_strs[0]} or {slot_time_strs[1]}. Which works better for you?"
            else:
                message = f"I can schedule your {service_type.name.lower()}. The next available slot is {slot_time_strs[0]}. To book this appointment, I'll need: "
            missing_fields = []
            if not has_identity:
                missing_fields.append("contact information (phone, email, or name)")
            if not has_location:
                missing_fields.append("service address")
            if missing_fields:
                message += ", ".join(missing_fields) + "."
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message=message,
                requires_human=True,
                missing_fields=missing_fields,
                data={
                    "availability_check": True,
                    "next_available_slots": next_available_slots,
                    "next_available_slot": next_available_slots[0] if next_available_slots else None,
                    "service_type": service_type.name,
                    "duration_minutes": duration_minutes,
                },
            )
        except Exception as e:
            logger.exception(f"Error checking availability: {e}")
            return OpsResult(
                status=OpsStatus.ERROR,
                message="I had trouble checking availability. A representative will contact you.",
                requires_human=True,
            )
    
    # Full scheduling mode - create appointment (we have identity and location)
    try:
        # Create appointment service
        appointment_service = await create_appointment_service()
        
        # Look for existing partner (for linking); use returning customer if present
        lead_service = await create_lead_service()
        returning = (command.metadata or {}).get("_returning_customer")
        existing_partner_id = returning.get("partner_id") if isinstance(returning, dict) else None
        partner_id = await lead_service.ensure_partner(
            phone=entities.phone,
            email=entities.email,
            name=entities.full_name,
            address=entities.address,
            city=entities.city,
            zip_code=entities.zip_code,
            existing_partner_id=existing_partner_id,
        )
        
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
        
        tech_id = tech_id or "junior"
        now = datetime.now()
        # Use timezone-aware now for comparisons (avoid naive vs aware)
        now_aware = now.astimezone() if now.tzinfo else now.replace(tzinfo=datetime.now().astimezone().tzinfo)
        preferred_start = now_aware + timedelta(hours=2)  # Default: 2 hours from now
        
        # Try to parse preferred time if provided
        if entities.preferred_time_windows:
            preferred_start = now_aware + timedelta(hours=4)  # Default fallback
        
        chosen_slot_start = command.metadata.get("chosen_slot_start") if command.metadata else None
        slot = None
        
        if chosen_slot_start:
            # Customer chose one of the two offered slots - parse and use it
            try:
                s = chosen_slot_start.strip().replace("Z", "+00:00")
                chosen_start = datetime.fromisoformat(s)
                if chosen_start.tzinfo is None:
                    chosen_start = chosen_start.replace(tzinfo=now_aware.tzinfo)
                chosen_end = chosen_start + timedelta(minutes=duration_minutes)
                if chosen_start >= now_aware:
                    slot = TimeSlot(start=chosen_start, end=chosen_end)
                    logger.info("Schedule appointment: using chosen_slot_start=%s", chosen_slot_start)
                else:
                    logger.warning(
                        "Schedule appointment: chosen_slot_start %s is in the past (now=%s)",
                        chosen_slot_start,
                        now_aware.isoformat(),
                    )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Schedule appointment: failed to parse chosen_slot_start=%r: %s",
                    chosen_slot_start,
                    e,
                )
        
        if not slot:
            # Offer two slots and ask which works better (do not create yet)
            slots = await appointment_service.find_next_two_available_slots(
                tech_id=tech_id,
                after=preferred_start,
                duration_minutes=duration_minutes,
            )
            if slots:
                next_available_slots = [
                    {"start": s.start.isoformat(), "end": s.end.isoformat(), "technician_id": tech_id}
                    for s in slots
                ]
                slot_time_strs = [s.start.strftime("%A, %B %d at %I:%M %p") for s in slots]
                if len(slot_time_strs) == 2:
                    return OpsResult(
                        status=OpsStatus.NEEDS_HUMAN,
                        message=f"I have {slot_time_strs[0]} or {slot_time_strs[1]}. Which works better for you?",
                        requires_human=True,
                        data={
                            "next_available_slots": next_available_slots,
                            "service_type": service_type.name,
                            "duration_minutes": duration_minutes,
                            "choose_then_book": True,
                        },
                    )
                slot = slots[0] if slots else None
        
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


def _parse_natural_date(text: str, base_date: datetime) -> datetime | None:
    """
    Parse natural language date phrases like "next Tuesday", "Tuesday", "10 AM on January 17", etc.
    
    Args:
        text: Natural language date string
        base_date: Base date to calculate relative dates from (usually now)
    
    Returns:
        Parsed datetime or None if unable to parse
    """
    text = text.lower().strip()
    
    # Day of week mapping
    days_of_week = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tues': 1, 'tue': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thurs': 3, 'thur': 3, 'thu': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6,
    }
    
    # Month mapping
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    
    # Calculate next occurrence of a day of week
    def next_day_of_week(target_day: int) -> datetime:
        current_day = base_date.weekday()
        days_ahead = target_day - current_day
        if days_ahead <= 0:  # Target day already passed this week, move to next week
            days_ahead += 7
        return base_date + timedelta(days=days_ahead)
    
    # Parse time (e.g., "10 AM", "2 PM", "10:00 AM", "14:00")
    def parse_time(time_str: str) -> tuple[int, int] | None:
        """Returns (hour, minute) in 24-hour format, or None if can't parse"""
        time_str = time_str.strip()
        # Pattern: "10 AM", "2 PM", "10:00 AM", "14:00"
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            am_pm = time_match.group(3)
            if am_pm:
                if am_pm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif am_pm.lower() == 'am' and hour == 12:
                    hour = 0
            return (hour, minute)
        return None
    
    # Try to parse specific date with time (e.g., "10 AM on January 17", "January 17 at 10 AM", "17 jan at 10 AM")
    # Pattern 1: "10 AM on January 17" or "10 AM on 17 jan"
    date_time_match = re.search(r'(\d{1,2}\s*(?:am|pm))\s+on\s+((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)', text, re.IGNORECASE)
    if date_time_match:
        time_str = date_time_match.group(1)
        date_str = date_time_match.group(2)
        parsed_time = parse_time(time_str)
        if parsed_time:
            # Parse date
            date_parts = date_str.lower().split()
            if len(date_parts) == 2:
                month_str = date_parts[0]
                day_str = date_parts[1]
                if month_str in months:
                    try:
                        day = int(day_str)
                        month = months[month_str]
                        year = base_date.year
                        # If date is in the past, assume next year
                        if month < base_date.month or (month == base_date.month and day < base_date.day):
                            year = base_date.year + 1
                        return datetime(year, month, day, parsed_time[0], parsed_time[1], 0, 0)
                    except ValueError:
                        pass
    
    # Pattern 2: "January 17 at 10 AM" or "17 jan at 10 AM"
    date_time_match2 = re.search(r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)\s+at\s+(\d{1,2}\s*(?:am|pm))', text, re.IGNORECASE)
    if date_time_match2:
        date_str = date_time_match2.group(1)
        time_str = date_time_match2.group(2)
        parsed_time = parse_time(time_str)
        if parsed_time:
            date_parts = date_str.lower().split()
            if len(date_parts) == 2:
                month_str = date_parts[0]
                day_str = date_parts[1]
                if month_str in months:
                    try:
                        day = int(day_str)
                        month = months[month_str]
                        year = base_date.year
                        if month < base_date.month or (month == base_date.month and day < base_date.day):
                            year = base_date.year + 1
                        return datetime(year, month, day, parsed_time[0], parsed_time[1], 0, 0)
                    except ValueError:
                        pass
                # Try reverse order: "17 jan"
                elif date_parts[1] in months:
                    month_str = date_parts[1]
                    day_str = date_parts[0]
                    try:
                        day = int(day_str)
                        month = months[month_str]
                        year = base_date.year
                        if month < base_date.month or (month == base_date.month and day < base_date.day):
                            year = base_date.year + 1
                        return datetime(year, month, day, parsed_time[0], parsed_time[1], 0, 0)
                    except ValueError:
                        pass
    
    # Check for "next [day]" pattern
    next_match = re.search(r'next\s+(\w+)', text)
    if next_match:
        day_name = next_match.group(1).lower()
        if day_name in days_of_week:
            target_day = days_of_week[day_name]
            result = next_day_of_week(target_day)
            # Try to parse time if provided
            time_match = re.search(r'(\d{1,2}\s*(?:am|pm))', text)
            if time_match:
                parsed_time = parse_time(time_match.group(1))
                if parsed_time:
                    return result.replace(hour=parsed_time[0], minute=parsed_time[1], second=0, microsecond=0)
            return result.replace(hour=base_date.hour, minute=0, second=0, microsecond=0)
    
    # Check for just "[day]" pattern (implies next occurrence)
    for day_name, day_num in days_of_week.items():
        if day_name in text and 'next' not in text and 'this' not in text:
            result = next_day_of_week(day_num)
            # Try to parse time if provided
            time_match = re.search(r'(\d{1,2}\s*(?:am|pm))', text)
            if time_match:
                parsed_time = parse_time(time_match.group(1))
                if parsed_time:
                    return result.replace(hour=parsed_time[0], minute=parsed_time[1], second=0, microsecond=0)
            return result.replace(hour=base_date.hour, minute=0, second=0, microsecond=0)
    
    # Check for "tomorrow"
    if 'tomorrow' in text:
        tomorrow = base_date + timedelta(days=1)
        # Try to parse time if provided
        time_match = re.search(r'(\d{1,2}\s*(?:am|pm))', text)
        if time_match:
            parsed_time = parse_time(time_match.group(1))
            if parsed_time:
                return tomorrow.replace(hour=parsed_time[0], minute=parsed_time[1], second=0, microsecond=0)
        return tomorrow.replace(hour=base_date.hour, minute=0, second=0, microsecond=0)
    
    # Check for "next week"
    if 'next week' in text:
        next_week = base_date + timedelta(days=7)
        return next_week.replace(hour=base_date.hour, minute=0, second=0, microsecond=0)
    
    return None


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
        
        # Parse preferred time from user's natural language
        if entities.preferred_time_windows:
            preferred_time_str = entities.preferred_time_windows[0].lower() if entities.preferred_time_windows else ""
            parsed_date = _parse_natural_date(preferred_time_str, now)
            if parsed_date:
                # Keep the same time of day from existing appointment if possible
                preferred_start = parsed_date.replace(
                    hour=existing_start.hour,
                    minute=existing_start.minute,
                    second=0,
                    microsecond=0
                )
                # If the parsed date is in the past or too soon, move to the next occurrence
                if preferred_start < now:
                    preferred_start += timedelta(days=7)  # Move to next week
                # Ensure at least 2 hours in the future
                if preferred_start < now + timedelta(hours=2):
                    preferred_start = now + timedelta(hours=2)
        
        # Also check if raw_text contains date hints (fallback)
        if not entities.preferred_time_windows and command.raw_text:
            parsed_date = _parse_natural_date(command.raw_text, now)
            if parsed_date:
                # Use the parsed date/time as-is (it already includes the time if specified)
                preferred_start = parsed_date
                if preferred_start < now:
                    # If it's a specific date that passed, try next year
                    if preferred_start.year == now.year:
                        try:
                            preferred_start = preferred_start.replace(year=now.year + 1)
                        except ValueError:  # Leap year issue
                            preferred_start = preferred_start + timedelta(days=365)
                    else:
                        preferred_start += timedelta(days=7)
                if preferred_start < now + timedelta(hours=2):
                    preferred_start = now + timedelta(hours=2)
        
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
        
        # Check if user has provided a preferred time or is just asking for availability
        text_lower = (command.raw_text or "").lower()
        availability_keywords = [
            "next available",
            "next available slot",
            "when is the next",
            "what's the next",
            "check availability",
            "tell me next",
            "show me next",
            "when can you",
            "what time is available",
            "available time",
            "available slot",
        ]
        
        # Check if user provided explicit preferred time (not just asking for availability)
        has_explicit_preferred_time = bool(entities.preferred_time_windows)
        
        # Check if text contains explicit date/time confirmation phrases
        confirmation_keywords = [
            "yes", "confirm", "that works", "sounds good", "reschedule it",
            "move it to", "change it to", "make it", "schedule it for",
            "book it for", "set it for", "put it on"
        ]
        has_confirmation = any(keyword in text_lower for keyword in confirmation_keywords)
        
        is_availability_check = any(keyword in text_lower for keyword in availability_keywords)
        
        # If user hasn't provided explicit preferred time AND hasn't confirmed, show availability and ask
        if not has_explicit_preferred_time and not has_confirmation:
            old_time_str = existing_start.strftime("%A, %B %d at %I:%M %p")
            new_time_str = slot.start.strftime("%A, %B %d at %I:%M %p")
            
            # Get technician info
            tech_name = None
            if tech_id:
                from src.brains.ops.tech_roster import get_technician
                tech = get_technician(tech_id)
                if tech:
                    tech_name = tech.name
            
            response_message = (
                f"Your current appointment is on {old_time_str}. "
                f"The next available slot is {new_time_str}."
            )
            if tech_name:
                response_message += f" {tech_name} would be assigned to your appointment."
            response_message += " Would you like me to reschedule your appointment to this time?"
            
            return OpsResult(
                status=OpsStatus.NEEDS_HUMAN,
                message=response_message,
                requires_human=True,
                data={
                    "existing_appointment_id": event_id,
                    "current_appointment_time": existing_start.isoformat(),
                    "availability_check": True,
                    "next_available_slot": {
                        "start": slot.start.isoformat(),
                        "end": slot.end.isoformat(),
                        "technician_id": tech_id,
                        "technician_name": tech_name,
                    },
                    "contact_phone": entities.phone,
                },
            )
        
        # Update the appointment (user has confirmed or provided explicit preferred time)
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
        
        # Format times for display
        old_time_str = existing_start.strftime("%A, %B %d at %I:%M %p")
        new_time_str = slot.start.strftime("%A, %B %d at %I:%M %p")
        
        # Get technician info for notifications
        tech_name = None
        tech_email = None
        if tech_id:
            from src.brains.ops.tech_roster import get_technician
            tech = get_technician(tech_id)
            if tech:
                tech_name = tech.name
                tech_email = tech.email
        
        # Send SMS confirmation to customer
        if entities.phone:
            try:
                from src.integrations.twilio_sms import send_reschedule_confirmation_sms
                sms_result = await send_reschedule_confirmation_sms(
                    to_phone=entities.phone,
                    customer_name=entities.full_name,
                    new_time_str=new_time_str,
                    tech_name=tech_name,
                )
                logger.info(f"Reschedule SMS sent: {sms_result.get('status')}")
            except Exception as sms_err:
                logger.error(f"Failed to send reschedule SMS: {sms_err}")
        
        # Send email notification to technician
        if tech_email and tech_name:
            try:
                from src.integrations.email_notifications import create_email_service_from_settings
                service = create_email_service_from_settings()
                if service:
                    customer_name = entities.full_name or "Customer"
                    subject = f"Appointment Rescheduled - {customer_name}"
                    html_body = (
                        f"<h2>Appointment Rescheduled</h2>"
                        f"<p><strong>Customer:</strong> {customer_name}</p>"
                        f"<p><strong>Phone:</strong> {entities.phone or 'N/A'}</p>"
                        f"<p><strong>Previous Time:</strong> {old_time_str}</p>"
                        f"<p><strong>New Time:</strong> {new_time_str}</p>"
                        f"<p><strong>Assigned To:</strong> {tech_name}</p>"
                        f"<p>Please update your calendar accordingly.</p>"
                    )
                    text_body = (
                        f"Appointment Rescheduled\n\n"
                        f"Customer: {customer_name}\n"
                        f"Phone: {entities.phone or 'N/A'}\n"
                        f"Previous Time: {old_time_str}\n"
                        f"New Time: {new_time_str}\n"
                        f"Assigned To: {tech_name}\n\n"
                        f"Please update your calendar accordingly."
                    )
                    email_result = service.send_email(
                        to=tech_email,
                        subject=subject,
                        body_html=html_body,
                        body_text=text_body,
                    )
                    logger.info(f"Reschedule notification sent to technician {tech_name} ({tech_email}): {email_result.get('status')}")
            except Exception as email_err:
                logger.error(f"Failed to send technician notification: {email_err}")
        
        # Build response message showing both old and new times
        response_message = (
            f"I found your appointment scheduled for {old_time_str}. "
            f"I've rescheduled it to {new_time_str}."
        )
        if tech_name:
            response_message += f" {tech_name} is still assigned to your appointment."
        response_message += " A confirmation has been sent."
        
        return OpsResult(
            status=OpsStatus.SUCCESS,
            message=response_message,
            requires_human=False,
            data={
                "appointment_id": event_id,
                "scheduled_time": slot.start.isoformat(),
                "scheduled_time_end": slot.end.isoformat(),
                "previous_time": existing_start.isoformat(),
                "previous_time_str": old_time_str,
                "technician": {
                    "id": tech_id,
                    "name": tech_name,
                    "email": tech_email,
                } if tech_id else None,
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
        
        # Get appointment details for notifications
        appointment_start_str = appointment.get("start")
        appointment_name = appointment.get("name", "Appointment")
        appointment_location = appointment.get("location")
        tech_user_id = appointment.get("user_id")
        
        # Parse appointment datetime
        appointment_datetime = None
        if appointment_start_str:
            try:
                appointment_datetime = datetime.fromisoformat(appointment_start_str.replace("Z", "+00:00"))
                if appointment_datetime.tzinfo:
                    appointment_datetime = appointment_datetime.replace(tzinfo=None)
            except Exception as e:
                logger.warning(f"Failed to parse appointment datetime: {e}")
        
        # Check if cancellation is within 24 hours (cancellation policy applies)
        cancellation_within_24h = False
        if appointment_datetime:
            hours_until_appointment = (appointment_datetime - now).total_seconds() / 3600
            cancellation_within_24h = 0 < hours_until_appointment < 24
        
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
        
        # Initialize response data
        response_data = {
            "appointment_id": event_id,
            "cancelled": True,
            "lead_id": lead_id,
            "cancellation_within_24h": cancellation_within_24h,
            "appointment_datetime": appointment_start_str,
            "appointment_name": appointment_name,
        }
        
        # Send cancellation confirmation SMS to customer (fire-and-forget)
        if entities.phone:
            try:
                from src.integrations.twilio_sms import create_twilio_client_from_settings
                sms_client = create_twilio_client_from_settings()
                if sms_client:
                    # Format appointment date/time for SMS
                    if appointment_datetime:
                        appointment_date = appointment_datetime.strftime("%A, %B %d")
                        appointment_time = appointment_datetime.strftime("%I:%M %p")
                        sms_body = f"HVACR FINEST: Your appointment on {appointment_date} at {appointment_time} has been cancelled. If you need to reschedule, please call us at (972) 372-4458."
                    else:
                        sms_body = f"HVACR FINEST: Your appointment has been cancelled. If you need to reschedule, please call us at (972) 372-4458."
                    
                    # Send SMS asynchronously (fire-and-forget)
                    import asyncio
                    asyncio.create_task(sms_client.send_sms(entities.phone, sms_body))
                    logger.info(f"Scheduled cancellation confirmation SMS to {entities.phone}")
                    response_data["sms_scheduled"] = True
            except Exception as e:
                logger.warning(f"Failed to send cancellation SMS: {e}")
        
        # Send notification email to dispatch team (fire-and-forget)
        try:
            from src.integrations.email_notifications import send_new_lead_notification
            
            # Format appointment details for email
            service_type = f"Cancelled: {appointment_name}"
            if appointment_datetime:
                appointment_date = appointment_datetime.strftime("%A, %B %d, %Y")
                appointment_time = appointment_datetime.strftime("%I:%M %p")
                service_type += f" (was scheduled for {appointment_date} at {appointment_time})"
            
            # Send notification asynchronously (fire-and-forget)
            import asyncio
            asyncio.create_task(send_new_lead_notification(
                customer_name=entities.full_name,
                phone=entities.phone,
                email=entities.email,
                address=entities.address,
                service_type=service_type,
                priority_label="Cancellation",
                assigned_technician=None,  # Appointment cancelled, no tech assigned
                lead_id=lead_id,
            ))
            logger.info(f"Scheduled cancellation notification email for appointment {event_id}")
            response_data["email_scheduled"] = True
        except Exception as e:
            logger.warning(f"Failed to send cancellation notification email: {e}")
        
        # Optionally update linked lead status (simplified - could be enhanced)
        if lead_id:
            try:
                # Could update lead stage to "cancelled" or "lost" here
                # For now, just log it
                logger.info(f"Appointment {event_id} cancelled, linked to lead {lead_id}")
            except Exception as e:
                logger.warning(f"Failed to update lead {lead_id} after cancellation: {e}")
        
        # Add cancellation policy info
        if cancellation_within_24h:
            response_data["cancellation_policy_applies"] = True
            response_data["cancellation_policy_note"] = "Cancellation within 24 hours - policy may apply"
        
        return OpsResult(
            status=OpsStatus.SUCCESS,
            message="Your appointment has been cancelled. You will receive a confirmation shortly.",
            requires_human=False,
            data=response_data,
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

