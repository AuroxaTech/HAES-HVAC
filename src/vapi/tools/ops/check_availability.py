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
from src.brains.ops.scheduling_rules import (
    BUSINESS_START,
    OPERATING_DAYS,
    SAME_DAY_DISPATCH_CUTOFF,
    get_earliest_slot_by_urgency,
)

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


def _as_naive_local(dt: datetime) -> datetime:
    """Normalize datetime to naive local time for safe comparisons."""
    if dt.tzinfo:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def _next_business_day_start(now: datetime) -> datetime:
    """Return the next operating day at dispatch start hour."""
    next_start = now.replace(
        hour=BUSINESS_START.hour,
        minute=BUSINESS_START.minute,
        second=0,
        microsecond=0,
    ) + timedelta(days=1)
    while next_start.weekday() not in OPERATING_DAYS:
        next_start += timedelta(days=1)
    return next_start


def _dispatch_search_start(now: datetime, allow_same_day_after_cutoff: bool) -> datetime:
    """
    Compute earliest dispatchable search time.
    - Same-day dispatch cutoff: 5 PM (unless override is enabled)
    - Earliest dispatch start: 8 AM
    """
    if not allow_same_day_after_cutoff and now.time() >= SAME_DAY_DISPATCH_CUTOFF:
        return _next_business_day_start(now)

    baseline = now + timedelta(hours=2)
    day_start = now.replace(
        hour=BUSINESS_START.hour,
        minute=BUSINESS_START.minute,
        second=0,
        microsecond=0,
    )
    if baseline < day_start:
        baseline = day_start
    while baseline.weekday() not in OPERATING_DAYS:
        baseline = _next_business_day_start(baseline)
    return baseline


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
        - preferred_time (optional): Earliest time for slots (e.g. "15:00" or "15" for after 3pm).
          Use when customer needs later-in-day slots (e.g. "I work until 3pm", "something after work").
        - urgency (optional): "emergency", "urgent", or "routine" — pass the value the customer stated.
          emergency=same-day slots, urgent=2-3 days out, routine=~7 days out.
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
        
        zip_code = parameters.get("zip_code")
        
        # Determine preferred start time (never offer past time windows)
        now = datetime.now()
        allow_same_day_after_cutoff = bool(parameters.get("allow_same_day_after_cutoff"))
        minimum_start = _dispatch_search_start(
            now,
            allow_same_day_after_cutoff=allow_same_day_after_cutoff,
        )
        preferred_start = minimum_start

        # Apply urgency-based slot targeting (emergency=same day, urgent=2-3 days out, routine=~7 days out)
        urgency_raw = parameters.get("urgency")
        if urgency_raw:
            urgency_earliest = get_earliest_slot_by_urgency(minimum_start, str(urgency_raw).strip())
            preferred_start = max(preferred_start, urgency_earliest)
        
        # Parse preferred_date if provided
        if parameters.get("preferred_date"):
            try:
                # Try to parse date string
                preferred_date_str = parameters["preferred_date"]
                # Simple parsing - could be enhanced
                parsed_preferred = datetime.fromisoformat(preferred_date_str.replace("Z", "+00:00"))
                parsed_preferred = _as_naive_local(parsed_preferred)
                # Date-only inputs parse as midnight; move them to business start.
                if len(preferred_date_str.strip()) <= 10:
                    parsed_preferred = parsed_preferred.replace(
                        hour=BUSINESS_START.hour,
                        minute=BUSINESS_START.minute,
                        second=0,
                        microsecond=0,
                    )
                preferred_start = max(parsed_preferred, minimum_start)
            except Exception:
                pass

        # Parse preferred_time if provided (e.g. "15:00" or "15" for after 3pm - use when customer needs later-in-day slots)
        preferred_time_raw = parameters.get("preferred_time")
        if preferred_time_raw:
            try:
                pt = str(preferred_time_raw).strip()
                hour, minute = BUSINESS_START.hour, 0
                if ":" in pt:
                    parts = pt.split(":")
                    hour = int(parts[0]) if parts[0].isdigit() else hour
                    minute = int(parts[1][:2]) if len(parts) > 1 and parts[1][:2].isdigit() else 0
                elif pt.isdigit():
                    h = int(pt)
                    hour = h + 12 if 1 <= h <= 7 else h  # 3->15 (3pm), 5->17 (5pm)
                hour = max(8, min(20, hour))
                candidate = preferred_start.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if candidate >= minimum_start:
                    preferred_start = candidate
            except Exception:
                pass
        
        # Collect slots from all technicians; sort by start; take two earliest across everyone.
        candidates = await appointment_service.get_live_technicians()
        all_slot_entries: list[tuple[datetime, Any, str]] = []  # (start_naive, slot, tech_id)
        for candidate in candidates:
            candidate_id = str(candidate.get("id"))
            raw_slots = await appointment_service.find_next_two_available_slots(
                tech_id=candidate_id,
                after=preferred_start,
                duration_minutes=duration_minutes,
            )
            valid_slots = [
                s for s in (raw_slots or []) if _as_naive_local(s.start) >= minimum_start
            ]
            for s in valid_slots:
                all_slot_entries.append((_as_naive_local(s.start), s, candidate_id))
        all_slot_entries.sort(key=lambda x: x[0])
        first_two = all_slot_entries[:2]
        slots = [entry[1] for entry in first_two]
        slot_tech_ids = [entry[2] for entry in first_two]

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
            {
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "technician_id": slot_tech_ids[i],
            }
            for i, s in enumerate(slots)
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
