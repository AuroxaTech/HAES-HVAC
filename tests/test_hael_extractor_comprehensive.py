"""
HAES HVAC - Comprehensive HAEL Extractor Tests

Exhaustive tests for the rule-based HAEL extractor covering:
- All intents with multiple phrasings
- Entity extraction edge cases
- Urgency classification
- Confidence scoring
"""

import json
import pytest
from pathlib import Path

from src.hael.schema import Intent, UrgencyLevel
from src.hael.extractors.rule_based import RuleBasedExtractor


@pytest.fixture
def extractor():
    """Create a rule-based extractor instance."""
    return RuleBasedExtractor()


@pytest.fixture
def test_samples():
    """Load test samples from fixtures."""
    fixture_path = Path(__file__).parent / "fixtures" / "brain_test_samples.json"
    with open(fixture_path) as f:
        return json.load(f)


# =============================================================================
# INTENT CLASSIFICATION TESTS
# =============================================================================


class TestServiceRequestIntent:
    """Comprehensive tests for SERVICE_REQUEST intent classification."""

    def test_service_request_from_fixtures(self, extractor, test_samples):
        """Test all service request samples from fixtures."""
        for sample in test_samples["service_requests"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.SERVICE_REQUEST, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "My AC is not working",
        "My heater is broken",
        "The furnace won't turn on",
        "AC not cooling properly",
        "Heater not heating",
        "My air conditioner is making noise",
        "The HVAC system stopped",
        "I need my AC fixed",
        "Can someone fix my furnace?",
        "My unit is not working",
        "The system is down",
        "I need help with my AC",
        "My A/C is broken",
        "The heat pump isn't working",
        "My central air is not working",
        "Need repair for my HVAC",
        "Service request for air conditioner",
        "My heating system needs repair",
    ])
    def test_service_request_variations(self, extractor, text):
        """Test various service request phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.SERVICE_REQUEST

    def test_service_request_with_context(self, extractor):
        """Test service request with additional context."""
        texts = [
            "Hi, I'm calling because my AC isn't working and I need help",
            "Good morning, my heater stopped working overnight",
            "Yeah so my furnace is making this weird noise",
        ]
        for text in texts:
            result = extractor.extract(text)
            assert result.intent == Intent.SERVICE_REQUEST


class TestQuoteRequestIntent:
    """Comprehensive tests for QUOTE_REQUEST intent classification."""

    def test_quote_request_from_fixtures(self, extractor, test_samples):
        """Test all quote request samples from fixtures."""
        for sample in test_samples["quote_requests"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.QUOTE_REQUEST, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "I need a quote for a new AC",
        "How much for a new HVAC?",
        "Can I get an estimate?",
        "What's the price for installation?",
        "I want a quote",
        "Give me a price estimate",
        "How much would it cost?",
        "Need pricing information",
        "What's the cost to replace?",
        "Looking for an estimate",
    ])
    def test_quote_request_variations(self, extractor, text):
        """Test various quote request phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.QUOTE_REQUEST


class TestScheduleAppointmentIntent:
    """Comprehensive tests for SCHEDULE_APPOINTMENT intent classification."""

    def test_schedule_from_fixtures(self, extractor, test_samples):
        """Test all schedule appointment samples from fixtures."""
        for sample in test_samples["schedule_appointments"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.SCHEDULE_APPOINTMENT, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "I'd like to schedule an appointment",
        "Can I book a service call?",
        "Schedule a technician visit",
        "I want to set up an appointment",
        "When is your next available slot?",
        "Book an appointment for maintenance",
        "I need to arrange a service visit",
        "Schedule a tune-up",
        "I'd like to make an appointment",
    ])
    def test_schedule_variations(self, extractor, text):
        """Test various schedule appointment phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.SCHEDULE_APPOINTMENT


class TestRescheduleAppointmentIntent:
    """Comprehensive tests for RESCHEDULE_APPOINTMENT intent classification."""

    def test_reschedule_from_fixtures(self, extractor, test_samples):
        """Test all reschedule appointment samples from fixtures."""
        for sample in test_samples["reschedule_appointments"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.RESCHEDULE_APPOINTMENT, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "I need to reschedule my appointment",
        "Can I change my appointment time?",
        "Move my appointment to next week",
        "I want to reschedule",
        "Can we change the time?",
        "Reschedule my service call",
        "Change my booking",
    ])
    def test_reschedule_variations(self, extractor, text):
        """Test various reschedule appointment phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.RESCHEDULE_APPOINTMENT


class TestCancelAppointmentIntent:
    """Comprehensive tests for CANCEL_APPOINTMENT intent classification."""

    def test_cancel_from_fixtures(self, extractor, test_samples):
        """Test all cancel appointment samples from fixtures."""
        for sample in test_samples["cancel_appointments"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.CANCEL_APPOINTMENT, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "I need to cancel my appointment",
        "Cancel my service call",
        "I don't need the service anymore",
        "Please cancel my booking",
        "I want to cancel",
        "Cancel the technician visit",
        "I no longer need service",
    ])
    def test_cancel_variations(self, extractor, text):
        """Test various cancel appointment phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.CANCEL_APPOINTMENT


class TestStatusUpdateIntent:
    """Comprehensive tests for STATUS_UPDATE_REQUEST intent classification."""

    def test_status_from_fixtures(self, extractor, test_samples):
        """Test all status update samples from fixtures."""
        for sample in test_samples["status_updates"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.STATUS_UPDATE_REQUEST, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "Where is the technician?",
        "What's the status of my service call?",
        "When will the tech arrive?",
        "ETA on the technician?",
        "Status update please",
        "How long until someone arrives?",
        "Is the technician on the way?",
    ])
    def test_status_variations(self, extractor, text):
        """Test various status update phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.STATUS_UPDATE_REQUEST


class TestBillingInquiryIntent:
    """Comprehensive tests for BILLING_INQUIRY intent classification."""

    def test_billing_from_fixtures(self, extractor, test_samples):
        """Test all billing inquiry samples from fixtures."""
        for sample in test_samples["billing_inquiries"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.BILLING_INQUIRY, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "I have a question about my bill",
        "What's my balance?",
        "I don't understand this charge",
        "Why was I charged this amount?",
        "What do I owe?",
        "I need to discuss my bill",
        "Can you explain these charges?",
        "I was overcharged",
    ])
    def test_billing_variations(self, extractor, text):
        """Test various billing inquiry phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.BILLING_INQUIRY


class TestPaymentTermsInquiryIntent:
    """Comprehensive tests for PAYMENT_TERMS_INQUIRY intent classification."""

    def test_payment_terms_from_fixtures(self, extractor, test_samples):
        """Test all payment terms samples from fixtures."""
        for sample in test_samples["payment_terms_inquiries"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.PAYMENT_TERMS_INQUIRY, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "What are your payment terms?",
        "Do you offer financing?",
        "What payment options do you have?",
        "Do you accept credit cards?",
        "Can I pay in installments?",
        "Do you offer payment plans?",
    ])
    def test_payment_terms_variations(self, extractor, text):
        """Test various payment terms phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.PAYMENT_TERMS_INQUIRY


class TestInvoiceRequestIntent:
    """Comprehensive tests for INVOICE_REQUEST intent classification."""

    def test_invoice_from_fixtures(self, extractor, test_samples):
        """Test all invoice request samples from fixtures."""
        for sample in test_samples["invoice_requests"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.INVOICE_REQUEST, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "Can you send me an invoice?",
        "I need a copy of my invoice",
        "Send me a receipt please",
        "Email me the invoice",
        "I need my invoice for taxes",
        "Resend my invoice",
    ])
    def test_invoice_variations(self, extractor, text):
        """Test various invoice request phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.INVOICE_REQUEST


class TestInventoryInquiryIntent:
    """Comprehensive tests for INVENTORY_INQUIRY intent classification."""

    def test_inventory_from_fixtures(self, extractor, test_samples):
        """Test all inventory inquiry samples from fixtures."""
        for sample in test_samples["inventory_inquiries"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.INVENTORY_INQUIRY, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "Do you have this part in stock?",
        "Is the filter available?",
        "Check if you have the compressor",
        "Parts availability check",
        "What brands do you stock?",
        "Is this equipment available?",
    ])
    def test_inventory_variations(self, extractor, text):
        """Test various inventory inquiry phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.INVENTORY_INQUIRY


class TestPurchaseRequestIntent:
    """Comprehensive tests for PURCHASE_REQUEST intent classification."""

    def test_purchase_from_fixtures(self, extractor, test_samples):
        """Test all purchase request samples from fixtures."""
        for sample in test_samples["purchase_requests"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.PURCHASE_REQUEST, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "I want to order a new filter",
        "Can I buy parts from you?",
        "I need to purchase a thermostat",
        "Order replacement parts",
        "I want to buy equipment",
        "Place an order for supplies",
    ])
    def test_purchase_variations(self, extractor, text):
        """Test various purchase request phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.PURCHASE_REQUEST


class TestHiringInquiryIntent:
    """Comprehensive tests for HIRING_INQUIRY intent classification."""

    def test_hiring_from_fixtures(self, extractor, test_samples):
        """Test all hiring inquiry samples from fixtures."""
        for sample in test_samples["hiring_inquiries"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.HIRING_INQUIRY, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "Are you hiring?",
        "Do you have any job openings?",
        "I'm looking for a job",
        "How do I apply for a position?",
        "Job opportunities?",
        "Career opportunities?",
        "Hiring technicians?",
    ])
    def test_hiring_variations(self, extractor, text):
        """Test various hiring inquiry phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.HIRING_INQUIRY


class TestOnboardingInquiryIntent:
    """Comprehensive tests for ONBOARDING_INQUIRY intent classification."""

    def test_onboarding_from_fixtures(self, extractor, test_samples):
        """Test all onboarding inquiry samples from fixtures."""
        for sample in test_samples["onboarding_inquiries"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.ONBOARDING_INQUIRY, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "What's the onboarding process?",
        "First day questions",
        "New employee orientation",
        "Onboarding checklist?",
        "New hire information",
    ])
    def test_onboarding_variations(self, extractor, text):
        """Test various onboarding inquiry phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.ONBOARDING_INQUIRY


class TestPayrollInquiryIntent:
    """Comprehensive tests for PAYROLL_INQUIRY intent classification."""

    def test_payroll_from_fixtures(self, extractor, test_samples):
        """Test all payroll inquiry samples from fixtures."""
        for sample in test_samples["payroll_inquiries"]:
            result = extractor.extract(sample["text"])
            assert result.intent == Intent.PAYROLL_INQUIRY, \
                f"Failed for: '{sample['text']}' - got {result.intent}"

    @pytest.mark.parametrize("text", [
        "When do I get paid?",
        "Where's my paycheck?",
        "Payroll question",
        "What's my commission?",
        "Pay stub request",
        "When is payday?",
    ])
    def test_payroll_variations(self, extractor, text):
        """Test various payroll inquiry phrasings."""
        result = extractor.extract(text)
        assert result.intent == Intent.PAYROLL_INQUIRY


class TestUnknownIntent:
    """Tests for UNKNOWN intent classification."""

    @pytest.mark.parametrize("text", [
        "Hello",
        "What's the weather?",
        "Tell me a joke",
        "How are you?",
        "Good morning",
        "Thanks",
        "Bye",
        "asdfghjkl",
        "你好",
        "12345",
    ])
    def test_unknown_for_unrelated(self, extractor, text):
        """Unrelated text should return UNKNOWN."""
        result = extractor.extract(text)
        assert result.intent == Intent.UNKNOWN


# =============================================================================
# ENTITY EXTRACTION TESTS
# =============================================================================


class TestPhoneExtraction:
    """Comprehensive tests for phone number extraction."""

    def test_phone_from_fixtures(self, extractor, test_samples):
        """Test phone extraction from fixtures."""
        for sample in test_samples["entities_with_phone"]:
            result = extractor.extract(sample["text"])
            assert result.entities.phone == sample["expected_phone"], \
                f"Failed for: '{sample['text']}' - got {result.entities.phone}"

    @pytest.mark.parametrize("text,expected", [
        ("My number is 512-555-1234", "512-555-1234"),
        ("Call me at (512) 555-1234", "512-555-1234"),
        ("512.555.1234", "512-555-1234"),
        ("5125551234", "512-555-1234"),
        ("512 555 1234", "512-555-1234"),
        ("+1 512 555 1234", "512-555-1234"),
        ("1-512-555-1234", "512-555-1234"),
        ("(512)555-1234", "512-555-1234"),
    ])
    def test_phone_formats(self, extractor, text, expected):
        """Test various phone number formats."""
        result = extractor.extract(text)
        assert result.entities.phone == expected

    def test_phone_embedded_in_text(self, extractor):
        """Test phone extraction when embedded in longer text."""
        text = "Hi, my AC is broken. Please call me at 972-555-4321. I'm in Dallas."
        result = extractor.extract(text)
        assert result.entities.phone == "972-555-4321"


class TestEmailExtraction:
    """Comprehensive tests for email extraction."""

    def test_email_from_fixtures(self, extractor, test_samples):
        """Test email extraction from fixtures."""
        for sample in test_samples["entities_with_email"]:
            result = extractor.extract(sample["text"])
            assert result.entities.email == sample["expected_email"], \
                f"Failed for: '{sample['text']}' - got {result.entities.email}"

    @pytest.mark.parametrize("text,expected", [
        ("My email is john@example.com", "john@example.com"),
        ("Email: test.user@company.org", "test.user@company.org"),
        ("john.doe+test@gmail.com", "john.doe+test@gmail.com"),
        ("Contact user@subdomain.domain.com", "user@subdomain.domain.com"),
        ("jsmith@haes-hvac.com", "jsmith@haes-hvac.com"),
    ])
    def test_email_formats(self, extractor, text, expected):
        """Test various email formats."""
        result = extractor.extract(text)
        assert result.entities.email == expected


class TestZipCodeExtraction:
    """Comprehensive tests for ZIP code extraction."""

    def test_zip_from_fixtures(self, extractor, test_samples):
        """Test ZIP extraction from fixtures."""
        for sample in test_samples["entities_with_zip"]:
            result = extractor.extract(sample["text"])
            assert result.entities.zip_code == sample["expected_zip"], \
                f"Failed for: '{sample['text']}' - got {result.entities.zip_code}"

    @pytest.mark.parametrize("text,expected", [
        ("I'm in 78701", "78701"),
        ("ZIP code 75201", "75201"),
        ("Located in 77001", "77001"),
        ("Postal code 75001", "75001"),
        ("My zip is 78704-1234", "78704"),
    ])
    def test_zip_formats(self, extractor, text, expected):
        """Test various ZIP code formats."""
        result = extractor.extract(text)
        assert result.entities.zip_code == expected


class TestSquareFootageExtraction:
    """Comprehensive tests for square footage extraction."""

    def test_sqft_from_fixtures(self, extractor, test_samples):
        """Test square footage extraction from fixtures."""
        for sample in test_samples["entities_with_sqft"]:
            result = extractor.extract(sample["text"])
            assert result.entities.square_footage == sample["expected_sqft"], \
                f"Failed for: '{sample['text']}' - got {result.entities.square_footage}"

    @pytest.mark.parametrize("text,expected", [
        ("My house is 2500 sq ft", 2500),
        ("About 1800 square feet", 1800),
        ("3500 sqft home", 3500),
        ("2000 sf building", 2000),
        ("1500 square foot house", 1500),
    ])
    def test_sqft_formats(self, extractor, text, expected):
        """Test various square footage formats."""
        result = extractor.extract(text)
        assert result.entities.square_footage == expected


class TestTemperatureExtraction:
    """Comprehensive tests for temperature extraction."""

    def test_temp_from_fixtures(self, extractor, test_samples):
        """Test temperature extraction from fixtures."""
        for sample in test_samples["entities_with_temperature"]:
            result = extractor.extract(sample["text"])
            assert result.entities.temperature_mentioned == sample["expected_temp"], \
                f"Failed for: '{sample['text']}' - got {result.entities.temperature_mentioned}"

    @pytest.mark.parametrize("text,expected", [
        ("It's 95 degrees in here", 95),
        ("Outside temp is 30 degrees", 30),
        ("House is at 85 degrees", 85),
        ("It's 102 degrees", 102),
    ])
    def test_temp_formats(self, extractor, text, expected):
        """Test various temperature formats."""
        result = extractor.extract(text)
        assert result.entities.temperature_mentioned == expected


class TestPropertyTypeExtraction:
    """Comprehensive tests for property type extraction."""

    def test_property_type_from_fixtures(self, extractor, test_samples):
        """Test property type extraction from fixtures."""
        for sample in test_samples["property_types"]:
            result = extractor.extract(sample["text"])
            assert result.entities.property_type == sample["expected_type"], \
                f"Failed for: '{sample['text']}' - got {result.entities.property_type}"

    @pytest.mark.parametrize("text,expected", [
        ("This is for my home", "residential"),
        ("It's a residential property", "residential"),
        ("My house needs service", "residential"),
        ("For our office building", "commercial"),
        ("Commercial property", "commercial"),
        ("Our business location", "commercial"),
        ("The warehouse needs cooling", "commercial"),
    ])
    def test_property_type_keywords(self, extractor, text, expected):
        """Test property type detection."""
        result = extractor.extract(text)
        assert result.entities.property_type == expected


class TestSystemAgeExtraction:
    """Tests for system age extraction."""

    @pytest.mark.parametrize("text,expected", [
        ("The unit is 15 years old", 15),
        ("System is about 10 years old", 10),
        ("My AC is 20 years old", 20),
        ("5 year old system", 5),
    ])
    def test_system_age(self, extractor, text, expected):
        """Test system age extraction."""
        result = extractor.extract(text)
        assert result.entities.system_age_years == expected


# =============================================================================
# URGENCY CLASSIFICATION TESTS
# =============================================================================


class TestEmergencyClassification:
    """Comprehensive tests for emergency urgency classification."""

    def test_emergencies_from_fixtures(self, extractor, test_samples):
        """Test emergency classification from fixtures."""
        for sample in test_samples["emergencies"]:
            result = extractor.extract(sample["text"])
            assert result.entities.urgency_level == UrgencyLevel.EMERGENCY, \
                f"Failed for: '{sample['text']}' - got {result.entities.urgency_level}"

    @pytest.mark.parametrize("text", [
        "I smell gas!",
        "Gas leak in the house",
        "My CO detector is going off",
        "Carbon monoxide alarm",
        "There's a burning smell",
        "Burning smell from the furnace",
        "Water is flooding from my AC",
        "AC is leaking everywhere, water damage",
        "Sparks coming from the unit",
        "Smoke coming from furnace",
        "The unit caught fire",
        "Electrical burning smell",
    ])
    def test_emergency_keywords(self, extractor, text):
        """Test emergency detection from keywords."""
        result = extractor.extract(text)
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY

    def test_emergency_no_heat_cold(self, extractor):
        """No heat with cold temperature should be emergency."""
        result = extractor.extract("No heat and it's 30 degrees outside")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY
        assert result.entities.temperature_mentioned == 30

    def test_emergency_no_ac_hot(self, extractor):
        """No AC with hot temperature should be emergency."""
        result = extractor.extract("AC broken and it's 100 degrees in here")
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY
        assert result.entities.temperature_mentioned == 100


class TestHighUrgencyClassification:
    """Comprehensive tests for high urgency classification."""

    def test_high_urgency_from_fixtures(self, extractor, test_samples):
        """Test high urgency classification from fixtures."""
        for sample in test_samples["high_urgency"]:
            result = extractor.extract(sample["text"])
            assert result.entities.urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.EMERGENCY], \
                f"Failed for: '{sample['text']}' - got {result.entities.urgency_level}"

    @pytest.mark.parametrize("text", [
        "I need someone today",
        "ASAP please",
        "Urgent repair needed",
        "This is urgent",
        "Can someone come right away?",
    ])
    def test_high_urgency_keywords(self, extractor, text):
        """Test high urgency detection from keywords."""
        result = extractor.extract(text)
        assert result.entities.urgency_level == UrgencyLevel.HIGH

    @pytest.mark.parametrize("text", [
        "My elderly mother has no heat",
        "I have elderly parents",
        "Senior citizen with AC problem",
    ])
    def test_high_urgency_elderly(self, extractor, text):
        """Test high urgency for elderly mentions."""
        result = extractor.extract(text)
        assert result.entities.urgency_level == UrgencyLevel.HIGH

    @pytest.mark.parametrize("text", [
        "I have a baby with no AC",
        "Infant in the house",
        "Newborn baby needs heat",
    ])
    def test_high_urgency_baby(self, extractor, text):
        """Test high urgency for baby/infant mentions."""
        result = extractor.extract(text)
        assert result.entities.urgency_level == UrgencyLevel.HIGH


class TestMediumUrgencyClassification:
    """Tests for medium urgency classification."""

    @pytest.mark.parametrize("text", [
        "I need to get my AC repaired",
        "My heater needs fixing",
        "The unit needs service",
    ])
    def test_medium_urgency(self, extractor, text):
        """Test medium urgency for standard repair requests."""
        result = extractor.extract(text)
        assert result.entities.urgency_level == UrgencyLevel.MEDIUM


class TestLowUrgencyClassification:
    """Tests for low urgency classification."""

    @pytest.mark.parametrize("text", [
        "My AC needs a tune-up when convenient",
        "Maintenance check when you have time",
        "Routine service needed",
    ])
    def test_low_urgency(self, extractor, text):
        """Test low urgency for maintenance requests."""
        result = extractor.extract(text)
        assert result.entities.urgency_level in [UrgencyLevel.LOW, UrgencyLevel.MEDIUM]


# =============================================================================
# CONFIDENCE SCORING TESTS
# =============================================================================


class TestConfidenceScores:
    """Tests for confidence scoring."""

    def test_high_confidence_for_clear_intent(self, extractor):
        """Clear intent should have higher confidence."""
        result = extractor.extract(
            "I need to schedule an appointment for AC repair service"
        )
        assert result.confidence >= 0.6

    def test_high_confidence_with_entities(self, extractor):
        """Request with entities should have higher confidence."""
        result = extractor.extract(
            "My AC is broken. I'm John at 512-555-1234"
        )
        assert result.confidence >= 0.7

    def test_low_confidence_for_ambiguous(self, extractor):
        """Ambiguous text should have lower confidence."""
        result = extractor.extract("Hello there")
        assert result.confidence < 0.5

    def test_confidence_always_valid_range(self, extractor, test_samples):
        """Confidence should always be 0-1."""
        all_texts = []
        for key in test_samples:
            if isinstance(test_samples[key], list):
                for item in test_samples[key]:
                    if isinstance(item, dict) and "text" in item:
                        all_texts.append(item["text"])

        for text in all_texts[:50]:  # Sample 50
            result = extractor.extract(text)
            assert 0.0 <= result.confidence <= 1.0, \
                f"Invalid confidence {result.confidence} for: '{text}'"


# =============================================================================
# COMBINED ENTITY AND INTENT TESTS
# =============================================================================


class TestCompleteRequests:
    """Tests for complete requests with multiple entities."""

    def test_complete_service_request(self, extractor):
        """Test a complete service request with all entities."""
        text = (
            "My name is John Smith, my AC is broken and I'm at 123 Main St "
            "Dallas TX 75201. My phone is 214-555-1234 and email is john@email.com"
        )
        result = extractor.extract(text)

        assert result.intent == Intent.SERVICE_REQUEST
        assert result.entities.phone == "214-555-1234"
        assert result.entities.email == "john@email.com"
        assert result.entities.zip_code == "75201"
        assert result.confidence >= 0.7

    def test_complete_quote_request(self, extractor):
        """Test a complete quote request with context."""
        text = (
            "I need a quote for a new AC system. I'm Sarah at 512-555-9999, "
            "sarah@home.com. My house is 2500 sq ft, residential property"
        )
        result = extractor.extract(text)

        assert result.intent == Intent.QUOTE_REQUEST
        assert result.entities.phone == "512-555-9999"
        assert result.entities.email == "sarah@home.com"
        assert result.entities.square_footage == 2500
        assert result.entities.property_type == "residential"

    def test_emergency_with_details(self, extractor):
        """Test emergency request with contact details."""
        text = (
            "EMERGENCY! I smell gas in my basement! Call me immediately at "
            "469-555-0001. Address is 456 Oak Ave, Plano TX 75024"
        )
        result = extractor.extract(text)

        assert result.intent == Intent.SERVICE_REQUEST
        assert result.entities.urgency_level == UrgencyLevel.EMERGENCY
        assert result.entities.phone == "469-555-0001"
        assert result.entities.zip_code == "75024"
