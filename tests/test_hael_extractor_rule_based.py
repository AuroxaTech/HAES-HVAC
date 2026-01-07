"""
HAES HVAC - Rule-Based Extractor Tests

Unit tests for the rule-based HAEL extractor.
"""

import pytest

from src.hael.schema import Intent, UrgencyLevel
from src.hael.extractors.rule_based import RuleBasedExtractor


@pytest.fixture
def extractor():
    """Create a rule-based extractor instance."""
    return RuleBasedExtractor()


class TestIntentExtraction:
    """Tests for intent classification."""

    def test_service_request_keywords(self, extractor):
        """Should detect service request from keywords."""
        result = extractor.extract("My AC is not working and I need it fixed")
        assert result.intent == Intent.SERVICE_REQUEST

    def test_quote_request_keywords(self, extractor):
        """Should detect quote request from keywords."""
        result = extractor.extract("I need a quote for a new HVAC system installation")
        assert result.intent == Intent.QUOTE_REQUEST

    def test_billing_inquiry_keywords(self, extractor):
        """Should detect billing inquiry from keywords."""
        result = extractor.extract("I have a question about my bill")
        assert result.intent == Intent.BILLING_INQUIRY

    def test_schedule_appointment_keywords(self, extractor):
        """Should detect scheduling intent from keywords."""
        result = extractor.extract("I'd like to schedule an appointment for maintenance")
        assert result.intent == Intent.SCHEDULE_APPOINTMENT

    def test_cancel_appointment_keywords(self, extractor):
        """Should detect cancellation intent from keywords."""
        result = extractor.extract("I need to cancel my service appointment")
        assert result.intent == Intent.CANCEL_APPOINTMENT

    def test_hiring_inquiry_keywords(self, extractor):
        """Should detect hiring inquiry from keywords."""
        result = extractor.extract("Are you hiring HVAC technicians?")
        assert result.intent == Intent.HIRING_INQUIRY

    def test_payroll_inquiry_keywords(self, extractor):
        """Should detect payroll inquiry from keywords."""
        result = extractor.extract("When will I get my paycheck?")
        assert result.intent == Intent.PAYROLL_INQUIRY

    def test_unknown_for_unrelated_text(self, extractor):
        """Should return unknown for unrelated text."""
        result = extractor.extract("What's the weather like today?")
        assert result.intent == Intent.UNKNOWN


class TestEntityExtraction:
    """Tests for entity extraction."""

    def test_phone_extraction_with_dashes(self, extractor):
        """Should extract phone with dashes."""
        result = extractor.extract("Call me at 512-555-1234")
        assert result.entities.phone == "512-555-1234"

    def test_phone_extraction_with_dots(self, extractor):
        """Should extract phone with dots."""
        result = extractor.extract("My number is 512.555.1234")
        assert result.entities.phone == "512-555-1234"

    def test_phone_extraction_with_parens(self, extractor):
        """Should extract phone with parentheses."""
        result = extractor.extract("Reach me at (512) 555-1234")
        assert result.entities.phone == "512-555-1234"

    def test_email_extraction(self, extractor):
        """Should extract email address."""
        result = extractor.extract("My email is john.doe@example.com")
        assert result.entities.email == "john.doe@example.com"

    def test_zip_code_extraction(self, extractor):
        """Should extract ZIP code."""
        result = extractor.extract("I'm located in 78701")
        assert result.entities.zip_code == "78701"

    def test_square_footage_extraction(self, extractor):
        """Should extract square footage."""
        result = extractor.extract("My house is about 2500 sq ft")
        assert result.entities.square_footage == 2500

    def test_square_footage_extraction_variant(self, extractor):
        """Should extract square footage with different format."""
        result = extractor.extract("It's a 1800 square feet home")
        assert result.entities.square_footage == 1800

    def test_system_age_extraction(self, extractor):
        """Should extract system age."""
        result = extractor.extract("The unit is 15 years old")
        assert result.entities.system_age_years == 15

    def test_temperature_extraction(self, extractor):
        """Should extract mentioned temperature."""
        result = extractor.extract("It's 95 degrees outside and my AC is broken")
        assert result.entities.temperature_mentioned == 95

    def test_property_type_commercial(self, extractor):
        """Should detect commercial property type."""
        result = extractor.extract("This is for our office building")
        assert result.entities.property_type == "commercial"

    def test_property_type_residential(self, extractor):
        """Should detect residential property type."""
        result = extractor.extract("I need service for my home")
        assert result.entities.property_type == "residential"


class TestUrgencyClassification:
    """Tests for urgency level classification."""

    def test_emergency_gas_leak(self, extractor):
        """Gas leak should be emergency."""
        result = extractor.extract("I smell gas coming from my furnace!")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY

    def test_emergency_no_heat(self, extractor):
        """No heat should be emergency."""
        result = extractor.extract("We have no heat and it's freezing")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY

    def test_emergency_carbon_monoxide(self, extractor):
        """Carbon monoxide should be emergency."""
        result = extractor.extract("My CO detector is going off!")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY

    def test_emergency_burning_smell(self, extractor):
        """Burning smell should be emergency."""
        result = extractor.extract("There's a burning smell from my AC unit")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY

    def test_emergency_flooding(self, extractor):
        """Water damage should be emergency."""
        result = extractor.extract("My AC is leaking and there's water damage")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY

    def test_high_urgency_today(self, extractor):
        """Request for today should be high urgency."""
        result = extractor.extract("I need someone to come out today")
        assert result.entities.urgency_level == UrgencyLevel.HIGH

    def test_high_urgency_elderly(self, extractor):
        """Elderly in household should be high urgency."""
        result = extractor.extract("My elderly parents need their AC fixed")
        assert result.entities.urgency_level == UrgencyLevel.HIGH

    def test_medium_urgency_repair(self, extractor):
        """General repair should be medium urgency."""
        result = extractor.extract("I need to get my AC repaired when convenient")
        assert result.entities.urgency_level == UrgencyLevel.MEDIUM


class TestConfidenceScores:
    """Tests for confidence scoring."""

    def test_high_confidence_for_clear_intent(self, extractor):
        """Clear intent should have higher confidence."""
        result = extractor.extract("I need to schedule an appointment for AC repair service")
        assert result.confidence >= 0.6

    def test_low_confidence_for_ambiguous(self, extractor):
        """Ambiguous text should have lower confidence."""
        result = extractor.extract("Hello there")
        assert result.confidence < 0.5

    def test_confidence_in_valid_range(self, extractor):
        """Confidence should always be 0-1."""
        texts = [
            "Fix my AC",
            "Quote please",
            "Random gibberish",
            "Hello",
            "I need service urgently my phone is 512-555-1234",
        ]
        for text in texts:
            result = extractor.extract(text)
            assert 0.0 <= result.confidence <= 1.0

