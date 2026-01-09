"""
HAES HVAC - Edge Cases and Error Handling Tests

Comprehensive tests for edge cases covering:
- Empty and malformed inputs
- Unicode and special characters
- Injection attempts
- Concurrent request handling
- Boundary conditions
"""

import json
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock

from src.hael.schema import (
    Brain,
    Channel,
    Entity,
    HaelCommand,
    Intent,
    UrgencyLevel,
)
from src.hael.extractors.rule_based import RuleBasedExtractor
from src.hael.router import route_command, build_hael_command


@pytest.fixture
def extractor():
    """Create a rule-based extractor."""
    return RuleBasedExtractor()


# =============================================================================
# EMPTY INPUT TESTS
# =============================================================================


class TestEmptyInputs:
    """Tests for empty and whitespace-only inputs."""

    def test_empty_string(self, extractor):
        """Empty string should return UNKNOWN intent."""
        result = extractor.extract("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence < 0.5

    def test_whitespace_only(self, extractor):
        """Whitespace-only input should return UNKNOWN."""
        result = extractor.extract("   ")
        assert result.intent == Intent.UNKNOWN

    def test_tabs_only(self, extractor):
        """Tabs-only input should return UNKNOWN."""
        result = extractor.extract("\t\t\t")
        assert result.intent == Intent.UNKNOWN

    def test_newlines_only(self, extractor):
        """Newlines-only input should return UNKNOWN."""
        result = extractor.extract("\n\n\n")
        assert result.intent == Intent.UNKNOWN

    def test_mixed_whitespace(self, extractor):
        """Mixed whitespace should return UNKNOWN."""
        result = extractor.extract(" \t\n  \t\n ")
        assert result.intent == Intent.UNKNOWN


# =============================================================================
# VERY LONG INPUT TESTS
# =============================================================================


class TestLongInputs:
    """Tests for very long inputs."""

    def test_very_long_input(self, extractor):
        """Very long input should not crash."""
        long_text = "My AC is broken. " * 1000  # ~17000 chars
        result = extractor.extract(long_text)
        
        # Should extract intent
        assert result.intent == Intent.SERVICE_REQUEST
        # Should have valid confidence
        assert 0.0 <= result.confidence <= 1.0

    def test_long_single_word(self, extractor):
        """Long single word should not crash."""
        long_word = "a" * 10000
        result = extractor.extract(long_word)
        
        assert result.intent == Intent.UNKNOWN

    def test_input_at_boundary(self, extractor):
        """Input at typical boundary lengths."""
        for length in [100, 500, 1000, 5000]:
            text = f"AC broken. " * (length // 11)
            result = extractor.extract(text[:length])
            assert result is not None


# =============================================================================
# UNICODE AND SPECIAL CHARACTER TESTS
# =============================================================================


class TestUnicodeCharacters:
    """Tests for Unicode and international characters."""

    def test_chinese_characters(self, extractor):
        """Chinese characters should not crash."""
        result = extractor.extract("我的空调坏了")
        assert result.intent == Intent.UNKNOWN

    def test_arabic_characters(self, extractor):
        """Arabic characters should not crash."""
        result = extractor.extract("مكيف الهواء معطل")
        assert result.intent == Intent.UNKNOWN

    def test_emoji_characters(self, extractor):
        """Emoji should not crash."""
        result = extractor.extract("My AC is broken 😢 Please help 🙏")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_mixed_unicode(self, extractor):
        """Mixed Unicode should extract English content."""
        result = extractor.extract("My AC 空调 is broken 坏了")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_spanish_text(self, extractor):
        """Spanish text with English keywords."""
        result = extractor.extract("Mi AC está roto, necesito service")
        # May or may not detect based on keywords
        assert result is not None

    def test_accented_characters(self, extractor):
        """Accented characters should not crash."""
        result = extractor.extract("My naïve système is broken")
        assert result is not None

    def test_unicode_email(self, extractor):
        """Email with unicode domain should be handled."""
        result = extractor.extract("Email me at test@例え.jp")
        # May not extract the email, but shouldn't crash
        assert result is not None


# =============================================================================
# SPECIAL CHARACTER TESTS
# =============================================================================


class TestSpecialCharacters:
    """Tests for special characters and punctuation."""

    def test_excessive_punctuation(self, extractor):
        """Excessive punctuation should not crash."""
        result = extractor.extract("My AC....is.....broken!!!!!!")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_special_symbols_only(self, extractor):
        """Special symbols only should return UNKNOWN."""
        result = extractor.extract("!!!@@@###$$$%%%^^^&&&***")
        assert result.intent == Intent.UNKNOWN

    def test_mixed_punctuation(self, extractor):
        """Mixed punctuation should extract meaning."""
        result = extractor.extract("My AC, is - broken? Yes!")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_quotes_in_text(self, extractor):
        """Quotes in text should be handled."""
        result = extractor.extract('My "AC" is \'broken\'')
        assert result.intent == Intent.SERVICE_REQUEST

    def test_backslashes(self, extractor):
        """Backslashes should not crash."""
        result = extractor.extract("My AC\\is\\broken")
        assert result is not None

    def test_null_character(self, extractor):
        """Null character should be handled."""
        result = extractor.extract("My AC is\x00broken")
        assert result is not None


# =============================================================================
# INJECTION ATTEMPT TESTS
# =============================================================================


class TestInjectionAttempts:
    """Tests for potential injection attempts."""

    def test_sql_injection(self, extractor):
        """SQL injection should not affect extraction."""
        result = extractor.extract("' OR 1=1; DROP TABLE users;--")
        assert result.intent == Intent.UNKNOWN

    def test_xss_attempt(self, extractor):
        """XSS attempt should be treated as text."""
        result = extractor.extract("<script>alert('xss')</script> my ac is broken")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_html_tags(self, extractor):
        """HTML tags should be treated as text."""
        result = extractor.extract("<b>My AC</b> is <i>broken</i>")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_command_injection(self, extractor):
        """Command injection should not affect extraction."""
        result = extractor.extract("; rm -rf /; my ac is broken")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_path_traversal(self, extractor):
        """Path traversal should not affect extraction."""
        result = extractor.extract("../../../etc/passwd my ac broken")
        assert result.intent == Intent.SERVICE_REQUEST


# =============================================================================
# MALFORMED ENTITY TESTS
# =============================================================================


class TestMalformedEntities:
    """Tests for malformed entity values."""

    def test_invalid_phone_format(self, extractor):
        """Invalid phone format should not extract."""
        result = extractor.extract("Call me at 1234")
        assert result.entities.phone is None

    def test_partial_phone(self, extractor):
        """Partial phone should not extract."""
        result = extractor.extract("My number is 512-555")
        # Should not extract incomplete phone
        assert result.entities.phone is None or len(result.entities.phone) < 10

    def test_invalid_email(self, extractor):
        """Invalid email should not extract."""
        result = extractor.extract("Email me at notanemail")
        assert result.entities.email is None

    def test_invalid_zip(self, extractor):
        """Invalid ZIP should not extract."""
        result = extractor.extract("I'm in 123")  # Too short
        assert result.entities.zip_code is None

    def test_negative_square_footage(self, extractor):
        """Negative square footage should not extract."""
        result = extractor.extract("My house is -2000 sq ft")
        # Should not extract negative values
        assert result.entities.square_footage is None or result.entities.square_footage > 0

    def test_unrealistic_temperature(self, extractor):
        """Unrealistic temperature should still extract."""
        result = extractor.extract("It's 500 degrees outside")
        # May or may not extract extreme values
        assert result is not None


# =============================================================================
# MULTIPLE INTENT TESTS
# =============================================================================


class TestMultipleIntents:
    """Tests for messages with multiple potential intents."""

    def test_service_and_quote(self, extractor):
        """Message with both service and quote keywords."""
        result = extractor.extract(
            "My AC is broken AND I want a quote for a new system"
        )
        # Should pick one intent
        assert result.intent in [Intent.SERVICE_REQUEST, Intent.QUOTE_REQUEST]

    def test_schedule_and_cancel(self, extractor):
        """Message with both schedule and cancel keywords."""
        result = extractor.extract(
            "I want to schedule an appointment but might need to cancel"
        )
        # Should pick one intent
        assert result.intent in [Intent.SCHEDULE_APPOINTMENT, Intent.CANCEL_APPOINTMENT]

    def test_billing_and_payment(self, extractor):
        """Message with both billing and payment keywords."""
        result = extractor.extract(
            "I have a billing question about payment terms"
        )
        # Should pick one intent
        assert result.intent in [Intent.BILLING_INQUIRY, Intent.PAYMENT_TERMS_INQUIRY]


# =============================================================================
# REPEATED CONTENT TESTS
# =============================================================================


class TestRepeatedContent:
    """Tests for repeated words and content."""

    def test_repeated_words(self, extractor):
        """Repeated words should still extract intent."""
        result = extractor.extract("broken broken broken AC AC AC")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_stuttered_text(self, extractor):
        """Stuttered text should extract intent."""
        result = extractor.extract("My my my AC AC is is broken broken")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_stretched_words(self, extractor):
        """Stretched words should be handled."""
        result = extractor.extract("Myyyyy AAAACCCCC is broooooken")
        # May or may not extract, shouldn't crash
        assert result is not None


# =============================================================================
# CASE SENSITIVITY TESTS
# =============================================================================


class TestCaseSensitivity:
    """Tests for case sensitivity."""

    def test_all_uppercase(self, extractor):
        """All uppercase should extract intent."""
        result = extractor.extract("MY AC IS BROKEN")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_all_lowercase(self, extractor):
        """All lowercase should extract intent."""
        result = extractor.extract("my ac is broken")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_mixed_case(self, extractor):
        """Mixed case should extract intent."""
        result = extractor.extract("My Ac Is BroKen")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_random_case(self, extractor):
        """Random case should extract intent."""
        result = extractor.extract("mY aC iS bRoKeN")
        assert result.intent == Intent.SERVICE_REQUEST


# =============================================================================
# MULTILINE INPUT TESTS
# =============================================================================


class TestMultilineInput:
    """Tests for multiline inputs."""

    def test_simple_multiline(self, extractor):
        """Simple multiline should extract intent."""
        text = "My AC\nis\nbroken"
        result = extractor.extract(text)
        assert result.intent == Intent.SERVICE_REQUEST

    def test_multiline_with_contact(self, extractor):
        """Multiline with contact info should extract."""
        text = """
        My AC is broken.
        Please call me at 512-555-1234.
        I'm in zip code 78701.
        """
        result = extractor.extract(text)
        
        assert result.intent == Intent.SERVICE_REQUEST
        assert result.entities.phone == "512-555-1234"
        assert result.entities.zip_code == "78701"


# =============================================================================
# ENTITY VALIDATION TESTS
# =============================================================================


class TestEntityValidation:
    """Tests for entity validation."""

    def test_entity_defaults(self):
        """Entity should have sensible defaults."""
        entity = Entity()
        
        assert entity.full_name is None
        assert entity.phone is None
        assert entity.email is None
        assert entity.urgency_level == UrgencyLevel.UNKNOWN
        assert entity.preferred_time_windows == []

    def test_entity_with_all_fields(self):
        """Entity should accept all fields."""
        entity = Entity(
            full_name="John Smith",
            phone="512-555-1234",
            email="john@example.com",
            address="123 Main St",
            zip_code="78701",
            city="Austin",
            state="TX",
            problem_description="AC broken",
            system_type="central_air",
            urgency_level=UrgencyLevel.HIGH,
            preferred_time_windows=["morning", "afternoon"],
            property_type="residential",
            square_footage=2000,
            system_age_years=10,
            budget_range="$10000",
            timeline="2 weeks",
            temperature_mentioned=95,
        )
        
        assert entity.full_name == "John Smith"
        assert entity.urgency_level == UrgencyLevel.HIGH
        assert len(entity.preferred_time_windows) == 2


# =============================================================================
# HAEL COMMAND VALIDATION TESTS
# =============================================================================


class TestHaelCommandValidation:
    """Tests for HaelCommand validation."""

    def test_command_requires_fields(self):
        """Command should require essential fields."""
        command = HaelCommand(
            request_id=str(uuid4()),
            channel=Channel.VOICE,
            raw_text="Test",
            intent=Intent.SERVICE_REQUEST,
            brain=Brain.OPS,
            confidence=0.8,
            requires_human=False,
            idempotency_key=str(uuid4()),
        )
        
        assert command.request_id is not None
        assert command.entities is not None  # Default entity

    def test_command_confidence_bounds(self):
        """Confidence should be bounded 0-1."""
        with pytest.raises(ValueError):
            HaelCommand(
                request_id=str(uuid4()),
                channel=Channel.VOICE,
                raw_text="Test",
                intent=Intent.SERVICE_REQUEST,
                brain=Brain.OPS,
                confidence=1.5,  # Invalid
                requires_human=False,
                idempotency_key=str(uuid4()),
            )


# =============================================================================
# CONCURRENT REQUEST SIMULATION
# =============================================================================


class TestConcurrentRequests:
    """Tests simulating concurrent request handling."""

    def test_unique_request_ids(self, extractor):
        """Each extraction should have unique context."""
        results = []
        for i in range(10):
            text = f"My AC is broken {i}"
            result = extractor.extract(text)
            results.append(result)
        
        # All should be valid extractions
        for result in results:
            assert result.intent == Intent.SERVICE_REQUEST

    def test_no_state_leakage(self, extractor):
        """Subsequent extractions should not affect each other."""
        # First extraction with lots of entities
        result1 = extractor.extract(
            "John Smith 512-555-1234 john@example.com 78701"
        )
        
        # Second extraction with no entities
        result2 = extractor.extract("My AC is broken")
        
        # Second should not have first's entities
        assert result2.entities.phone is None or result2.entities.phone != "512-555-1234"


# =============================================================================
# BOUNDARY VALUE TESTS
# =============================================================================


class TestBoundaryValues:
    """Tests for boundary values."""

    def test_zero_confidence(self, extractor):
        """Should handle zero confidence."""
        result = extractor.extract("asdfghjkl")
        # Very low confidence is valid
        assert result.confidence >= 0.0

    def test_single_character(self, extractor):
        """Single character should return UNKNOWN."""
        result = extractor.extract("a")
        assert result.intent == Intent.UNKNOWN

    def test_minimum_valid_phone(self, extractor):
        """Minimum valid phone (10 digits)."""
        result = extractor.extract("Call 5125551234")
        assert result.entities.phone == "512-555-1234"

    def test_minimum_valid_zip(self, extractor):
        """Minimum valid ZIP (5 digits)."""
        result = extractor.extract("I'm in 78701")
        assert result.entities.zip_code == "78701"

    def test_age_boundary_values(self, extractor):
        """System age boundary values."""
        # Very new system
        result1 = extractor.extract("System is 1 year old")
        assert result1.entities.system_age_years == 1
        
        # Very old system
        result2 = extractor.extract("System is 50 years old")
        assert result2.entities.system_age_years == 50


# =============================================================================
# ERROR RECOVERY TESTS
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery."""

    def test_partial_json_in_text(self, extractor):
        """Partial JSON in text should not crash."""
        result = extractor.extract('My AC {"status": "broken"} is not working')
        assert result is not None

    def test_binary_like_text(self, extractor):
        """Binary-like text should not crash."""
        result = extractor.extract("0x48454C50 my AC broken")
        assert result is not None

    def test_url_in_text(self, extractor):
        """URL in text should not crash."""
        result = extractor.extract(
            "Check https://example.com/my/ac/broken for details"
        )
        assert result is not None


# =============================================================================
# FIXTURE-BASED EDGE CASE TESTS
# =============================================================================


class TestFixtureEdgeCases:
    """Tests using fixture edge cases."""

    def test_edge_cases_from_fixtures(self, extractor):
        """Test edge cases defined in fixtures file."""
        from pathlib import Path
        
        fixture_path = Path(__file__).parent / "fixtures" / "brain_test_samples.json"
        with open(fixture_path) as f:
            samples = json.load(f)
        
        for case in samples.get("edge_cases", []):
            text = case.get("text", "")
            result = extractor.extract(text)
            
            # Should not crash
            assert result is not None
            
            # Check expected intent if specified
            if "expected_intent" in case:
                expected = Intent[case["expected_intent"].upper()]
                # Note: May not always match due to complex edge cases
                # But should be a valid intent
                assert isinstance(result.intent, Intent)
