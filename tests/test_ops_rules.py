"""
HAES HVAC - OPS Brain Rules Tests

Unit tests for OPS brain emergency and scheduling rules.
"""

import pytest
from datetime import datetime, time, timedelta

from src.hael.schema import UrgencyLevel
from src.brains.ops.emergency_rules import qualify_emergency
from src.brains.ops.scheduling_rules import (
    MIN_TIME_BETWEEN_APPOINTMENTS_MINUTES,
    is_business_hours,
    calculate_travel_time,
    validate_scheduling_request,
    TimeSlot,
    SlotStatus,
)


class TestEmergencyRules:
    """Tests for emergency qualification rules."""

    def test_gas_leak_is_emergency(self):
        """Gas leak should always be emergency."""
        result = qualify_emergency(
            problem_description="I smell gas coming from my furnace",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert result.is_emergency is True
        assert "gas" in result.reason.lower()

    def test_carbon_monoxide_is_emergency(self):
        """Carbon monoxide should always be emergency."""
        result = qualify_emergency(
            problem_description="My CO detector is going off",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert result.is_emergency is True

    def test_burning_smell_is_emergency(self):
        """Burning smell should always be emergency."""
        result = qualify_emergency(
            problem_description="There's a burning smell from my AC",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert result.is_emergency is True

    def test_flooding_is_emergency(self):
        """Water damage should always be emergency."""
        result = qualify_emergency(
            problem_description="My AC is flooding the basement",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert result.is_emergency is True

    def test_no_heat_below_threshold_is_emergency(self):
        """No heat with cold temperature should be emergency."""
        result = qualify_emergency(
            problem_description="My heating is not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=45,  # Below 55°F threshold
        )
        assert result.is_emergency is True

    def test_no_heat_above_threshold_not_emergency(self):
        """No heat with warm temperature should not be emergency."""
        result = qualify_emergency(
            problem_description="My heating is not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=65,  # Above 55°F threshold
        )
        assert result.is_emergency is False

    def test_no_ac_above_threshold_is_emergency(self):
        """No AC with hot temperature should be emergency."""
        result = qualify_emergency(
            problem_description="My AC is not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=90,  # Above 85°F threshold
        )
        assert result.is_emergency is True

    def test_no_ac_below_threshold_not_emergency(self):
        """No AC with moderate temperature should not be emergency."""
        result = qualify_emergency(
            problem_description="My AC is not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=75,  # Below 85°F threshold
        )
        assert result.is_emergency is False

    def test_hael_emergency_urgency_is_emergency(self):
        """HAEL emergency urgency should be emergency."""
        result = qualify_emergency(
            problem_description="Standard repair needed",
            urgency_level=UrgencyLevel.EMERGENCY,
        )
        assert result.is_emergency is True

    def test_standard_request_not_emergency(self):
        """Standard request should not be emergency."""
        result = qualify_emergency(
            problem_description="My AC needs a tune-up",
            urgency_level=UrgencyLevel.LOW,
        )
        assert result.is_emergency is False


class TestSchedulingRules:
    """Tests for scheduling rules."""

    def test_business_hours_weekday_morning(self):
        """Weekday morning should be business hours."""
        dt = datetime(2026, 1, 8, 10, 0)  # Thursday 10 AM
        assert is_business_hours(dt) is True

    def test_business_hours_weekday_evening(self):
        """Weekday evening after close should not be business hours."""
        dt = datetime(2026, 1, 8, 19, 0)  # Thursday 7 PM
        assert is_business_hours(dt) is False

    def test_business_hours_sunday(self):
        """Sunday should not be business hours."""
        dt = datetime(2026, 1, 11, 10, 0)  # Sunday 10 AM
        assert is_business_hours(dt) is False

    def test_travel_time_includes_buffer(self):
        """Travel time should include 15% buffer."""
        base = 30
        travel = calculate_travel_time(None, None, base)
        expected = base + int(base * 15 / 100)
        assert travel == expected

    def test_min_buffer_between_appointments(self):
        """Minimum buffer between appointments is 30 minutes."""
        assert MIN_TIME_BETWEEN_APPOINTMENTS_MINUTES == 30

    def test_scheduling_past_time_fails(self):
        """Cannot schedule in the past."""
        past_time = datetime.now() - timedelta(hours=1)
        result = validate_scheduling_request(
            requested_start=past_time,
            duration_minutes=60,
        )
        assert result.success is False
        assert "past" in result.reason.lower()

    def test_scheduling_conflict_fails(self):
        """Scheduling conflict should fail."""
        now = datetime.now() + timedelta(days=1)
        # Create at 10 AM on a weekday
        start = now.replace(hour=10, minute=0, second=0, microsecond=0)
        while start.weekday() > 5:  # Skip weekend
            start += timedelta(days=1)
        
        existing = [
            TimeSlot(
                start=start,
                end=start + timedelta(hours=2),
                status=SlotStatus.BOOKED,
                technician_id="tech1",
            )
        ]
        
        result = validate_scheduling_request(
            requested_start=start + timedelta(minutes=30),
            duration_minutes=60,
            technician_id="tech1",
            existing_bookings=existing,
        )
        assert result.success is False
        assert "conflict" in result.reason.lower()

