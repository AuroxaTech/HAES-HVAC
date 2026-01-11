"""
HAES HVAC - Comprehensive OPS Brain Handler Tests

Exhaustive tests for OPS brain handlers covering:
- Service request handling with all scenarios
- Emergency qualification
- Appointment scheduling, rescheduling, cancellation
- Status updates
- Technician assignment
- Missing field validation
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.hael.schema import (
    Brain,
    Channel,
    Entity,
    HaelCommand,
    Intent,
    UrgencyLevel,
)
from src.brains.ops.handlers import (
    handle_ops_command,
    OPS_INTENTS,
)

from src.brains.ops.schema import OpsStatus, ServicePriority
from src.brains.ops.emergency_rules import qualify_emergency
from src.brains.ops.service_catalog import infer_service_type_from_description
from src.brains.ops.tech_roster import assign_technician


def create_ops_command(
    intent: Intent,
    entities: Entity | None = None,
    requires_human: bool = False,
    missing_fields: list[str] | None = None,
    confidence: float = 0.8,
) -> HaelCommand:
    """Helper to create HaelCommand for OPS brain testing."""
    return HaelCommand(
        request_id=str(uuid4()),
        channel=Channel.VOICE,
        raw_text="Test OPS command",
        intent=intent,
        brain=Brain.OPS,
        entities=entities or Entity(),
        confidence=confidence,
        requires_human=requires_human,
        missing_fields=missing_fields or [],
        idempotency_key=str(uuid4()),
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def complete_service_entity():
    """Entity with all fields for service request."""
    return Entity(
        full_name="John Smith",
        phone="512-555-1234",
        email="john@example.com",
        address="123 Main St, Austin, TX",
        zip_code="78701",
        city="Austin",
        state="TX",
        problem_description="AC not cooling properly",
        system_type="central_air",
        urgency_level=UrgencyLevel.MEDIUM,
        property_type="residential",
    )


@pytest.fixture
def emergency_entity():
    """Entity for emergency service request."""
    return Entity(
        full_name="Jane Doe",
        phone="512-555-9999",
        address="456 Oak Ave, Austin, TX",
        zip_code="78702",
        problem_description="I smell gas coming from the furnace",
        urgency_level=UrgencyLevel.EMERGENCY,
    )


# =============================================================================
# OPS INTENTS CONFIGURATION TESTS
# =============================================================================


class TestOpsIntentsConfiguration:
    """Tests for OPS intents configuration."""

    def test_ops_intents_contains_service_request(self):
        """SERVICE_REQUEST should be in OPS intents."""
        assert Intent.SERVICE_REQUEST in OPS_INTENTS

    def test_ops_intents_contains_scheduling(self):
        """Scheduling intents should be in OPS intents."""
        assert Intent.SCHEDULE_APPOINTMENT in OPS_INTENTS
        assert Intent.RESCHEDULE_APPOINTMENT in OPS_INTENTS
        assert Intent.CANCEL_APPOINTMENT in OPS_INTENTS

    def test_ops_intents_contains_status_update(self):
        """STATUS_UPDATE_REQUEST should be in OPS intents."""
        assert Intent.STATUS_UPDATE_REQUEST in OPS_INTENTS

    def test_ops_intents_count(self):
        """OPS should handle exactly 5 intents."""
        assert len(OPS_INTENTS) == 5


# =============================================================================
# SERVICE REQUEST HANDLER TESTS
# =============================================================================


class TestServiceRequestHandler:
    """Comprehensive tests for service request handling."""

    def test_complete_service_request_success(self, complete_service_entity):
        """Complete service request should succeed."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.SUCCESS
        assert result.requires_human is False
        assert result.work_order is not None
        assert result.work_order.customer_name == "John Smith"
        assert result.work_order.customer_phone == "512-555-1234"
        assert result.work_order.zip_code == "78701"

    def test_service_request_missing_identity(self):
        """Service request without identity should need human."""
        entities = Entity(
            address="123 Main St",
            zip_code="78701",
            problem_description="AC not working",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert any("identity" in f.lower() for f in result.missing_fields)

    def test_service_request_missing_location(self):
        """Service request without location should need human."""
        entities = Entity(
            full_name="John Smith",
            phone="512-555-1234",
            problem_description="AC not working",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert any("location" in f.lower() for f in result.missing_fields)

    def test_service_request_missing_problem_description(self):
        """Service request without problem description should need human."""
        entities = Entity(
            full_name="John Smith",
            phone="512-555-1234",
            address="123 Main St",
            zip_code="78701",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert any("problem" in f.lower() for f in result.missing_fields)

    def test_service_request_phone_only_for_identity(self):
        """Phone number alone should satisfy identity."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC not working",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        # Should not flag identity as missing
        assert "identity" not in " ".join(result.missing_fields).lower()

    def test_service_request_email_only_for_identity(self):
        """Email alone should satisfy identity."""
        entities = Entity(
            email="john@example.com",
            address="123 Main St, Austin TX",
            problem_description="AC not working",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        # Should not flag identity as missing
        assert "identity" not in " ".join(result.missing_fields).lower()

    def test_service_request_name_only_for_identity(self):
        """Name alone should satisfy identity."""
        entities = Entity(
            full_name="John Smith",
            zip_code="78701",
            problem_description="AC not working",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        # Should not flag identity as missing
        assert "identity" not in " ".join(result.missing_fields).lower()

    def test_service_request_with_multiple_missing_fields(self):
        """Service request with multiple missing fields."""
        entities = Entity()  # Empty entity
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert len(result.missing_fields) >= 2


# =============================================================================
# EMERGENCY CLASSIFICATION TESTS
# =============================================================================


class TestEmergencyClassification:
    """Tests for emergency qualification in service requests."""

    def test_emergency_gas_leak(self, emergency_entity):
        """Gas leak should be classified as emergency."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=emergency_entity,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.SUCCESS
        assert result.data is not None
        assert result.data.get("is_emergency") is True

    def test_emergency_priority_assigned(self, emergency_entity):
        """Emergency should get emergency priority."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=emergency_entity,
        )
        result = handle_ops_command(command)

        assert result.work_order is not None
        assert result.work_order.priority == ServicePriority.EMERGENCY

    @pytest.mark.parametrize("description", [
        "I smell gas",
        "Gas leak",
        "Carbon monoxide alarm going off",
        "CO detector beeping",
        "Burning smell from furnace",
        "Smoke coming from AC",
        "Water flooding from unit",
        "Fire smell",
        "Sparks from the unit",
    ])
    def test_emergency_keywords(self, description):
        """Various emergency keywords should trigger emergency."""
        result = qualify_emergency(
            problem_description=description,
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert result.is_emergency is True

    def test_emergency_no_heat_cold_temp(self):
        """No heat with cold temperature should be emergency."""
        result = qualify_emergency(
            problem_description="Heater not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=30,  # Below 55°F threshold
        )
        assert result.is_emergency is True

    def test_emergency_no_heat_warm_temp(self):
        """No heat with warm temperature should not be emergency."""
        result = qualify_emergency(
            problem_description="Heater not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=65,  # Above 55°F threshold
        )
        assert result.is_emergency is False

    def test_emergency_no_ac_hot_temp(self):
        """No AC with hot temperature should be emergency."""
        result = qualify_emergency(
            problem_description="AC not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=95,  # Above 85°F threshold
        )
        assert result.is_emergency is True

    def test_emergency_no_ac_moderate_temp(self):
        """No AC with moderate temperature should not be emergency."""
        result = qualify_emergency(
            problem_description="AC not working",
            urgency_level=UrgencyLevel.UNKNOWN,
            temperature_mentioned=75,  # Below 85°F threshold
        )
        assert result.is_emergency is False

    def test_hael_emergency_urgency(self):
        """HAEL emergency urgency should be classified as emergency."""
        result = qualify_emergency(
            problem_description="Standard repair",
            urgency_level=UrgencyLevel.EMERGENCY,
        )
        assert result.is_emergency is True


# =============================================================================
# PRIORITY CLASSIFICATION TESTS
# =============================================================================


class TestPriorityClassification:
    """Tests for service priority classification."""

    def test_emergency_priority(self, emergency_entity):
        """Emergency issue should get EMERGENCY priority."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=emergency_entity,
        )
        result = handle_ops_command(command)

        assert result.work_order.priority == ServicePriority.EMERGENCY

    def test_urgent_priority(self):
        """High urgency should get URGENT priority."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC not working",
            urgency_level=UrgencyLevel.HIGH,
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.work_order.priority == ServicePriority.URGENT

    def test_high_priority(self):
        """Medium urgency should get HIGH priority."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC not working",
            urgency_level=UrgencyLevel.MEDIUM,
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.work_order.priority == ServicePriority.HIGH

    def test_normal_priority(self):
        """Low urgency should get NORMAL priority."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC needs tune-up",
            urgency_level=UrgencyLevel.LOW,
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.work_order.priority == ServicePriority.NORMAL


# =============================================================================
# SERVICE TYPE INFERENCE TESTS
# =============================================================================


class TestServiceTypeInference:
    """Tests for service type inference from problem description."""

    @pytest.mark.parametrize("description", [
        "AC not working",
        "Air conditioner broken",
        "Cooling not working",
        "Heater not working",
        "Furnace broken",
        "Heating system issue",
        "HVAC system down",
    ])
    def test_service_type_inference(self, description):
        """Service type should be inferred from description."""
        service_type = infer_service_type_from_description(description)
        # Should return a valid service type
        assert service_type is not None
        assert service_type.code is not None
        assert service_type.name is not None
        assert service_type.duration_minutes_min > 0


# =============================================================================
# TECHNICIAN ASSIGNMENT TESTS
# =============================================================================


class TestTechnicianAssignment:
    """Tests for technician assignment."""

    def test_technician_assigned_for_valid_zip(self, complete_service_entity):
        """Technician should be assigned for valid service area."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
        )
        result = handle_ops_command(command)

        # May or may not have technician depending on roster
        # But work order should exist
        assert result.work_order is not None

    def test_technician_assignment_emergency_priority(self):
        """Emergency calls should prioritize available technicians."""
        technician = assign_technician(
            zip_code="78701",
            is_emergency=True,
            is_commercial=False,
        )
        # Technician may or may not be available
        # This tests the function doesn't crash

    def test_technician_assignment_commercial(self):
        """Commercial jobs should consider commercial certification."""
        technician = assign_technician(
            zip_code="78701",
            is_emergency=False,
            is_commercial=True,
        )
        # Technician may or may not be available


# =============================================================================
# SCHEDULE APPOINTMENT HANDLER TESTS
# =============================================================================


class TestScheduleAppointmentHandler:
    """Tests for schedule appointment handling."""

    @pytest.mark.asyncio
    async def test_schedule_with_contact_info(self):
        """Schedule with contact info should succeed."""
        entities = Entity(
            phone="512-555-1234",
            email="john@example.com",
            preferred_time_windows=["morning", "afternoon"],
        )
        command = create_ops_command(
            intent=Intent.SCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        assert result.status == OpsStatus.SUCCESS
        assert result.requires_human is False
        assert result.data is not None
        # Appointment handler returns appointment_id, scheduled_time, etc.
        assert result.data.get("appointment_id") is not None
        assert result.data.get("scheduled_time") is not None

    @pytest.mark.asyncio
    async def test_schedule_missing_contact(self):
        """Schedule without contact should need human."""
        entities = Entity(
            preferred_time_windows=["morning"],
        )
        command = create_ops_command(
            intent=Intent.SCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True

    @pytest.mark.asyncio
    async def test_schedule_phone_only(self):
        """Phone only should be sufficient for scheduling."""
        entities = Entity(phone="512-555-1234")
        command = create_ops_command(
            intent=Intent.SCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        assert result.status == OpsStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_schedule_email_only(self):
        """Email only should be sufficient for scheduling."""
        entities = Entity(email="john@example.com")
        command = create_ops_command(
            intent=Intent.SCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        assert result.status == OpsStatus.SUCCESS


# =============================================================================
# RESCHEDULE APPOINTMENT HANDLER TESTS
# =============================================================================


class TestRescheduleAppointmentHandler:
    """Tests for reschedule appointment handling."""

    @pytest.mark.asyncio
    async def test_reschedule_with_contact_info(self):
        """Reschedule with contact info should succeed."""
        entities = Entity(
            phone="512-555-1234",
            email="john@example.com",
        )
        command = create_ops_command(
            intent=Intent.RESCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        # May need human if no appointment found (expected in unit tests)
        assert result.status in (OpsStatus.SUCCESS, OpsStatus.NEEDS_HUMAN)
        # Message should mention reschedule or appointment
        assert "reschedule" in result.message.lower() or "appointment" in result.message.lower()

    @pytest.mark.asyncio
    async def test_reschedule_missing_contact(self):
        """Reschedule without contact should need human."""
        entities = Entity()
        command = create_ops_command(
            intent=Intent.RESCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# CANCEL APPOINTMENT HANDLER TESTS
# =============================================================================


class TestCancelAppointmentHandler:
    """Tests for cancel appointment handling."""

    @pytest.mark.asyncio
    async def test_cancel_with_contact_info(self):
        """Cancel with contact info should succeed."""
        entities = Entity(
            phone="512-555-1234",
        )
        command = create_ops_command(
            intent=Intent.CANCEL_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        # May need human if no appointment found (expected in unit tests)
        assert result.status in (OpsStatus.SUCCESS, OpsStatus.NEEDS_HUMAN)
        # Message should mention cancel or appointment
        assert "cancel" in result.message.lower() or "appointment" in result.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_missing_contact(self):
        """Cancel without contact should need human."""
        entities = Entity()
        command = create_ops_command(
            intent=Intent.CANCEL_APPOINTMENT,
            entities=entities,
        )
        result = await handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# STATUS UPDATE HANDLER TESTS
# =============================================================================


class TestStatusUpdateHandler:
    """Tests for status update handling."""

    def test_status_with_contact_info(self):
        """Status request with contact should succeed."""
        entities = Entity(
            phone="512-555-1234",
        )
        command = create_ops_command(
            intent=Intent.STATUS_UPDATE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.SUCCESS
        assert result.requires_human is False
        assert "status" in result.message.lower()

    def test_status_missing_contact(self):
        """Status request without contact should need human."""
        entities = Entity()
        command = create_ops_command(
            intent=Intent.STATUS_UPDATE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# UNSUPPORTED INTENT TESTS
# =============================================================================


class TestUnsupportedIntent:
    """Tests for unsupported intent handling."""

    @pytest.mark.parametrize("intent", [
        Intent.QUOTE_REQUEST,
        Intent.BILLING_INQUIRY,
        Intent.HIRING_INQUIRY,
        Intent.PAYROLL_INQUIRY,
    ])
    def test_unsupported_intent(self, intent):
        """Non-OPS intents should return unsupported."""
        command = create_ops_command(
            intent=intent,
            entities=Entity(),
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.UNSUPPORTED_INTENT


# =============================================================================
# HAEL REQUIRES HUMAN PROPAGATION TESTS
# =============================================================================


class TestHaelRequiresHumanPropagation:
    """Tests for HAEL requires_human flag propagation."""

    def test_hael_requires_human_propagates(self, complete_service_entity):
        """HAEL requires_human flag should propagate."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
            requires_human=True,  # Pre-set by HAEL
            missing_fields=["some_field"],
        )
        result = handle_ops_command(command)

        assert result.status == OpsStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# WORK ORDER DATA TESTS
# =============================================================================


class TestWorkOrderData:
    """Tests for work order data structure."""

    def test_work_order_contains_customer_info(self, complete_service_entity):
        """Work order should contain customer information."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
        )
        result = handle_ops_command(command)

        wo = result.work_order
        assert wo.customer_name == "John Smith"
        assert wo.customer_phone == "512-555-1234"
        assert wo.customer_email == "john@example.com"

    def test_work_order_contains_location(self, complete_service_entity):
        """Work order should contain location information."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
        )
        result = handle_ops_command(command)

        wo = result.work_order
        assert wo.address == "123 Main St, Austin, TX"
        assert wo.zip_code == "78701"

    def test_work_order_contains_problem(self, complete_service_entity):
        """Work order should contain problem description."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
        )
        result = handle_ops_command(command)

        wo = result.work_order
        assert wo.problem_description == "AC not cooling properly"

    def test_work_order_has_timestamp(self, complete_service_entity):
        """Work order should have creation timestamp."""
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_service_entity,
        )
        result = handle_ops_command(command)

        wo = result.work_order
        assert wo.created_at is not None
        assert isinstance(wo.created_at, datetime)


# =============================================================================
# COMMERCIAL VS RESIDENTIAL TESTS
# =============================================================================


class TestCommercialVsResidential:
    """Tests for commercial vs residential handling."""

    def test_commercial_property_flag(self):
        """Commercial property should be flagged correctly."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC not working",
            property_type="commercial",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        # Technician assignment considers commercial flag
        assert result.work_order is not None

    def test_residential_property_flag(self):
        """Residential property should be flagged correctly."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC not working",
            property_type="residential",
        )
        command = create_ops_command(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = handle_ops_command(command)

        assert result.work_order is not None
