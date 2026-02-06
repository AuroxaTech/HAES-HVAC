"""
HAES HVAC - OPS Brain Scheduling Rules

Scheduling constraints and slot management from RDD.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any


# Scheduling constants from RDD
MIN_TIME_BETWEEN_APPOINTMENTS_MINUTES = 30
TRAVEL_TIME_BUFFER_PERCENT = 15
DEFAULT_TRAVEL_TIME_MINUTES = 30

# Business hours from RDD
BUSINESS_START = time(8, 0)   # 8:00 AM
BUSINESS_END = time(18, 0)    # 6:00 PM

# Days of operation (Monday=0, Sunday=6)
OPERATING_DAYS = [0, 1, 2, 3, 4, 5]  # Mon-Sat


class SlotStatus(str, Enum):
    """Scheduling slot status."""
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"
    PAST = "past"


@dataclass
class TimeSlot:
    """A schedulable time slot."""
    start: datetime
    end: datetime
    status: SlotStatus = SlotStatus.AVAILABLE
    technician_id: str | None = None
    job_id: str | None = None


@dataclass
class SchedulingResult:
    """Result of scheduling attempt."""
    success: bool
    slot: TimeSlot | None
    reason: str
    alternatives: list[TimeSlot]


def is_business_hours(dt: datetime) -> bool:
    """Check if datetime falls within business hours."""
    if dt.weekday() not in OPERATING_DAYS:
        return False
    
    return BUSINESS_START <= dt.time() <= BUSINESS_END


def calculate_travel_time(
    from_zip: str | None,
    to_zip: str | None,
    base_minutes: int = DEFAULT_TRAVEL_TIME_MINUTES,
) -> int:
    """
    Calculate travel time between locations.
    
    Note: GPS integration not available yet.
    Using base time + buffer for now.
    
    Args:
        from_zip: Origin ZIP code
        to_zip: Destination ZIP code
        base_minutes: Base travel time estimate
        
    Returns:
        Travel time in minutes with buffer
    """
    # Apply 15% buffer per RDD
    buffer = int(base_minutes * TRAVEL_TIME_BUFFER_PERCENT / 100)
    return base_minutes + buffer


def calculate_slot_end(
    start: datetime,
    service_duration_minutes: int,
    include_travel: bool = True,
) -> datetime:
    """
    Calculate slot end time.
    
    Args:
        start: Slot start time
        service_duration_minutes: Expected service duration
        include_travel: Whether to include travel buffer
        
    Returns:
        Slot end datetime
    """
    duration = service_duration_minutes
    
    if include_travel:
        duration += calculate_travel_time(None, None)
    
    # Add minimum buffer between appointments
    duration += MIN_TIME_BETWEEN_APPOINTMENTS_MINUTES
    
    return start + timedelta(minutes=duration)


def get_next_available_slot(
    after: datetime,
    duration_minutes: int,
    technician_id: str | None = None,
    existing_bookings: list[TimeSlot] | None = None,
) -> TimeSlot | None:
    """
    Find the next available scheduling slot.
    
    Args:
        after: Find slots after this time
        duration_minutes: Required duration
        technician_id: Filter by technician
        existing_bookings: Current bookings to avoid
        
    Returns:
        Next available slot or None
    """
    existing_bookings = existing_bookings or []
    
    # Start from next business day if needed
    current = after
    if not is_business_hours(current):
        # Move to next business day start
        current = current.replace(
            hour=BUSINESS_START.hour,
            minute=BUSINESS_START.minute,
            second=0,
            microsecond=0,
        )
        if current <= after:
            current += timedelta(days=1)
        
        # Skip to operating day
        while current.weekday() not in OPERATING_DAYS:
            current += timedelta(days=1)
    
    # Find slot
    slot_end = calculate_slot_end(current, duration_minutes)
    
    # Check for conflicts
    for booking in existing_bookings:
        if booking.technician_id != technician_id:
            continue
        
        # Check overlap
        if current < booking.end and slot_end > booking.start:
            # Move past this booking
            current = booking.end + timedelta(minutes=MIN_TIME_BETWEEN_APPOINTMENTS_MINUTES)
            slot_end = calculate_slot_end(current, duration_minutes)
    
    # Verify still in business hours
    if not is_business_hours(current):
        return None
    
    return TimeSlot(
        start=current,
        end=slot_end,
        status=SlotStatus.AVAILABLE,
        technician_id=technician_id,
    )


def get_next_two_available_slots(
    after: datetime,
    duration_minutes: int,
    technician_id: str | None = None,
    existing_bookings: list[TimeSlot] | None = None,
) -> list[TimeSlot]:
    """
    Find the next two distinct available scheduling slots.
    Used to offer the customer a choice (e.g. "Tuesday 10 AM or Wednesday 2 PM").

    Args:
        after: Find slots after this time
        duration_minutes: Required duration per slot
        technician_id: Filter by technician
        existing_bookings: Current bookings to avoid

    Returns:
        List of 0, 1, or 2 TimeSlots (at most two).
    """
    existing_bookings = existing_bookings or []
    slots: list[TimeSlot] = []
    cursor = after

    for _ in range(2):
        slot = get_next_available_slot(
            cursor,
            duration_minutes,
            technician_id=technician_id,
            existing_bookings=existing_bookings,
        )
        if not slot:
            break
        slots.append(slot)
        # Next slot starts after this one ends, plus buffer
        cursor = slot.end + timedelta(minutes=MIN_TIME_BETWEEN_APPOINTMENTS_MINUTES)

    return slots


def validate_scheduling_request(
    requested_start: datetime,
    duration_minutes: int,
    technician_id: str | None = None,
    existing_bookings: list[TimeSlot] | None = None,
) -> SchedulingResult:
    """
    Validate a scheduling request.
    
    Args:
        requested_start: Requested start time
        duration_minutes: Required duration
        technician_id: Assigned technician
        existing_bookings: Current bookings
        
    Returns:
        SchedulingResult with success status and alternatives
    """
    existing_bookings = existing_bookings or []
    
    # Check if in past (most critical check - do first)
    if requested_start < datetime.now():
        return SchedulingResult(
            success=False,
            slot=None,
            reason="Cannot schedule in the past",
            alternatives=[],
        )
    
    # Check if in business hours
    if not is_business_hours(requested_start):
        next_slot = get_next_available_slot(
            requested_start,
            duration_minutes,
            technician_id,
            existing_bookings,
        )
        return SchedulingResult(
            success=False,
            slot=None,
            reason="Requested time is outside business hours",
            alternatives=[next_slot] if next_slot else [],
        )
    
    slot_end = calculate_slot_end(requested_start, duration_minutes)
    
    # Check for conflicts
    for booking in existing_bookings:
        if technician_id and booking.technician_id != technician_id:
            continue
        
        if requested_start < booking.end and slot_end > booking.start:
            next_slot = get_next_available_slot(
                booking.end,
                duration_minutes,
                technician_id,
                existing_bookings,
            )
            return SchedulingResult(
                success=False,
                slot=None,
                reason=f"Time conflict with existing booking",
                alternatives=[next_slot] if next_slot else [],
            )
    
    # Success
    return SchedulingResult(
        success=True,
        slot=TimeSlot(
            start=requested_start,
            end=slot_end,
            status=SlotStatus.BOOKED,
            technician_id=technician_id,
        ),
        reason="Slot available",
        alternatives=[],
    )

