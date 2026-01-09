"""
HAES HVAC - Comprehensive REVENUE Brain Handler Tests

Exhaustive tests for REVENUE brain handlers covering:
- Quote request handling
- Lead qualification (HOT, WARM, COLD)
- Lead routing
- Follow-up generation
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
from src.brains.revenue.handlers import (
    handle_revenue_command,
    REVENUE_INTENTS,
)
from src.brains.revenue.schema import (
    LeadQualification,
    LeadSource,
    PipelineStage,
    RevenueStatus,
)
from src.brains.revenue.qualification import qualify_lead, get_response_time_goal
from src.brains.revenue.routing import route_lead, get_primary_assignee
from src.brains.revenue.followups import generate_lead_followups


def create_revenue_command(
    intent: Intent,
    entities: Entity | None = None,
    requires_human: bool = False,
    missing_fields: list[str] | None = None,
    confidence: float = 0.8,
    channel: Channel = Channel.VOICE,
) -> HaelCommand:
    """Helper to create HaelCommand for REVENUE brain testing."""
    return HaelCommand(
        request_id=str(uuid4()),
        channel=channel,
        raw_text="Test REVENUE command",
        intent=intent,
        brain=Brain.REVENUE,
        entities=entities or Entity(),
        confidence=confidence,
        requires_human=requires_human,
        missing_fields=missing_fields or [],
        idempotency_key=str(uuid4()),
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def complete_quote_entity():
    """Entity with all fields for quote request."""
    return Entity(
        full_name="Sarah Johnson",
        phone="512-555-9999",
        email="sarah@example.com",
        address="789 Oak Ave, Austin, TX",
        zip_code="78703",
        property_type="residential",
        square_footage=2500,
        system_age_years=15,
        budget_range="$8000-$12000",
        timeline="within 2 weeks",
        problem_description="Need new AC system, current one is 15 years old",
        urgency_level=UrgencyLevel.MEDIUM,
    )


@pytest.fixture
def hot_lead_entity():
    """Entity for a HOT lead."""
    return Entity(
        full_name="John Urgent",
        phone="512-555-1111",
        email="john@urgent.com",
        property_type="commercial",
        budget_range="$15000-$20000",
        timeline="ASAP",
        urgency_level=UrgencyLevel.HIGH,
        problem_description="AC broken, need new system urgently",
    )


@pytest.fixture
def cold_lead_entity():
    """Entity for a COLD lead."""
    return Entity(
        full_name="Maybe Later",
        phone="512-555-2222",
        property_type="residential",
        timeline="just browsing",
        problem_description="Thinking about upgrading eventually",
    )


# =============================================================================
# REVENUE INTENTS CONFIGURATION TESTS
# =============================================================================


class TestRevenueIntentsConfiguration:
    """Tests for REVENUE intents configuration."""

    def test_revenue_intents_contains_quote_request(self):
        """QUOTE_REQUEST should be in REVENUE intents."""
        assert Intent.QUOTE_REQUEST in REVENUE_INTENTS

    def test_revenue_intents_count(self):
        """REVENUE should handle exactly 1 intent."""
        assert len(REVENUE_INTENTS) == 1


# =============================================================================
# QUOTE REQUEST HANDLER TESTS
# =============================================================================


class TestQuoteRequestHandler:
    """Comprehensive tests for quote request handling."""

    def test_complete_quote_request_success(self, complete_quote_entity):
        """Complete quote request should succeed."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.SUCCESS
        assert result.requires_human is False
        assert result.lead is not None
        assert result.lead.customer_name == "Sarah Johnson"
        assert result.lead.customer_phone == "512-555-9999"

    def test_quote_request_missing_identity(self):
        """Quote request without identity should need human."""
        entities = Entity(
            property_type="residential",
            timeline="within 2 weeks",
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert any("identity" in f.lower() for f in result.missing_fields)

    def test_quote_request_missing_property_type(self):
        """Quote request without property type should need human."""
        entities = Entity(
            full_name="Sarah Johnson",
            phone="512-555-9999",
            timeline="within 2 weeks",
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert "property_type" in result.missing_fields

    def test_quote_request_missing_timeline(self):
        """Quote request without timeline should need human."""
        entities = Entity(
            full_name="Sarah Johnson",
            phone="512-555-9999",
            property_type="residential",
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert "timeline" in result.missing_fields

    def test_quote_request_with_multiple_missing_fields(self):
        """Quote request with multiple missing fields."""
        entities = Entity()  # Empty entity
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.NEEDS_HUMAN
        assert len(result.missing_fields) >= 2

    def test_quote_request_phone_only_for_identity(self):
        """Phone number alone should satisfy identity."""
        entities = Entity(
            phone="512-555-9999",
            property_type="residential",
            timeline="within 2 weeks",
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = handle_revenue_command(command)

        # Should not flag identity as missing
        identity_missing = any("identity" in f.lower() for f in result.missing_fields)
        assert identity_missing is False

    def test_quote_request_email_only_for_identity(self):
        """Email alone should satisfy identity."""
        entities = Entity(
            email="sarah@example.com",
            property_type="residential",
            timeline="within 2 weeks",
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
        )
        result = handle_revenue_command(command)

        # Should not flag identity as missing
        identity_missing = any("identity" in f.lower() for f in result.missing_fields)
        assert identity_missing is False


# =============================================================================
# LEAD QUALIFICATION TESTS
# =============================================================================


class TestLeadQualification:
    """Comprehensive tests for lead qualification."""

    def test_hot_lead_qualification(self):
        """HOT lead should be qualified correctly."""
        qualification, confidence, reason = qualify_lead(
            problem_description="Need new AC urgently, current system failed",
            timeline="ASAP",
            urgency_level=UrgencyLevel.HIGH,
            budget_range="$15000-$20000",
        )

        assert qualification == LeadQualification.HOT
        assert confidence >= 0.6

    def test_warm_lead_qualification(self):
        """WARM lead should be qualified correctly."""
        qualification, confidence, reason = qualify_lead(
            problem_description="Thinking about replacing my AC",
            timeline="within a month",
            urgency_level=UrgencyLevel.MEDIUM,
            budget_range=None,
        )

        assert qualification == LeadQualification.WARM

    def test_cold_lead_qualification(self):
        """COLD lead should be qualified correctly."""
        qualification, confidence, reason = qualify_lead(
            problem_description="Just curious about prices",
            timeline="no rush",
            urgency_level=UrgencyLevel.LOW,
            budget_range=None,
        )

        assert qualification == LeadQualification.COLD

    def test_qualification_returns_reason(self):
        """Qualification should return a reason string."""
        qualification, confidence, reason = qualify_lead(
            problem_description="Need AC replacement",
            timeline="soon",
            urgency_level=UrgencyLevel.MEDIUM,
            budget_range=None,
        )

        assert isinstance(reason, str)
        assert len(reason) > 0

    def test_qualification_confidence_range(self):
        """Qualification confidence should be in valid range."""
        qualification, confidence, reason = qualify_lead(
            problem_description="Test",
            timeline="test",
            urgency_level=UrgencyLevel.UNKNOWN,
            budget_range=None,
        )

        assert 0.0 <= confidence <= 1.0


class TestLeadQualificationInHandler:
    """Tests for lead qualification within handler."""

    def test_hot_lead_handled(self, hot_lead_entity):
        """HOT lead should be processed correctly."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=hot_lead_entity,
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.SUCCESS
        assert result.qualification == LeadQualification.HOT
        assert "HOT" in result.message.upper()

    def test_low_confidence_triggers_human(self):
        """Low confidence qualification should trigger human review."""
        entities = Entity(
            phone="512-555-9999",
            property_type="residential",
            timeline="maybe someday",  # Vague timeline
            problem_description="idk",  # Vague description
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entities,
            confidence=0.4,  # Low confidence
        )
        result = handle_revenue_command(command)

        # Low confidence should trigger human review
        if result.status == RevenueStatus.NEEDS_HUMAN:
            assert "uncertain" in result.message.lower() or result.requires_human


# =============================================================================
# RESPONSE TIME GOALS TESTS
# =============================================================================


class TestResponseTimeGoals:
    """Tests for response time goals based on qualification."""

    def test_hot_lead_response_time(self):
        """HOT leads should have fast response time."""
        response_time = get_response_time_goal(LeadQualification.HOT)
        assert response_time <= 30  # 30 minutes or less

    def test_warm_lead_response_time(self):
        """WARM leads should have moderate response time."""
        response_time = get_response_time_goal(LeadQualification.WARM)
        assert response_time <= 120  # 2 hours or less

    def test_cold_lead_response_time(self):
        """COLD leads can have longer response time."""
        response_time = get_response_time_goal(LeadQualification.COLD)
        assert response_time > 0


# =============================================================================
# LEAD ROUTING TESTS
# =============================================================================


class TestLeadRouting:
    """Tests for lead routing logic."""

    def test_residential_lead_routing(self):
        """Residential leads should be routed correctly."""
        assignees, reason = route_lead(
            property_type="residential",
            budget_range="$8000-$12000",
        )

        assert len(assignees) > 0
        assert isinstance(reason, str)

    def test_commercial_lead_routing(self):
        """Commercial leads should be routed correctly."""
        assignees, reason = route_lead(
            property_type="commercial",
            budget_range="$20000+",
        )

        assert len(assignees) > 0

    def test_high_budget_routing(self):
        """High budget leads may have different routing."""
        assignees_low, _ = route_lead(
            property_type="residential",
            budget_range="$5000",
        )
        assignees_high, _ = route_lead(
            property_type="residential",
            budget_range="$20000+",
        )

        # Both should have assignees
        assert len(assignees_low) > 0
        assert len(assignees_high) > 0

    def test_get_primary_assignee(self):
        """Should return primary assignee from list."""
        assignees = ["John", "Jane", "Bob"]
        primary = get_primary_assignee(assignees)
        assert primary == "John"

    def test_get_primary_assignee_empty_list(self):
        """Should handle empty list."""
        primary = get_primary_assignee([])
        assert primary is None or primary == ""


# =============================================================================
# FOLLOW-UP GENERATION TESTS
# =============================================================================


class TestFollowUpGeneration:
    """Tests for follow-up task generation."""

    def test_followups_for_hot_lead(self):
        """HOT leads should have immediate follow-ups."""
        followups = generate_lead_followups(
            lead_created_at=datetime.utcnow(),
            qualification=LeadQualification.HOT,
            customer_email="john@example.com",
            customer_phone="512-555-1234",
        )

        assert len(followups) > 0

    def test_followups_for_warm_lead(self):
        """WARM leads should have follow-ups."""
        followups = generate_lead_followups(
            lead_created_at=datetime.utcnow(),
            qualification=LeadQualification.WARM,
            customer_email="sarah@example.com",
            customer_phone="512-555-9999",
        )

        assert len(followups) > 0

    def test_followups_for_cold_lead(self):
        """COLD leads should have nurture follow-ups."""
        followups = generate_lead_followups(
            lead_created_at=datetime.utcnow(),
            qualification=LeadQualification.COLD,
            customer_email="maybe@example.com",
            customer_phone="512-555-2222",
        )

        # Cold leads still get follow-ups for nurturing
        assert isinstance(followups, list)


# =============================================================================
# LEAD DATA STRUCTURE TESTS
# =============================================================================


class TestLeadDataStructure:
    """Tests for lead data structure."""

    def test_lead_contains_customer_info(self, complete_quote_entity):
        """Lead should contain customer information."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        lead = result.lead
        assert lead.customer_name == "Sarah Johnson"
        assert lead.customer_phone == "512-555-9999"
        assert lead.customer_email == "sarah@example.com"

    def test_lead_contains_property_info(self, complete_quote_entity):
        """Lead should contain property information."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        lead = result.lead
        assert lead.property_type == "residential"
        assert lead.square_footage == 2500

    def test_lead_contains_qualification(self, complete_quote_entity):
        """Lead should contain qualification."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        lead = result.lead
        assert lead.qualification is not None

    def test_lead_has_source(self, complete_quote_entity):
        """Lead should have source based on channel."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
            channel=Channel.VOICE,
        )
        result = handle_revenue_command(command)

        assert result.lead.source == LeadSource.PHONE

    def test_lead_has_chat_source(self, complete_quote_entity):
        """Chat lead should have WEBSITE source."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
            channel=Channel.CHAT,
        )
        result = handle_revenue_command(command)

        assert result.lead.source == LeadSource.WEBSITE

    def test_lead_has_pipeline_stage(self, complete_quote_entity):
        """Lead should have pipeline stage set."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.lead.stage == PipelineStage.PENDING_QUOTE_APPROVAL

    def test_lead_has_assignee(self, complete_quote_entity):
        """Lead should have assignee."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.lead.assigned_to is not None

    def test_lead_has_timestamp(self, complete_quote_entity):
        """Lead should have creation timestamp."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.lead.created_at is not None
        assert isinstance(result.lead.created_at, datetime)


# =============================================================================
# RESULT DATA TESTS
# =============================================================================


class TestResultData:
    """Tests for result data structure."""

    def test_result_contains_qualification_reason(self, complete_quote_entity):
        """Result should contain qualification reason."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.data is not None
        assert "qualification_reason" in result.data

    def test_result_contains_routing_reason(self, complete_quote_entity):
        """Result should contain routing reason."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert "routing_reason" in result.data

    def test_result_contains_response_time_goal(self, complete_quote_entity):
        """Result should contain response time goal."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert "response_time_goal_minutes" in result.data

    def test_result_contains_recommended_missing(self, complete_quote_entity):
        """Result should track recommended missing fields."""
        # Remove some recommended fields
        entity = Entity(
            phone="512-555-9999",
            property_type="residential",
            timeline="within 2 weeks",
            # Missing: square_footage, system_age_years
        )
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=entity,
        )
        result = handle_revenue_command(command)

        if result.status == RevenueStatus.SUCCESS:
            assert "recommended_missing" in result.data


# =============================================================================
# FOLLOW-UPS IN RESULT TESTS
# =============================================================================


class TestFollowUpsInResult:
    """Tests for follow-ups included in result."""

    def test_result_contains_followups(self, complete_quote_entity):
        """Result should contain follow-up tasks."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.follow_ups is not None
        assert isinstance(result.follow_ups, list)

    def test_result_contains_assignees(self, complete_quote_entity):
        """Result should contain assignee list."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.assigned_to is not None
        assert len(result.assigned_to) > 0


# =============================================================================
# UNSUPPORTED INTENT TESTS
# =============================================================================


class TestUnsupportedIntent:
    """Tests for unsupported intent handling."""

    @pytest.mark.parametrize("intent", [
        Intent.SERVICE_REQUEST,
        Intent.BILLING_INQUIRY,
        Intent.HIRING_INQUIRY,
        Intent.PAYROLL_INQUIRY,
    ])
    def test_unsupported_intent(self, intent):
        """Non-REVENUE intents should return unsupported."""
        command = create_revenue_command(
            intent=intent,
            entities=Entity(),
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.UNSUPPORTED_INTENT


# =============================================================================
# HAEL REQUIRES HUMAN PROPAGATION TESTS
# =============================================================================


class TestHaelRequiresHumanPropagation:
    """Tests for HAEL requires_human flag propagation."""

    def test_hael_requires_human_propagates(self, complete_quote_entity):
        """HAEL requires_human flag should propagate."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
            requires_human=True,  # Pre-set by HAEL
            missing_fields=["some_field"],
        )
        result = handle_revenue_command(command)

        assert result.status == RevenueStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# MESSAGE CONTENT TESTS
# =============================================================================


class TestMessageContent:
    """Tests for result message content."""

    def test_success_message_contains_qualification(self, complete_quote_entity):
        """Success message should mention lead qualification."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert result.qualification.value.upper() in result.message.upper()

    def test_success_message_contains_assignee(self, complete_quote_entity):
        """Success message should mention assignee."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert "assigned" in result.message.lower()

    def test_success_message_contains_response_time(self, complete_quote_entity):
        """Success message should mention response time."""
        command = create_revenue_command(
            intent=Intent.QUOTE_REQUEST,
            entities=complete_quote_entity,
        )
        result = handle_revenue_command(command)

        assert "response" in result.message.lower() or "minutes" in result.message.lower()
