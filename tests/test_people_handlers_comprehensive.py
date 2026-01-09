"""
HAES HVAC - Comprehensive PEOPLE Brain Handler Tests

Exhaustive tests for PEOPLE brain handlers covering:
- Hiring inquiry handling
- Onboarding inquiry handling
- Payroll inquiry handling
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
from src.brains.people.handlers import (
    handle_people_command,
    PEOPLE_INTENTS,
)
from src.brains.people.schema import PeopleStatus
from src.brains.people.hiring_policy import get_hiring_requirements, format_hiring_info
from src.brains.people.onboarding_catalog import get_onboarding_checklist, get_onboarding_summary
from src.brains.people.training_catalog import get_training_program, get_training_summary
from src.brains.people.payroll_rules import get_payroll_summary


def create_people_command(
    intent: Intent,
    entities: Entity | None = None,
    requires_human: bool = False,
    missing_fields: list[str] | None = None,
    confidence: float = 0.8,
) -> HaelCommand:
    """Helper to create HaelCommand for PEOPLE brain testing."""
    return HaelCommand(
        request_id=str(uuid4()),
        channel=Channel.VOICE,
        raw_text="Test PEOPLE command",
        intent=intent,
        brain=Brain.PEOPLE,
        entities=entities or Entity(),
        confidence=confidence,
        requires_human=requires_human,
        missing_fields=missing_fields or [],
        idempotency_key=str(uuid4()),
        created_at=datetime.utcnow(),
    )


# =============================================================================
# PEOPLE INTENTS CONFIGURATION TESTS
# =============================================================================


class TestPeopleIntentsConfiguration:
    """Tests for PEOPLE intents configuration."""

    def test_people_intents_contains_hiring(self):
        """HIRING_INQUIRY should be in PEOPLE intents."""
        assert Intent.HIRING_INQUIRY in PEOPLE_INTENTS

    def test_people_intents_contains_onboarding(self):
        """ONBOARDING_INQUIRY should be in PEOPLE intents."""
        assert Intent.ONBOARDING_INQUIRY in PEOPLE_INTENTS

    def test_people_intents_contains_payroll(self):
        """PAYROLL_INQUIRY should be in PEOPLE intents."""
        assert Intent.PAYROLL_INQUIRY in PEOPLE_INTENTS

    def test_people_intents_count(self):
        """PEOPLE should handle exactly 3 intents."""
        assert len(PEOPLE_INTENTS) == 3


# =============================================================================
# HIRING INQUIRY HANDLER TESTS
# =============================================================================


class TestHiringInquiryHandler:
    """Comprehensive tests for hiring inquiry handling."""

    def test_hiring_inquiry_no_identity_required(self):
        """Hiring inquiry shouldn't require identity."""
        entities = Entity()
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.SUCCESS
        assert result.requires_human is False

    def test_hiring_inquiry_returns_requirements(self):
        """Hiring inquiry should return requirements."""
        entities = Entity()
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.hiring_requirements is not None

    def test_hiring_inquiry_contains_interview_stages(self):
        """Hiring inquiry should contain interview stages."""
        entities = Entity()
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.data is not None
        assert "interview_stages" in result.data

    def test_hiring_inquiry_contains_approvers(self):
        """Hiring inquiry should contain approvers."""
        entities = Entity()
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert "approvers" in result.data

    def test_hiring_inquiry_approval_required(self):
        """Hiring should indicate approval is required."""
        entities = Entity()
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.data["approval_required"] is True

    def test_hiring_inquiry_with_context(self):
        """Hiring inquiry with caller context should work."""
        entities = Entity(
            full_name="John Applicant",
            phone="512-555-1234",
            email="john@example.com",
        )
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.SUCCESS

    def test_hiring_inquiry_message_content(self):
        """Hiring inquiry should have informative message."""
        entities = Entity()
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert len(result.message) > 0


# =============================================================================
# ONBOARDING INQUIRY HANDLER TESTS
# =============================================================================


class TestOnboardingInquiryHandler:
    """Comprehensive tests for onboarding inquiry handling."""

    def test_onboarding_inquiry_with_email(self):
        """Onboarding inquiry with email should succeed."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.SUCCESS
        assert result.requires_human is False

    def test_onboarding_inquiry_missing_email(self):
        """Onboarding inquiry without email should need human."""
        entities = Entity(
            full_name="John Employee",
            phone="512-555-1234",  # Phone but no email
        )
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert "email" in result.missing_fields

    def test_onboarding_inquiry_returns_checklist(self):
        """Onboarding inquiry should return checklist."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.onboarding_items is not None
        assert isinstance(result.onboarding_items, list)

    def test_onboarding_inquiry_returns_training(self):
        """Onboarding inquiry should return training program."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.training_program is not None

    def test_onboarding_inquiry_contains_summary(self):
        """Onboarding inquiry should contain summary in data."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.data is not None
        assert "summary" in result.data

    def test_onboarding_inquiry_contains_training_summary(self):
        """Onboarding inquiry should contain training summary."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert "training_summary" in result.data

    def test_onboarding_inquiry_message_content(self):
        """Onboarding message should mention items and training."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert "item" in result.message.lower() or "checklist" in result.message.lower()
        assert "training" in result.message.lower()


# =============================================================================
# PAYROLL INQUIRY HANDLER TESTS
# =============================================================================


class TestPayrollInquiryHandler:
    """Comprehensive tests for payroll inquiry handling."""

    def test_payroll_inquiry_with_email(self):
        """Payroll inquiry with email should succeed."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.SUCCESS
        assert result.requires_human is False

    def test_payroll_inquiry_missing_email(self):
        """Payroll inquiry without email should need human."""
        entities = Entity(
            full_name="John Employee",
            phone="512-555-1234",  # Phone but no email
        )
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert "email" in result.missing_fields

    def test_payroll_inquiry_returns_config(self):
        """Payroll inquiry should return payroll config in data."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.data is not None
        assert "payroll_config" in result.data

    def test_payroll_inquiry_contains_employee_email(self):
        """Payroll inquiry should record employee email."""
        entities = Entity(email="john@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert result.data["employee_email"] == "john@company.com"

    def test_payroll_inquiry_message_mentions_period(self):
        """Payroll message should mention pay period."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        # Should mention pay period (weekly, bi-weekly, etc.)
        assert any(word in result.message.lower() for word in 
                   ["weekly", "bi-weekly", "biweekly", "monthly", "period", "processed"])

    def test_payroll_inquiry_message_mentions_commission(self):
        """Payroll message should mention commission."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        assert "commission" in result.message.lower()

    def test_payroll_inquiry_commission_rules(self):
        """Payroll message should mention commission rules."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        # Should mention repairs and installs commission
        assert "repair" in result.message.lower() or "install" in result.message.lower()


# =============================================================================
# HIRING POLICY FUNCTIONS TESTS
# =============================================================================


class TestHiringPolicyFunctions:
    """Tests for hiring policy functions."""

    def test_get_hiring_requirements(self):
        """Should return hiring requirements."""
        requirements = get_hiring_requirements()
        assert requirements is not None

    def test_hiring_requirements_structure(self):
        """Hiring requirements should have proper structure."""
        requirements = get_hiring_requirements()
        assert hasattr(requirements, 'interview_stages')
        assert hasattr(requirements, 'approvers')

    def test_format_hiring_info(self):
        """Should format hiring info as string."""
        info = format_hiring_info()
        assert isinstance(info, str)
        assert len(info) > 0


# =============================================================================
# ONBOARDING CATALOG FUNCTIONS TESTS
# =============================================================================


class TestOnboardingCatalogFunctions:
    """Tests for onboarding catalog functions."""

    def test_get_onboarding_checklist(self):
        """Should return onboarding checklist."""
        checklist = get_onboarding_checklist()
        assert checklist is not None
        assert isinstance(checklist, list)

    def test_get_onboarding_summary(self):
        """Should return onboarding summary."""
        summary = get_onboarding_summary()
        assert summary is not None
        assert isinstance(summary, dict)

    def test_onboarding_summary_contains_counts(self):
        """Onboarding summary should contain item counts."""
        summary = get_onboarding_summary()
        assert "total_items" in summary
        assert "required_items" in summary


# =============================================================================
# TRAINING CATALOG FUNCTIONS TESTS
# =============================================================================


class TestTrainingCatalogFunctions:
    """Tests for training catalog functions."""

    def test_get_training_program(self):
        """Should return training program."""
        program = get_training_program()
        assert program is not None

    def test_training_program_structure(self):
        """Training program should have proper structure."""
        program = get_training_program()
        assert hasattr(program, 'onboarding_days')
        assert hasattr(program, 'topics')

    def test_get_training_summary(self):
        """Should return training summary."""
        summary = get_training_summary()
        assert summary is not None


# =============================================================================
# PAYROLL RULES FUNCTIONS TESTS
# =============================================================================


class TestPayrollRulesFunctions:
    """Tests for payroll rules functions."""

    def test_get_payroll_summary(self):
        """Should return payroll summary."""
        summary = get_payroll_summary()
        assert summary is not None
        assert isinstance(summary, dict)

    def test_payroll_summary_contains_pay_period(self):
        """Payroll summary should contain pay period."""
        summary = get_payroll_summary()
        assert "pay_period" in summary


# =============================================================================
# UNSUPPORTED INTENT TESTS
# =============================================================================


class TestUnsupportedIntent:
    """Tests for unsupported intent handling."""

    @pytest.mark.parametrize("intent", [
        Intent.SERVICE_REQUEST,
        Intent.QUOTE_REQUEST,
        Intent.BILLING_INQUIRY,
        Intent.INVOICE_REQUEST,
    ])
    def test_unsupported_intent(self, intent):
        """Non-PEOPLE intents should return unsupported."""
        command = create_people_command(
            intent=intent,
            entities=Entity(),
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.UNSUPPORTED_INTENT


# =============================================================================
# HAEL REQUIRES HUMAN PROPAGATION TESTS
# =============================================================================


class TestHaelRequiresHumanPropagation:
    """Tests for HAEL requires_human flag propagation."""

    def test_hael_requires_human_propagates_hiring(self):
        """HAEL requires_human flag should propagate for hiring."""
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=Entity(),
            requires_human=True,  # Pre-set by HAEL
            missing_fields=["some_field"],
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN
        assert result.requires_human is True

    def test_hael_requires_human_propagates_onboarding(self):
        """HAEL requires_human flag should propagate for onboarding."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=entities,
            requires_human=True,
            missing_fields=["some_field"],
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN
        assert result.requires_human is True

    def test_hael_requires_human_propagates_payroll(self):
        """HAEL requires_human flag should propagate for payroll."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
            requires_human=True,
            missing_fields=["some_field"],
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in PEOPLE brain."""

    def test_empty_entity_hiring(self):
        """Hiring should work with empty entity."""
        command = create_people_command(
            intent=Intent.HIRING_INQUIRY,
            entities=Entity(),
        )
        result = handle_people_command(command)

        # Should succeed since no identity required
        assert result.status == PeopleStatus.SUCCESS

    def test_empty_entity_onboarding(self):
        """Onboarding should need human with empty entity."""
        command = create_people_command(
            intent=Intent.ONBOARDING_INQUIRY,
            entities=Entity(),
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN

    def test_empty_entity_payroll(self):
        """Payroll should need human with empty entity."""
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=Entity(),
        )
        result = handle_people_command(command)

        assert result.status == PeopleStatus.NEEDS_HUMAN


# =============================================================================
# COMMISSION RULES TESTS
# =============================================================================


class TestCommissionRules:
    """Tests for commission rules in payroll."""

    def test_commission_mentioned_in_payroll_message(self):
        """Commission should be mentioned in payroll response."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        # Message should mention commission percentages
        assert "15%" in result.message or "5%" in result.message

    def test_commission_trigger_mentioned(self):
        """Commission trigger should be mentioned."""
        entities = Entity(email="employee@company.com")
        command = create_people_command(
            intent=Intent.PAYROLL_INQUIRY,
            entities=entities,
        )
        result = handle_people_command(command)

        # Should mention when commission is paid
        assert "invoice" in result.message.lower() or "collected" in result.message.lower()
