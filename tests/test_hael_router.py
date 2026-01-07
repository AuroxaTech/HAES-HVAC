"""
HAES HVAC - HAEL Router Tests

Unit tests for HAEL command routing.
"""

import pytest
from datetime import datetime

from src.hael.schema import (
    Brain,
    Channel,
    Entity,
    HaelExtractionResult,
    Intent,
    UrgencyLevel,
)
from src.hael.router import (
    build_hael_command,
    generate_idempotency_key,
    route_command,
    INTENT_BRAIN_MAP,
)


class TestIntentBrainMapping:
    """Tests for intent to brain mapping."""

    def test_service_request_routes_to_ops(self):
        """Service requests should route to OPS brain."""
        assert INTENT_BRAIN_MAP[Intent.SERVICE_REQUEST] == Brain.OPS

    def test_schedule_appointment_routes_to_ops(self):
        """Schedule appointment should route to OPS brain."""
        assert INTENT_BRAIN_MAP[Intent.SCHEDULE_APPOINTMENT] == Brain.OPS

    def test_quote_request_routes_to_revenue(self):
        """Quote requests should route to REVENUE brain."""
        assert INTENT_BRAIN_MAP[Intent.QUOTE_REQUEST] == Brain.REVENUE

    def test_billing_inquiry_routes_to_core(self):
        """Billing inquiries should route to CORE brain."""
        assert INTENT_BRAIN_MAP[Intent.BILLING_INQUIRY] == Brain.CORE

    def test_hiring_inquiry_routes_to_people(self):
        """Hiring inquiries should route to PEOPLE brain."""
        assert INTENT_BRAIN_MAP[Intent.HIRING_INQUIRY] == Brain.PEOPLE

    def test_unknown_routes_to_unknown(self):
        """Unknown intent should route to UNKNOWN brain."""
        assert INTENT_BRAIN_MAP[Intent.UNKNOWN] == Brain.UNKNOWN


class TestRouteCommand:
    """Tests for route_command function."""

    def test_unknown_intent_requires_human(self):
        """Unknown intent should always require human."""
        extraction = HaelExtractionResult(
            intent=Intent.UNKNOWN,
            entities=Entity(),
            confidence=0.3,
        )

        result = route_command(extraction)

        assert result.brain == Brain.UNKNOWN
        assert result.requires_human is True
        assert "intent" in result.missing_fields

    def test_service_request_with_all_fields(self):
        """Service request with all fields should not require human."""
        extraction = HaelExtractionResult(
            intent=Intent.SERVICE_REQUEST,
            entities=Entity(
                phone="512-555-1234",
                zip_code="78701",
                problem_description="AC not working",
                urgency_level=UrgencyLevel.MEDIUM,
            ),
            confidence=0.8,
        )

        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is False
        assert len(result.missing_fields) == 0

    def test_service_request_missing_identity(self):
        """Service request without identity should require human."""
        extraction = HaelExtractionResult(
            intent=Intent.SERVICE_REQUEST,
            entities=Entity(
                zip_code="78701",
                problem_description="AC not working",
                urgency_level=UrgencyLevel.MEDIUM,
            ),
            confidence=0.8,
        )

        result = route_command(extraction)

        assert result.brain == Brain.OPS
        assert result.requires_human is True
        assert any("identity" in f for f in result.missing_fields)

    def test_quote_request_missing_property_type(self):
        """Quote request without property type should require human."""
        extraction = HaelExtractionResult(
            intent=Intent.QUOTE_REQUEST,
            entities=Entity(
                email="test@example.com",
                timeline="next month",
            ),
            confidence=0.8,
        )

        result = route_command(extraction)

        assert result.brain == Brain.REVENUE
        assert result.requires_human is True
        assert "property_type" in result.missing_fields

    def test_low_confidence_requires_human(self):
        """Low confidence extraction should require human."""
        extraction = HaelExtractionResult(
            intent=Intent.BILLING_INQUIRY,
            entities=Entity(email="test@example.com"),
            confidence=0.3,  # Below 0.5 threshold
        )

        result = route_command(extraction)

        assert result.requires_human is True


class TestGenerateIdempotencyKey:
    """Tests for idempotency key generation."""

    def test_same_inputs_same_key(self):
        """Same inputs should generate same key."""
        entities = Entity(phone="512-555-1234")
        timestamp = datetime(2026, 1, 8, 12, 0, 0)

        key1 = generate_idempotency_key(
            Channel.VOICE, entities, Intent.SERVICE_REQUEST, timestamp
        )
        key2 = generate_idempotency_key(
            Channel.VOICE, entities, Intent.SERVICE_REQUEST, timestamp
        )

        assert key1 == key2

    def test_different_channel_different_key(self):
        """Different channel should generate different key."""
        entities = Entity(phone="512-555-1234")
        timestamp = datetime(2026, 1, 8, 12, 0, 0)

        key_voice = generate_idempotency_key(
            Channel.VOICE, entities, Intent.SERVICE_REQUEST, timestamp
        )
        key_chat = generate_idempotency_key(
            Channel.CHAT, entities, Intent.SERVICE_REQUEST, timestamp
        )

        assert key_voice != key_chat

    def test_different_intent_different_key(self):
        """Different intent should generate different key."""
        entities = Entity(phone="512-555-1234")
        timestamp = datetime(2026, 1, 8, 12, 0, 0)

        key1 = generate_idempotency_key(
            Channel.VOICE, entities, Intent.SERVICE_REQUEST, timestamp
        )
        key2 = generate_idempotency_key(
            Channel.VOICE, entities, Intent.BILLING_INQUIRY, timestamp
        )

        assert key1 != key2

    def test_key_is_32_chars(self):
        """Key should be 32 characters (truncated SHA256)."""
        entities = Entity(phone="512-555-1234")
        timestamp = datetime(2026, 1, 8, 12, 0, 0)

        key = generate_idempotency_key(
            Channel.VOICE, entities, Intent.SERVICE_REQUEST, timestamp
        )

        assert len(key) == 32


class TestBuildHaelCommand:
    """Tests for building complete HAEL commands."""

    def test_builds_complete_command(self):
        """Should build a complete command with all fields."""
        extraction = HaelExtractionResult(
            intent=Intent.SERVICE_REQUEST,
            entities=Entity(
                phone="512-555-1234",
                zip_code="78701",
                problem_description="AC not working",
                urgency_level=UrgencyLevel.EMERGENCY,
            ),
            confidence=0.9,
        )
        routing = route_command(extraction)

        command = build_hael_command(
            request_id="test-123",
            channel=Channel.VOICE,
            raw_text="My AC is broken",
            extraction=extraction,
            routing=routing,
        )

        assert command.request_id == "test-123"
        assert command.channel == Channel.VOICE
        assert command.intent == Intent.SERVICE_REQUEST
        assert command.brain == Brain.OPS
        assert command.entities.phone == "512-555-1234"
        assert command.confidence == 0.9
        assert len(command.idempotency_key) == 32

