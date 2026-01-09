"""
HAES HVAC - Comprehensive HAEL Routing Tests

Exhaustive tests for HAEL routing covering:
- Brain routing for all intents
- Field validation and missing field detection
- Confidence thresholds
- requires_human logic
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.hael.schema import (
    Brain,
    Channel,
    Entity,
    HaelExtractionResult,
    Intent,
    UrgencyLevel,
)
from src.hael.router import route_command, INTENT_BRAIN_MAP


@pytest.fixture
def base_entity():
    """Create a base entity with minimal data."""
    return Entity()


@pytest.fixture
def complete_entity():
    """Create an entity with all common fields populated."""
    return Entity(
        full_name="John Smith",
        phone="512-555-1234",
        email="john@example.com",
        address="123 Main St",
        zip_code="78701",
        city="Austin",
        state="TX",
        problem_description="AC not working",
        system_type="central_air",
        urgency_level=UrgencyLevel.MEDIUM,
        property_type="residential",
        square_footage=2000,
        system_age_years=10,
        timeline="within 2 weeks",
    )


def create_extraction(
    intent: Intent,
    entities: Entity | None = None,
    confidence: float = 0.8,
) -> HaelExtractionResult:
    """Helper to create HaelExtractionResult for routing tests."""
    return HaelExtractionResult(
        intent=intent,
        entities=entities or Entity(),
        confidence=confidence,
        raw_signals={},
    )


def determine_brain(intent: Intent) -> Brain:
    """Get the brain for a given intent."""
    return INTENT_BRAIN_MAP.get(intent, Brain.UNKNOWN)


# =============================================================================
# BRAIN ROUTING TESTS
# =============================================================================


class TestBrainDetermination:
    """Tests for brain determination based on intent."""

    @pytest.mark.parametrize("intent,expected_brain", [
        (Intent.SERVICE_REQUEST, Brain.OPS),
        (Intent.SCHEDULE_APPOINTMENT, Brain.OPS),
        (Intent.RESCHEDULE_APPOINTMENT, Brain.OPS),
        (Intent.CANCEL_APPOINTMENT, Brain.OPS),
        (Intent.STATUS_UPDATE_REQUEST, Brain.OPS),
        (Intent.QUOTE_REQUEST, Brain.REVENUE),
        (Intent.BILLING_INQUIRY, Brain.CORE),
        (Intent.PAYMENT_TERMS_INQUIRY, Brain.CORE),
        (Intent.INVOICE_REQUEST, Brain.CORE),
        (Intent.INVENTORY_INQUIRY, Brain.CORE),
        (Intent.PURCHASE_REQUEST, Brain.CORE),
        (Intent.HIRING_INQUIRY, Brain.PEOPLE),
        (Intent.ONBOARDING_INQUIRY, Brain.PEOPLE),
        (Intent.PAYROLL_INQUIRY, Brain.PEOPLE),
        (Intent.UNKNOWN, Brain.UNKNOWN),
    ])
    def test_brain_routing_for_all_intents(self, intent, expected_brain):
        """Test that each intent routes to the correct brain."""
        brain = determine_brain(intent)
        assert brain == expected_brain

    def test_ops_intents_route_to_ops(self):
        """All OPS intents should route to OPS brain."""
        ops_intents = [
            Intent.SERVICE_REQUEST,
            Intent.SCHEDULE_APPOINTMENT,
            Intent.RESCHEDULE_APPOINTMENT,
            Intent.CANCEL_APPOINTMENT,
            Intent.STATUS_UPDATE_REQUEST,
        ]
        for intent in ops_intents:
            assert determine_brain(intent) == Brain.OPS

    def test_core_intents_route_to_core(self):
        """All CORE intents should route to CORE brain."""
        core_intents = [
            Intent.BILLING_INQUIRY,
            Intent.PAYMENT_TERMS_INQUIRY,
            Intent.INVOICE_REQUEST,
            Intent.INVENTORY_INQUIRY,
            Intent.PURCHASE_REQUEST,
        ]
        for intent in core_intents:
            assert determine_brain(intent) == Brain.CORE

    def test_revenue_intents_route_to_revenue(self):
        """All REVENUE intents should route to REVENUE brain."""
        revenue_intents = [
            Intent.QUOTE_REQUEST,
        ]
        for intent in revenue_intents:
            assert determine_brain(intent) == Brain.REVENUE

    def test_people_intents_route_to_people(self):
        """All PEOPLE intents should route to PEOPLE brain."""
        people_intents = [
            Intent.HIRING_INQUIRY,
            Intent.ONBOARDING_INQUIRY,
            Intent.PAYROLL_INQUIRY,
        ]
        for intent in people_intents:
            assert determine_brain(intent) == Brain.PEOPLE


# =============================================================================
# SERVICE REQUEST ROUTING TESTS
# =============================================================================


class TestServiceRequestRouting:
    """Tests for SERVICE_REQUEST routing and field validation."""

    def test_complete_service_request_routes_successfully(self, complete_entity):
        """Service request with all fields should route without human."""
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_entity,
            confidence=0.8,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is False
        assert len(result.missing_fields) == 0

    def test_service_request_missing_identity(self):
        """Service request missing identity should need human."""
        entities = Entity(
            address="123 Main St",
            zip_code="78701",
            problem_description="AC not working",
            urgency_level=UrgencyLevel.MEDIUM,
        )
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True
        assert any("identity" in f.lower() for f in result.missing_fields)

    def test_service_request_missing_location(self):
        """Service request missing location should need human."""
        entities = Entity(
            full_name="John Smith",
            phone="512-555-1234",
            problem_description="AC not working",
            urgency_level=UrgencyLevel.MEDIUM,
        )
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True
        assert any("location" in f.lower() for f in result.missing_fields)

    def test_service_request_missing_problem_description(self):
        """Service request missing problem description should need human."""
        entities = Entity(
            full_name="John Smith",
            phone="512-555-1234",
            address="123 Main St",
            zip_code="78701",
            urgency_level=UrgencyLevel.MEDIUM,
        )
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True
        assert any("problem" in f.lower() for f in result.missing_fields)

    def test_service_request_with_phone_only_for_identity(self):
        """Phone number alone should satisfy identity requirement."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="AC not working",
            urgency_level=UrgencyLevel.MEDIUM,
        )
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        # Should not flag identity as missing since phone is present
        assert not any("identity" in f.lower() for f in result.missing_fields)

    def test_service_request_with_email_only_for_identity(self):
        """Email alone should satisfy identity requirement."""
        entities = Entity(
            email="john@example.com",
            address="123 Main St",
            problem_description="AC not working",
            urgency_level=UrgencyLevel.MEDIUM,
        )
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS


# =============================================================================
# QUOTE REQUEST ROUTING TESTS
# =============================================================================


class TestQuoteRequestRouting:
    """Tests for QUOTE_REQUEST routing and field validation."""

    def test_complete_quote_request_routes_successfully(self):
        """Quote request with all fields should route without human."""
        entities = Entity(
            full_name="Sarah Jones",
            phone="512-555-9999",
            email="sarah@example.com",
            property_type="residential",
            square_footage=2500,
            system_age_years=15,
            timeline="within 2 weeks",
        )
        extraction = create_extraction(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
            confidence=0.8,
        )
        result = route_command(extraction)

        assert result.brain == Brain.REVENUE
        assert result.requires_human is False

    def test_quote_request_missing_identity(self):
        """Quote request missing identity should need human."""
        entities = Entity(
            property_type="residential",
            timeline="within 2 weeks",
        )
        extraction = create_extraction(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.REVENUE
        assert result.requires_human is True

    def test_quote_request_missing_property_type(self):
        """Quote request missing property type should need human."""
        entities = Entity(
            full_name="Sarah Jones",
            phone="512-555-9999",
            timeline="within 2 weeks",
        )
        extraction = create_extraction(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.REVENUE
        assert result.requires_human is True
        assert any("property" in f.lower() for f in result.missing_fields)

    def test_quote_request_missing_timeline(self):
        """Quote request missing timeline should need human."""
        entities = Entity(
            full_name="Sarah Jones",
            phone="512-555-9999",
            property_type="residential",
        )
        extraction = create_extraction(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.REVENUE
        assert result.requires_human is True
        assert any("timeline" in f.lower() for f in result.missing_fields)


# =============================================================================
# BILLING INQUIRY ROUTING TESTS
# =============================================================================


class TestBillingInquiryRouting:
    """Tests for BILLING_INQUIRY routing and field validation."""

    def test_billing_inquiry_with_phone(self):
        """Billing inquiry with phone should route without human."""
        entities = Entity(phone="512-555-1234")
        extraction = create_extraction(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is False

    def test_billing_inquiry_with_email(self):
        """Billing inquiry with email should route without human."""
        entities = Entity(email="john@example.com")
        extraction = create_extraction(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is False

    def test_billing_inquiry_missing_contact(self):
        """Billing inquiry without contact should need human."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is True


# =============================================================================
# PAYMENT TERMS INQUIRY ROUTING TESTS
# =============================================================================


class TestPaymentTermsRouting:
    """Tests for PAYMENT_TERMS_INQUIRY routing."""

    def test_payment_terms_no_identity_required(self):
        """Payment terms inquiry shouldn't require identity."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is False

    def test_payment_terms_with_property_type(self):
        """Payment terms with property type should provide segment info."""
        entities = Entity(property_type="commercial")
        extraction = create_extraction(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE


# =============================================================================
# HIRING INQUIRY ROUTING TESTS
# =============================================================================


class TestHiringInquiryRouting:
    """Tests for HIRING_INQUIRY routing."""

    def test_hiring_inquiry_no_identity_required(self):
        """Hiring inquiry shouldn't require identity."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.PEOPLE
        assert result.requires_human is False


# =============================================================================
# ONBOARDING INQUIRY ROUTING TESTS
# =============================================================================


class TestOnboardingInquiryRouting:
    """Tests for ONBOARDING_INQUIRY routing."""

    def test_onboarding_inquiry_with_email(self):
        """Onboarding inquiry with email should route without human."""
        entities = Entity(email="employee@company.com")
        extraction = create_extraction(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.PEOPLE
        assert result.requires_human is False

    def test_onboarding_inquiry_missing_email(self):
        """Onboarding inquiry without email should need human."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.PEOPLE
        assert result.requires_human is True


# =============================================================================
# PAYROLL INQUIRY ROUTING TESTS
# =============================================================================


class TestPayrollInquiryRouting:
    """Tests for PAYROLL_INQUIRY routing."""

    def test_payroll_inquiry_with_email(self):
        """Payroll inquiry with email should route without human."""
        entities = Entity(email="employee@company.com")
        extraction = create_extraction(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.PEOPLE
        assert result.requires_human is False

    def test_payroll_inquiry_missing_email(self):
        """Payroll inquiry without email should need human."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.PEOPLE
        assert result.requires_human is True


# =============================================================================
# CONFIDENCE THRESHOLD TESTS
# =============================================================================


class TestConfidenceThresholds:
    """Tests for confidence-based routing decisions."""

    def test_low_confidence_triggers_human_review(self, complete_entity):
        """Low confidence should trigger human review."""
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_entity,
            confidence=0.3,  # Low confidence
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True
        assert "confidence" in result.routing_reason.lower()

    def test_high_confidence_routes_directly(self, complete_entity):
        """High confidence should route directly."""
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_entity,
            confidence=0.9,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is False

    def test_medium_confidence_depends_on_fields(self, complete_entity):
        """Medium confidence with complete fields should route."""
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_entity,
            confidence=0.6,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS


# =============================================================================
# UNKNOWN INTENT ROUTING TESTS
# =============================================================================


class TestUnknownIntentRouting:
    """Tests for UNKNOWN intent routing."""

    def test_unknown_intent_triggers_human(self):
        """Unknown intent should always trigger human."""
        extraction = create_extraction(
            intent=Intent.UNKNOWN,
            entities=Entity(),
            confidence=0.2,
        )
        result = route_command(extraction)

        assert result.brain == Brain.UNKNOWN
        assert result.requires_human is True


# =============================================================================
# ROUTING REASON TESTS
# =============================================================================


class TestRoutingReasons:
    """Tests for routing reason messages."""

    def test_routing_reason_includes_brain(self, complete_entity):
        """Routing reason should mention target brain."""
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=complete_entity,
        )
        result = route_command(extraction)

        assert "ops" in result.routing_reason.lower() or \
               "service" in result.routing_reason.lower()

    def test_routing_reason_mentions_missing_fields(self):
        """Routing reason should mention missing fields when applicable."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.SERVICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.requires_human is True
        assert "missing" in result.routing_reason.lower() or \
               len(result.missing_fields) > 0


# =============================================================================
# APPOINTMENT ROUTING TESTS
# =============================================================================


class TestAppointmentRouting:
    """Tests for appointment-related intent routing."""

    def test_schedule_appointment_with_identity(self):
        """Schedule appointment with contact should route."""
        entities = Entity(
            phone="512-555-1234",
            zip_code="78701",
            problem_description="Maintenance",
            urgency_level=UrgencyLevel.LOW,
        )
        extraction = create_extraction(
            intent=Intent.SCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS

    def test_schedule_appointment_missing_identity(self):
        """Schedule appointment without contact should need human."""
        entities = Entity(
            zip_code="78701",
            problem_description="Maintenance",
            urgency_level=UrgencyLevel.LOW,
        )
        extraction = create_extraction(
            intent=Intent.SCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True

    def test_reschedule_appointment_with_identity(self):
        """Reschedule appointment with contact should route."""
        entities = Entity(email="john@example.com")
        extraction = create_extraction(
            intent=Intent.RESCHEDULE_APPOINTMENT,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS

    def test_cancel_appointment_with_identity(self):
        """Cancel appointment with contact should route."""
        entities = Entity(phone="512-555-1234")
        extraction = create_extraction(
            intent=Intent.CANCEL_APPOINTMENT,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS


# =============================================================================
# INVOICE AND INVENTORY ROUTING TESTS
# =============================================================================


class TestInvoiceAndInventoryRouting:
    """Tests for invoice and inventory routing."""

    def test_invoice_request_with_identity(self):
        """Invoice request with identity should route."""
        entities = Entity(email="john@example.com")
        extraction = create_extraction(
            intent=Intent.INVOICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is False

    def test_invoice_request_missing_identity(self):
        """Invoice request without identity should need human."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.INVOICE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is True

    def test_inventory_inquiry_no_identity_required(self):
        """Inventory inquiry shouldn't require identity."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.INVENTORY_INQUIRY,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE
        assert result.requires_human is False

    def test_purchase_request_with_identity(self):
        """Purchase request with identity should route."""
        entities = Entity(phone="512-555-1234")
        extraction = create_extraction(
            intent=Intent.PURCHASE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.CORE


# =============================================================================
# STATUS UPDATE ROUTING TESTS
# =============================================================================


class TestStatusUpdateRouting:
    """Tests for status update routing."""

    def test_status_update_with_identity(self):
        """Status update with identity should route."""
        entities = Entity(phone="512-555-1234")
        extraction = create_extraction(
            intent=Intent.STATUS_UPDATE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is False

    def test_status_update_missing_identity(self):
        """Status update without identity should need human."""
        entities = Entity()
        extraction = create_extraction(
            intent=Intent.STATUS_UPDATE_REQUEST,
            entities=entities,
        )
        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True
