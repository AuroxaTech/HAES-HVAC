"""
HAES HVAC - Check Availability Tool

Direct Vapi tool for checking available appointment slots.
"""

import logging
from typing import Any
from datetime import datetime, timedelta

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.hael.schema import (
    Channel,
    Entity,
    HaelCommand,
    Intent,
    Brain,
)
from src.brains.ops import handle_ops_command
from src.brains.ops.schema import OpsStatus
from src.utils.request_id import generate_request_id
from src.integrations.odoo_appointments import create_appointment_service
from src.brains.ops.service_catalog import infer_service_type_from_description

logger = logging.getLogger(__name__)

# 4-hour block display: "8 AM", "12 PM" (no leading zero, no minutes when :00)
def _format_time_block(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{h} {ampm}"


def _format_slot_as_4hr_block(start: datetime, end: datetime) -> str:
    """Format a slot as 'Monday, January 27, 8 AM to 12 PM' (4-hour block)."""
    day_part = start.strftime("%A, %B %d")
    return f"{day_part}, {_format_time_block(start)} to {_format_time_block(end)}"


async def handle_check_availability(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle check_availability tool call.
    
    Parameters:
        - service_type (optional): Service type description
        - preferred_date (optional): Preferred date for availability
        - property_type (optional): "residential", "commercial", "property_management"
        - zip_code (optional): ZIP code for technician assignment
    """
    handler = BaseToolHandler("check_availability")
    
    # Infer service type
    service_desc = parameters.get("service_type") or conversation_context or "General service"
    service_type = infer_service_type_from_description(service_desc)
    duration_minutes = service_type.duration_minutes_max
    
    try:
        appointment_service = await create_appointment_service()
        
        # Determine technician
        tech_id = "junior"  # Default
        zip_code = parameters.get("zip_code")
        if zip_code:
            from src.brains.ops.tech_roster import assign_technician
            tech = assign_technician(
                zip_code=zip_code,
                is_emergency=False,
                is_commercial=parameters.get("property_type") == "commercial",
            )
            if tech:
                tech_id = tech.id
        
        # Determine preferred start time
        now = datetime.now()
        preferred_start = now + timedelta(hours=2)
        
        # Parse preferred_date if provided
        if parameters.get("preferred_date"):
            try:
                # Try to parse date string
                preferred_date_str = parameters["preferred_date"]
                # Simple parsing - could be enhanced
                preferred_start = datetime.fromisoformat(preferred_date_str.replace("Z", "+00:00"))
            except:
                pass
        
        # Find next available slots (offer at most 2 so agent only says 2)
        raw_slots = await appointment_service.find_next_two_available_slots(
            tech_id=tech_id,
            after=preferred_start,
            duration_minutes=duration_minutes,
        )
        slots = (raw_slots or [])[:2]  # Cap at 2; prompt/agent then only need to say 2
        
        if not slots:
            return ToolResponse(
                speak=f"I couldn't find an available slot for {service_type.name.lower()} at this time. Would you like me to check with our scheduling team?",
                action="needs_human",
                data={
                    "availability_check": True,
                    "service_type": service_type.name,
                    "no_slots_available": True,
                },
            )
        
        next_available_slots = [
            {"start": s.start.isoformat(), "end": s.end.isoformat(), "technician_id": tech_id}
            for s in slots
        ]
        # Format each slot as a 4-hour block: "Monday, January 27, 8 AM to 12 PM"
        slot_time_strs = [_format_slot_as_4hr_block(s.start, s.end) for s in slots]
        if len(slot_time_strs) >= 2:
            speak = f"I have {slot_time_strs[0]} or {slot_time_strs[1]} for {service_type.name.lower()}. Which works better for you?"
        elif len(slot_time_strs) == 1:
            speak = f"The next available slot for {service_type.name.lower()} is {slot_time_strs[0]}. Would you like me to schedule this appointment?"
        else:
            return ToolResponse(
                speak=f"I couldn't find an available slot for {service_type.name.lower()} at this time. Would you like me to check with our scheduling team?",
                action="needs_human",
                data={
                    "availability_check": True,
                    "service_type": service_type.name,
                    "no_slots_available": True,
                },
            )
        
        return ToolResponse(
            speak=speak,
            action="needs_human",  # Needs confirmation before scheduling
            data={
                "availability_check": True,
                "next_available_slots": next_available_slots,
                "next_available_slot": next_available_slots[0] if next_available_slots else None,
                "service_type": service_type.name,
                "duration_minutes": duration_minutes,
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
