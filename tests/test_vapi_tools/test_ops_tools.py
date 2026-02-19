"""
HAES HVAC - OPS Tools Tests

Tests for OPS brain tools:
- create_service_request
- schedule_appointment
- check_availability
- reschedule_appointment
- cancel_appointment
- check_appointment_status
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.vapi.tools.ops.create_service_request import handle_create_service_request
from src.vapi.tools.ops.schedule_appointment import handle_schedule_appointment
from src.vapi.tools.ops.check_availability import handle_check_availability
from src.vapi.tools.ops.reschedule_appointment import handle_reschedule_appointment
from src.vapi.tools.ops.cancel_appointment import handle_cancel_appointment
from src.vapi.tools.ops.check_appointment_status import handle_check_appointment_status


class TestCreateServiceRequest:
    """Tests for create_service_request tool."""
    
    @pytest.mark.asyncio
    async def test_create_service_request_requires_phone(self):
        """Should require phone number."""
        parameters = {
            "address": "123 Main St, Dallas, TX 75201",
            "issue_description": "AC not working",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_001",
            parameters=parameters,
            call_id="call_001",
        )
        
        assert response.action == "needs_human"
        assert "phone" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    async def test_create_service_request_requires_address(self):
        """Should require address."""
        parameters = {
            "phone": "+19725551234",
            "issue_description": "AC not working",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_002",
            parameters=parameters,
            call_id="call_002",
        )
        
        assert response.action == "needs_human"
        assert "address" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    async def test_create_service_request_requires_issue_description(self):
        """Should require issue description."""
        parameters = {
            "phone": "+19725551234",
            "address": "123 Main St, Dallas, TX 75201",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_003",
            parameters=parameters,
            call_id="call_003",
        )
        
        assert response.action == "needs_human"
        assert "issue_description" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.create_service_request.create_lead_service")
    @patch("src.vapi.tools.ops.create_service_request.handle_ops_command")
    async def test_create_service_request_success(self, mock_ops_handler, mock_lead_service):
        """Should successfully create service request."""
        # Mock OPS handler
        from src.brains.ops.schema import OpsResult, OpsStatus
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Service request created successfully",
            requires_human=False,
            data={"lead_id": 123, "assigned_technician": {"id": "junior", "name": "Junior"}},
        )
        
        parameters = {
            "phone": "+19725551234",
            "address": "123 Main St, DeSoto, TX 75115",
            "issue_description": "AC not cooling properly",
            "customer_name": "John Doe",
            "urgency": "medium",
            "property_type": "residential",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_004",
            parameters=parameters,
            call_id="call_004",
        )
        
        assert response.action == "completed"
        assert response.speak is not None and len(response.speak) > 0
        assert response.data.get("lead_id") is not None
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.create_service_request.handle_ops_command")
    async def test_create_service_request_emergency(self, mock_ops_handler):
        """Should handle emergency requests correctly."""
        from src.brains.ops.schema import OpsResult, OpsStatus
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Emergency service request created",
            requires_human=False,
            data={
                "lead_id": 456,
                "is_emergency": True,
                "priority_label": "CRITICAL",
                "eta_window_hours_min": 1.5,
                "eta_window_hours_max": 3.0,
            },
        )
        
        parameters = {
            "phone": "+19725559999",
            "address": "456 Emergency St, DeSoto, TX 75115",
            "issue_description": "No heat, it's freezing!",
            "indoor_temperature_f": 50,
            "urgency": "emergency",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_005",
            parameters=parameters,
            call_id="call_005",
        )
        
        assert response.action == "completed"
        assert response.data.get("is_emergency") is True
        assert response.data.get("priority_label") == "CRITICAL"
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.create_service_request.is_within_service_area")
    async def test_create_service_request_out_of_area(self, mock_service_area):
        """Should handle out-of-service-area requests."""
        # is_within_service_area returns (bool, str | None)
        mock_service_area.return_value = (False, "We service within 35 miles of downtown Dallas")
        
        parameters = {
            "phone": "+19725551234",
            "address": "123 Main St, Austin, TX 78701",  # Out of area
            "issue_description": "AC not working",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_006",
            parameters=parameters,
            call_id="call_006",
        )
        
        assert response.action == "needs_human"
        assert "35 miles" in response.speak.lower() or "service area" in response.speak.lower() or "outside" in response.speak.lower()
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.create_service_request.handle_ops_command")
    async def test_create_service_request_warranty(self, mock_ops_handler):
        """Should handle warranty claims correctly."""
        from src.brains.ops.schema import OpsResult, OpsStatus
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Warranty service request created",
            requires_human=False,
            data={
                "lead_id": 789,
                "is_warranty": True,
                "waive_diagnostic_fee": True,
            },
        )
        
        parameters = {
            "phone": "+19725551234",
            "address": "123 Main St, DeSoto, TX 75115",
            "issue_description": "AC you fixed last week is not working again",
            "is_warranty": True,
            "previous_service_id": "12345",
        }
        
        response = await handle_create_service_request(
            tool_call_id="tc_007",
            parameters=parameters,
            call_id="call_007",
        )
        
        assert response.action == "completed"
        assert response.data.get("is_warranty") is True


class TestScheduleAppointment:
    """Tests for schedule_appointment tool."""

    # Actual data used for two-slot flow validation (service area: DeSoto TX)
    FIRST_CALL_PARAMS = {
        "customer_name": "Jane Smith",
        "phone": "+19725551234",
        "address": "456 Oak Ave, DeSoto, TX 75115",
    }
    SLOT_1_START = "2026-02-02T10:00:00"
    SLOT_1_END = "2026-02-02T12:00:00"
    SLOT_2_START = "2026-02-03T14:00:00"
    SLOT_2_END = "2026-02-03T16:00:00"
    TWO_SLOTS_MESSAGE = (
        "I have Monday, February 2 at 10:00 AM or Tuesday, February 3 at 02:00 PM. "
        "Which works better for you?"
    )

    @pytest.mark.asyncio
    async def test_schedule_appointment_requires_phone(self):
        """Should require phone number."""
        parameters = {
            "address": "123 Main St, Dallas, TX 75201",
            "customer_name": "John Doe",
        }
        
        response = await handle_schedule_appointment(
            tool_call_id="tc_sched_001",
            parameters=parameters,
            call_id="call_sched_001",
        )
        
        assert response.action == "needs_human"
        assert "phone" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.schedule_appointment.handle_ops_command")
    @patch("src.vapi.tools.ops.schedule_appointment.is_within_service_area")
    async def test_schedule_appointment_first_call_returns_two_slots(
        self, mock_service_area, mock_ops_handler
    ):
        """
        First call with only name, phone, address (no chosen_slot_start) must return
        two time options and next_available_slots. Validates the two-slot flow
        used by the prompt (call tool first, then present options).
        """
        from src.brains.ops.schema import OpsResult, OpsStatus

        mock_service_area.return_value = (True, None)  # in service area
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message=self.TWO_SLOTS_MESSAGE,
            requires_human=True,
            data={
                "next_available_slots": [
                    {"start": self.SLOT_1_START, "end": self.SLOT_1_END, "technician_id": "junior"},
                    {"start": self.SLOT_2_START, "end": self.SLOT_2_END, "technician_id": "junior"},
                ],
                "choose_then_book": True,
            },
        )

        with patch(
            "src.vapi.tools.ops.schedule_appointment.BaseToolHandler.check_duplicate_call",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await handle_schedule_appointment(
                tool_call_id="tc_sched_two_001",
                parameters=dict(self.FIRST_CALL_PARAMS),
                call_id="call_sched_two_001",
            )

        assert response.action == "needs_human"
        assert "next_available_slots" in response.data
        slots = response.data["next_available_slots"]
        assert len(slots) == 2
        assert slots[0]["start"] == self.SLOT_1_START and slots[0]["end"] == self.SLOT_1_END
        assert slots[1]["start"] == self.SLOT_2_START and slots[1]["end"] == self.SLOT_2_END
        assert "Which works better" in response.speak

    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.schedule_appointment.handle_ops_command")
    @patch("src.vapi.tools.ops.schedule_appointment.is_within_service_area")
    async def test_schedule_appointment_first_call_returns_two_slots_no_extra_params(
        self, mock_service_area, mock_ops_handler
    ):
        """
        First call must NOT require service_type or preferred_time_windows.
        Backend returns two options with only name, phone, address.
        """
        from src.brains.ops.schema import OpsResult, OpsStatus

        mock_service_area.return_value = (True, None)
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.NEEDS_HUMAN,
            message=self.TWO_SLOTS_MESSAGE,
            requires_human=True,
            data={
                "next_available_slots": [
                    {"start": self.SLOT_1_START, "end": self.SLOT_1_END},
                    {"start": self.SLOT_2_START, "end": self.SLOT_2_END},
                ],
            },
        )

        with patch(
            "src.vapi.tools.ops.schedule_appointment.BaseToolHandler.check_duplicate_call",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await handle_schedule_appointment(
                tool_call_id="tc_sched_two_002",
                parameters=dict(self.FIRST_CALL_PARAMS),  # no service_type, no preferred_time_windows
                call_id="call_sched_two_002",
            )

        assert response.action == "needs_human"
        assert len(response.data.get("next_available_slots", [])) == 2
        mock_ops_handler.assert_called_once()
        call_kwargs = mock_ops_handler.call_args
        # Command should have been built from the params we passed (no chosen_slot in metadata for first call)
        assert call_kwargs is not None

    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.schedule_appointment.handle_ops_command")
    @patch("src.vapi.tools.ops.schedule_appointment.is_within_service_area")
    async def test_schedule_appointment_second_call_books_chosen_slot(
        self, mock_service_area, mock_ops_handler
    ):
        """
        Second call with chosen_slot_start (from first response) must book the appointment
        and return appointment_id. Validates the full two-slot flow end-to-end.
        """
        from src.brains.ops.schema import OpsResult, OpsStatus

        mock_service_area.return_value = (True, None)
        future_time = datetime.now() + timedelta(days=1)
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Your appointment is scheduled for Monday, February 2 at 10:00 AM.",
            requires_human=False,
            data={
                "appointment_id": "evt_2001",
                "scheduled_time": self.SLOT_1_START,
                "scheduled_time_end": self.SLOT_1_END,
                "assigned_technician": {"name": "Junior"},
            },
        )

        parameters = {
            **self.FIRST_CALL_PARAMS,
            "chosen_slot_start": self.SLOT_1_START,
        }
        with patch(
            "src.vapi.tools.ops.schedule_appointment.BaseToolHandler.check_duplicate_call",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await handle_schedule_appointment(
                tool_call_id="tc_sched_two_003",
                parameters=parameters,
                call_id="call_sched_two_003",
            )

        assert response.action == "completed"
        assert response.data.get("appointment_id") == "evt_2001"
        assert "scheduled" in response.speak.lower() or "appointment" in response.speak.lower()
        mock_ops_handler.assert_called_once()
        # Verify chosen_slot_start was passed through (in metadata)
        call_args = mock_ops_handler.call_args[0]
        assert len(call_args) >= 1
        command = call_args[0]
        assert command.metadata.get("chosen_slot_start") == self.SLOT_1_START
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.schedule_appointment.handle_ops_command")
    async def test_schedule_appointment_success(self, mock_ops_handler):
        """Should successfully schedule appointment."""
        from src.brains.ops.schema import OpsResult, OpsStatus
        # Keep slot safely beyond same-day cutoff/baseline logic used by check_availability.
        future_time = datetime.now() + timedelta(days=1, hours=4)
        
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Appointment scheduled successfully",
            requires_human=False,
            data={
                "appointment_id": 1001,
                "scheduled_time": future_time.isoformat(),
                "scheduled_time_end": (future_time + timedelta(hours=2)).isoformat(),
                "technician": None,
            },
        )
        
        parameters = {
            "phone": "+19725551234",
            "address": "123 Main St, DeSoto, TX 75115",
            "customer_name": "John Doe",
            "preferred_date": "tomorrow",
            "preferred_time": "morning",
        }
        
        response = await handle_schedule_appointment(
            tool_call_id="tc_sched_002",
            parameters=parameters,
            call_id="call_sched_002",
        )
        
        assert response.action == "completed"
        assert response.data.get("appointment_id") is not None
        assert "scheduled" in response.speak.lower()


class TestCheckAvailability:
    """Tests for check_availability tool.

    check_availability uses create_appointment_service().find_next_two_available_slots()
    (not handle_ops_command) and should return 2 slots when the service returns 2.
    """

    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_availability.create_appointment_service", new_callable=AsyncMock)
    async def test_check_availability_works_without_phone(self, mock_create_appointment_service):
        """Should work without phone number (just checking general availability)."""
        from src.brains.ops.scheduling_rules import TimeSlot, SlotStatus
        future = datetime.now() + timedelta(days=1, hours=8)
        slot = TimeSlot(start=future, end=future + timedelta(hours=2), status=SlotStatus.AVAILABLE)
        mock_service_instance = AsyncMock()
        mock_service_instance.get_live_technicians = AsyncMock(return_value=[{"id": 100}])
        mock_service_instance.find_next_two_available_slots = AsyncMock(return_value=[slot])
        mock_create_appointment_service.return_value = mock_service_instance

        parameters = {
            "service_type": "diagnostic",
        }
        
        response = await handle_check_availability(
            tool_call_id="tc_avail_001",
            parameters=parameters,
            call_id="call_avail_001",
        )
        
        # Should process (may complete or need more info, but shouldn't fail on missing phone)
        assert response.action in ["completed", "needs_human"]
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_availability.create_appointment_service", new_callable=AsyncMock)
    async def test_check_availability_returns_two_slots(self, mock_create_appointment_service):
        """check_availability should return exactly 2 slots and 'Which works better for you?' when service returns 2."""
        from src.brains.ops.scheduling_rules import TimeSlot, SlotStatus

        future1 = datetime.now() + timedelta(days=1, hours=10)
        future2 = datetime.now() + timedelta(days=2, hours=14)
        slot1 = TimeSlot(
            start=future1,
            end=future1 + timedelta(hours=2),
            status=SlotStatus.AVAILABLE,
        )
        slot2 = TimeSlot(
            start=future2,
            end=future2 + timedelta(hours=2),
            status=SlotStatus.AVAILABLE,
        )

        mock_service_instance = AsyncMock()
        mock_service_instance.get_live_technicians = AsyncMock(return_value=[{"id": 101}])
        mock_service_instance.find_next_two_available_slots = AsyncMock(return_value=[slot1, slot2])
        mock_create_appointment_service.return_value = mock_service_instance

        parameters = {
            "service_type": "maintenance",
        }

        response = await handle_check_availability(
            tool_call_id="tc_avail_002",
            parameters=parameters,
            call_id="call_avail_002",
        )

        assert response.action == "needs_human"
        assert "next_available_slots" in response.data
        slots = response.data["next_available_slots"]
        assert len(slots) == 2
        assert slots[0]["start"] == future1.isoformat()
        assert slots[1]["start"] == future2.isoformat()
        assert "Which works better" in response.speak
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_availability.create_appointment_service", new_callable=AsyncMock)
    async def test_check_availability_success_one_slot(self, mock_create_appointment_service):
        """When service returns 1 slot, should return that slot (no IndexError)."""
        from src.brains.ops.scheduling_rules import TimeSlot, SlotStatus

        # Use a slot well in the future so it passes minimum_start (e.g. after same-day cutoff)
        future_time = datetime.now() + timedelta(days=1, hours=10)
        mock_slot = TimeSlot(
            start=future_time,
            end=future_time + timedelta(hours=2),
            status=SlotStatus.AVAILABLE,
        )
        mock_service_instance = AsyncMock()
        mock_service_instance.get_live_technicians = AsyncMock(return_value=[{"id": 102}])
        mock_service_instance.find_next_two_available_slots = AsyncMock(return_value=[mock_slot])
        mock_create_appointment_service.return_value = mock_service_instance

        parameters = {"service_type": "diagnostic"}

        response = await handle_check_availability(
            tool_call_id="tc_avail_003",
            parameters=parameters,
            call_id="call_avail_003",
        )

        assert response.action == "needs_human"
        assert len(response.data.get("next_available_slots", [])) == 1
        assert "slot" in response.speak.lower() or "available" in response.speak.lower()
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_availability.create_appointment_service", new_callable=AsyncMock)
    async def test_check_availability_no_slots_available(self, mock_create_appointment_service):
        """When service returns 0 slots, should return friendly message and no_slots_available."""
        mock_service_instance = AsyncMock()
        mock_service_instance.get_live_technicians = AsyncMock(return_value=[{"id": 103}])
        mock_service_instance.find_next_two_available_slots = AsyncMock(return_value=[])
        mock_create_appointment_service.return_value = mock_service_instance

        parameters = {"service_type": "maintenance"}

        response = await handle_check_availability(
            tool_call_id="tc_avail_004",
            parameters=parameters,
            call_id="call_avail_004",
        )

        assert response.action == "needs_human"
        assert response.data.get("no_slots_available") is True
        assert "couldn't find" in response.speak.lower() or "available" in response.speak.lower()
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_availability.create_appointment_service", new_callable=AsyncMock)
    async def test_check_availability_success(self, mock_create_appointment_service):
        """Should successfully find available slots (legacy test name; now uses two slots)."""
        from src.brains.ops.scheduling_rules import TimeSlot, SlotStatus

        future_time = datetime.now() + timedelta(hours=4)
        slot1 = TimeSlot(start=future_time, end=future_time + timedelta(hours=2), status=SlotStatus.AVAILABLE)
        slot2 = TimeSlot(
            start=future_time + timedelta(days=1),
            end=future_time + timedelta(days=1, hours=2),
            status=SlotStatus.AVAILABLE,
        )
        mock_service_instance = AsyncMock()
        mock_service_instance.get_live_technicians = AsyncMock(return_value=[{"id": 104}])
        mock_service_instance.find_next_two_available_slots = AsyncMock(return_value=[slot1, slot2])
        mock_create_appointment_service.return_value = mock_service_instance

        parameters = {"preferred_date": "tomorrow", "service_type": "diagnostic"}

        response = await handle_check_availability(
            tool_call_id="tc_avail_002b",
            parameters=parameters,
            call_id="call_avail_002b",
        )

        assert response.action == "needs_human"
        assert "next_available_slots" in response.data
        assert len(response.data["next_available_slots"]) >= 1
        assert "which works better" in response.speak.lower() or "slot" in response.speak.lower() or "have" in response.speak.lower()

    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_availability.create_appointment_service", new_callable=AsyncMock)
    async def test_check_availability_two_earliest_across_technicians(self, mock_create_appointment_service):
        """Two earliest slots across all technicians: slot1 from tech 201, slot2 from tech 202."""
        from src.brains.ops.scheduling_rules import TimeSlot, SlotStatus

        # Use fixed future times so they pass minimum_start regardless of current time
        base = datetime.now() + timedelta(days=2)
        slot1_start = base.replace(hour=8, minute=0, second=0, microsecond=0)
        slot2_start = base.replace(hour=14, minute=0, second=0, microsecond=0)
        if slot2_start <= slot1_start:
            slot2_start += timedelta(days=1)
        slot_tech_201 = TimeSlot(
            start=slot1_start,
            end=slot1_start + timedelta(hours=2),
            status=SlotStatus.AVAILABLE,
        )
        slot_tech_202 = TimeSlot(
            start=slot2_start,
            end=slot2_start + timedelta(hours=2),
            status=SlotStatus.AVAILABLE,
        )
        mock_service_instance = AsyncMock()

        async def side_effect_find_slots(tech_id, **kwargs):
            if str(tech_id) == "201":
                return [slot_tech_201]
            if str(tech_id) == "202":
                return [slot_tech_202]
            return []

        mock_service_instance.get_live_technicians = AsyncMock(
            return_value=[{"id": 201}, {"id": 202}]
        )
        mock_service_instance.find_next_two_available_slots = AsyncMock(
            side_effect=side_effect_find_slots
        )
        mock_create_appointment_service.return_value = mock_service_instance

        parameters = {"service_type": "diagnostic"}

        response = await handle_check_availability(
            tool_call_id="tc_avail_cross_tech",
            parameters=parameters,
            call_id="call_avail_cross",
        )

        assert response.action == "needs_human"
        assert "next_available_slots" in response.data
        slots = response.data["next_available_slots"]
        assert len(slots) == 2
        assert slots[0]["technician_id"] == "201"
        assert slots[1]["technician_id"] == "202"
        assert slots[0]["start"] == slot1_start.isoformat()
        assert slots[1]["start"] == slot2_start.isoformat()


class TestRescheduleAppointment:
    """Tests for reschedule_appointment tool."""
    
    @pytest.mark.asyncio
    async def test_reschedule_appointment_requires_phone(self):
        """Should require phone number."""
        parameters = {}
        
        response = await handle_reschedule_appointment(
            tool_call_id="tc_resched_001",
            parameters=parameters,
            call_id="call_resched_001",
        )
        
        assert response.action == "needs_human"
        assert "phone" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.reschedule_appointment.handle_ops_command")
    async def test_reschedule_appointment_success(self, mock_ops_handler):
        """Should successfully reschedule appointment."""
        from datetime import datetime, timedelta
        from src.brains.ops.schema import OpsResult, OpsStatus
        old_time = datetime.now() + timedelta(days=1)
        new_time = datetime.now() + timedelta(days=2)
        
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Appointment rescheduled successfully",
            requires_human=False,
            data={
                "appointment_id": 2001,
                "scheduled_time": new_time.isoformat(),
                "scheduled_time_end": (new_time + timedelta(hours=2)).isoformat(),
                "previous_time": old_time.isoformat(),
            },
        )
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
            "new_preferred_date": "next Tuesday",
        }
        
        response = await handle_reschedule_appointment(
            tool_call_id="tc_resched_002",
            parameters=parameters,
            call_id="call_resched_002",
        )
        
        assert response.action == "completed"
        assert "rescheduled" in response.speak.lower()
        assert response.data.get("appointment_id") is not None


class TestCancelAppointment:
    """Tests for cancel_appointment tool."""
    
    @pytest.mark.asyncio
    async def test_cancel_appointment_requires_phone(self):
        """Should require phone number."""
        parameters = {}
        
        response = await handle_cancel_appointment(
            tool_call_id="tc_cancel_001",
            parameters=parameters,
            call_id="call_cancel_001",
        )
        
        assert response.action == "needs_human"
        assert "phone" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.cancel_appointment.handle_ops_command")
    async def test_cancel_appointment_success(self, mock_ops_handler):
        """Should successfully cancel appointment."""
        from src.brains.ops.schema import OpsResult, OpsStatus
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Appointment cancelled successfully",
            requires_human=False,
            data={
                "appointment_id": 3001,
                "cancelled": True,
            },
        )
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
        }
        
        response = await handle_cancel_appointment(
            tool_call_id="tc_cancel_002",
            parameters=parameters,
            call_id="call_cancel_002",
        )
        
        assert response.action == "completed"
        assert "cancel" in response.speak.lower()


class TestCheckAppointmentStatus:
    """Tests for check_appointment_status tool."""
    
    @pytest.mark.asyncio
    async def test_check_appointment_status_requires_phone(self):
        """Should require phone number."""
        parameters = {}
        
        response = await handle_check_appointment_status(
            tool_call_id="tc_status_001",
            parameters=parameters,
            call_id="call_status_001",
        )
        
        assert response.action == "needs_human"
        assert "phone" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.ops.check_appointment_status.handle_ops_command")
    async def test_check_appointment_status_success(self, mock_ops_handler):
        """Should successfully find appointment status."""
        from datetime import datetime, timedelta
        from src.brains.ops.schema import OpsResult, OpsStatus
        
        future_time = datetime.now() + timedelta(days=1)
        
        # Mock OPS handler
        mock_ops_handler.return_value = OpsResult(
            status=OpsStatus.SUCCESS,
            message="Appointment found",
            requires_human=False,
            data={
                "appointments": [{
                    "id": 4001,
                    "name": "Service Appointment",
                    "scheduled_time": future_time.isoformat(),
                    "scheduled_time_end": (future_time + timedelta(hours=2)).isoformat(),
                    "state": "confirmed",
                }]
            },
        )
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
        }
        
        response = await handle_check_appointment_status(
            tool_call_id="tc_status_002",
            parameters=parameters,
            call_id="call_status_002",
        )
        
        assert response.action == "completed"
        assert "appointment" in response.speak.lower()
        assert response.data.get("appointments") is not None
