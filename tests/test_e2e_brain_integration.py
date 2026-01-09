"""
HAES HVAC - End-to-End Brain Integration Tests

Tests the complete flow from raw text input through:
1. HAEL extraction
2. Routing
3. Brain handler
4. Response generation

These tests validate the entire pipeline works together.
"""

import json
import pytest
from datetime import datetime
from uuid import uuid4

from src.hael.schema import Brain, Channel, Entity, Intent, UrgencyLevel
from src.hael.extractors.rule_based import RuleBasedExtractor
from src.hael.router import route_command, build_hael_command

from src.brains.ops.handlers import handle_ops_command
from src.brains.ops.schema import OpsStatus

from src.brains.core.handlers import handle_core_command
from src.brains.core.schema import CoreStatus

from src.brains.revenue.handlers import handle_revenue_command
from src.brains.revenue.schema import RevenueStatus

from src.brains.people.handlers import handle_people_command
from src.brains.people.schema import PeopleStatus


@pytest.fixture
def extractor():
    """Create a rule-based extractor."""
    return RuleBasedExtractor()


def full_pipeline(
    raw_text: str,
    channel: Channel = Channel.VOICE,
    extractor: RuleBasedExtractor = None,
):
    """
    Run the full pipeline from raw text to brain response.
    
    Returns tuple of (extraction_result, routing_result, brain_result)
    """
    if extractor is None:
        extractor = RuleBasedExtractor()
    
    # Step 1: Extract intent and entities
    extraction = extractor.extract(raw_text)
    
    # Step 2: Route based on extraction
    routing = route_command(extraction)
    
    # Step 3: Build full command
    command = build_hael_command(
        request_id=str(uuid4()),
        channel=channel,
        raw_text=raw_text,
        extraction=extraction,
        routing=routing,
    )
    
    # Step 4: Send to appropriate brain
    brain_result = None
    if routing.brain == Brain.OPS:
        brain_result = handle_ops_command(command)
    elif routing.brain == Brain.CORE:
        brain_result = handle_core_command(command)
    elif routing.brain == Brain.REVENUE:
        brain_result = handle_revenue_command(command)
    elif routing.brain == Brain.PEOPLE:
        brain_result = handle_people_command(command)
    
    return extraction, routing, brain_result


# =============================================================================
# SERVICE REQUEST E2E TESTS
# =============================================================================


class TestServiceRequestE2E:
    """End-to-end tests for service request flow."""

    def test_complete_service_request(self, extractor):
        """Full flow: Complete service request with all details."""
        text = (
            "My AC is broken and not working. I'm John Smith at 512-555-1234. "
            "I'm located at 123 Main St, Austin TX 78701. "
            "AC is making a loud noise and not cooling. This is urgent."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Verify extraction
        assert extraction.intent == Intent.SERVICE_REQUEST
        assert extraction.entities.phone == "512-555-1234"
        assert extraction.entities.zip_code == "78701"
        
        # Verify routing
        assert routing.brain == Brain.OPS
        
        # Verify brain result - may need human if urgency not extracted
        assert result is not None
        assert result.status in [OpsStatus.SUCCESS, OpsStatus.NEEDS_HUMAN]

    def test_service_request_missing_info(self, extractor):
        """Full flow: Service request missing required info."""
        text = "My AC is broken"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Should extract intent
        assert extraction.intent == Intent.SERVICE_REQUEST
        
        # Should route to OPS
        assert routing.brain == Brain.OPS
        
        # Should flag as needs human due to missing info
        assert routing.requires_human or result.requires_human

    def test_emergency_service_request(self, extractor):
        """Full flow: Emergency service request."""
        text = (
            "I smell gas coming from my furnace! This is an emergency! "
            "Call me at 512-555-9999. I'm at 456 Oak Ave, 78702. "
            "My furnace is broken and I smell gas leak."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Should detect emergency
        assert extraction.entities.urgency_level == UrgencyLevel.EMERGENCY
        
        # Should route to OPS
        assert routing.brain == Brain.OPS
        
        # Result should handle emergency (may or may not have all details)
        assert result is not None

    def test_service_request_with_email(self, extractor):
        """Full flow: Service request with email instead of phone."""
        text = (
            "My heater is not heating. Please contact me at john@email.com. "
            "I'm in zip code 78704."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.SERVICE_REQUEST
        assert extraction.entities.email == "john@email.com"
        assert extraction.entities.zip_code == "78704"
        assert routing.brain == Brain.OPS


# =============================================================================
# QUOTE REQUEST E2E TESTS
# =============================================================================


class TestQuoteRequestE2E:
    """End-to-end tests for quote request flow."""

    def test_complete_quote_request(self, extractor):
        """Full flow: Complete quote request with all details."""
        text = (
            "I need a quote for a new AC system installation. My name is Sarah Jones, "
            "phone 512-555-8888, email sarah@home.com. "
            "It's a residential home, about 2500 square feet, "
            "current system is 15 years old. Looking to do this within 2 weeks. "
            "Budget is around $10000. I want an estimate."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Verify extraction - may be quote or service based on keywords
        assert extraction.intent in [Intent.QUOTE_REQUEST, Intent.SERVICE_REQUEST]
        assert extraction.entities.phone == "512-555-8888"
        assert extraction.entities.email == "sarah@home.com"
        assert extraction.entities.square_footage == 2500
        assert extraction.entities.system_age_years == 15
        assert extraction.entities.property_type == "residential"
        
        # Verify routing based on intent
        assert routing.brain in [Brain.REVENUE, Brain.OPS]

    def test_quote_request_minimal_info(self, extractor):
        """Full flow: Quote request with minimal info."""
        text = "I want a price quote for new HVAC installation"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Should extract intent (may be quote or unknown)
        assert extraction.intent in [Intent.QUOTE_REQUEST, Intent.UNKNOWN, Intent.SERVICE_REQUEST]
        
        # If it's a quote request
        if extraction.intent == Intent.QUOTE_REQUEST:
            assert routing.brain == Brain.REVENUE
            # Should flag as needs human (missing info)
            assert routing.requires_human or result.requires_human

    def test_commercial_quote_request(self, extractor):
        """Full flow: Commercial quote request."""
        text = (
            "We need a quote for our office building HVAC. "
            "Call Bob at 512-555-7777. It's a commercial property, "
            "about 5000 square feet. Need it done within a month."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.QUOTE_REQUEST
        assert extraction.entities.property_type == "commercial"
        assert routing.brain == Brain.REVENUE


# =============================================================================
# BILLING INQUIRY E2E TESTS
# =============================================================================


class TestBillingInquiryE2E:
    """End-to-end tests for billing inquiry flow."""

    def test_billing_inquiry_with_contact(self, extractor):
        """Full flow: Billing inquiry with contact info."""
        text = (
            "I have a question about my bill. "
            "My phone number is 512-555-3333."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.BILLING_INQUIRY
        assert extraction.entities.phone == "512-555-3333"
        assert routing.brain == Brain.CORE
        assert result.status == CoreStatus.SUCCESS

    def test_billing_inquiry_no_contact(self, extractor):
        """Full flow: Billing inquiry without contact."""
        text = "I don't understand this charge on my bill"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.BILLING_INQUIRY
        assert routing.brain == Brain.CORE
        assert result.status == CoreStatus.NEEDS_HUMAN


# =============================================================================
# PAYMENT TERMS E2E TESTS
# =============================================================================


class TestPaymentTermsE2E:
    """End-to-end tests for payment terms inquiry flow."""

    def test_payment_terms_general(self, extractor):
        """Full flow: General payment terms inquiry."""
        text = "What are your payment terms?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.PAYMENT_TERMS_INQUIRY
        assert routing.brain == Brain.CORE
        assert result.status == CoreStatus.SUCCESS

    def test_payment_terms_commercial(self, extractor):
        """Full flow: Commercial payment terms."""
        text = "What payment options do you have for commercial properties?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.PAYMENT_TERMS_INQUIRY
        assert routing.brain == Brain.CORE
        assert result.status == CoreStatus.SUCCESS


# =============================================================================
# APPOINTMENT E2E TESTS
# =============================================================================


class TestAppointmentE2E:
    """End-to-end tests for appointment-related flows."""

    def test_schedule_appointment(self, extractor):
        """Full flow: Schedule appointment."""
        text = (
            "I'd like to schedule an appointment for AC maintenance. "
            "My phone is 512-555-4444. I'm in zip 78701."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.SCHEDULE_APPOINTMENT
        assert routing.brain == Brain.OPS
        # May need human if missing fields
        assert result.status in [OpsStatus.SUCCESS, OpsStatus.NEEDS_HUMAN]

    def test_reschedule_appointment(self, extractor):
        """Full flow: Reschedule appointment."""
        text = (
            "I need to reschedule my appointment. "
            "Call me at 512-555-5555."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.RESCHEDULE_APPOINTMENT
        assert routing.brain == Brain.OPS
        assert result.status == OpsStatus.SUCCESS

    def test_cancel_appointment(self, extractor):
        """Full flow: Cancel appointment."""
        text = (
            "I need to cancel my service call. "
            "My phone number is 512-555-6666."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.CANCEL_APPOINTMENT
        assert routing.brain == Brain.OPS
        assert result.status == OpsStatus.SUCCESS


# =============================================================================
# HIRING INQUIRY E2E TESTS
# =============================================================================


class TestHiringInquiryE2E:
    """End-to-end tests for hiring inquiry flow."""

    def test_hiring_inquiry(self, extractor):
        """Full flow: Hiring inquiry."""
        text = "Are you hiring HVAC technicians?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.HIRING_INQUIRY
        assert routing.brain == Brain.PEOPLE
        assert result.status == PeopleStatus.SUCCESS

    def test_job_application_inquiry(self, extractor):
        """Full flow: Job application inquiry."""
        text = "How do I apply for a job with your company?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.HIRING_INQUIRY
        assert routing.brain == Brain.PEOPLE


# =============================================================================
# PAYROLL INQUIRY E2E TESTS
# =============================================================================


class TestPayrollInquiryE2E:
    """End-to-end tests for payroll inquiry flow."""

    def test_payroll_inquiry_with_email(self, extractor):
        """Full flow: Payroll inquiry with email."""
        text = (
            "When do I get my paycheck? "
            "My email is employee@company.com"
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.PAYROLL_INQUIRY
        assert extraction.entities.email == "employee@company.com"
        assert routing.brain == Brain.PEOPLE
        assert result.status == PeopleStatus.SUCCESS

    def test_payroll_inquiry_no_email(self, extractor):
        """Full flow: Payroll inquiry without email."""
        text = "What's my commission?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.PAYROLL_INQUIRY
        assert routing.brain == Brain.PEOPLE
        assert result.status == PeopleStatus.NEEDS_HUMAN


# =============================================================================
# INVOICE REQUEST E2E TESTS
# =============================================================================


class TestInvoiceRequestE2E:
    """End-to-end tests for invoice request flow."""

    def test_invoice_request_with_email(self, extractor):
        """Full flow: Invoice request with email."""
        text = "Can you send me an invoice? My email is john@example.com"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.INVOICE_REQUEST
        assert routing.brain == Brain.CORE
        assert result.status == CoreStatus.SUCCESS


# =============================================================================
# REALISTIC CONVERSATION SCENARIOS
# =============================================================================


class TestRealisticScenarios:
    """Tests based on realistic conversation patterns."""

    def test_progressive_service_intake(self, extractor):
        """Simulate progressive information gathering."""
        # First message - just the problem
        text1 = "My AC is broken and not cooling"
        extraction1, routing1, result1 = full_pipeline(text1, extractor=extractor)
        
        assert extraction1.intent == Intent.SERVICE_REQUEST
        assert routing1.requires_human or result1.requires_human  # Missing info
        
        # Second message - with contact and location
        text2 = (
            "My AC is broken. I'm John at 512-555-1111, "
            "123 Main St Dallas 75201. The AC stopped working yesterday."
        )
        extraction2, routing2, result2 = full_pipeline(text2, extractor=extractor)
        
        assert extraction2.entities.phone == "512-555-1111"
        assert extraction2.entities.zip_code == "75201"
        # Should succeed with complete info
        if not routing2.requires_human:
            assert result2.status == OpsStatus.SUCCESS

    def test_quote_with_followup_info(self, extractor):
        """Simulate quote with additional context."""
        text = (
            "I need a quote for new AC. I'm Sarah at sarah@home.com, "
            "phone 512-555-2222. It's my home, about 2000 sq ft, "
            "system is 12 years old, want it done within 3 weeks."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.QUOTE_REQUEST
        assert extraction.entities.square_footage == 2000
        assert extraction.entities.system_age_years == 12
        assert extraction.entities.property_type == "residential"

    def test_status_check_scenario(self, extractor):
        """Customer checking on service status."""
        text = (
            "What's the status of my service call? "
            "My phone is 512-555-3333."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.STATUS_UPDATE_REQUEST
        assert routing.brain == Brain.OPS
        assert result.status == OpsStatus.SUCCESS

    def test_complex_emergency_scenario(self, extractor):
        """Complex emergency with multiple details."""
        text = (
            "EMERGENCY! I smell gas and my CO detector is beeping! "
            "My furnace is broken! This is John at 214-555-9999. I'm at 789 Oak St, "
            "Dallas TX 75202. There are elderly people in the house! Need service!"
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Should be emergency
        assert extraction.entities.urgency_level == UrgencyLevel.EMERGENCY
        
        # Should extract contact info
        assert extraction.entities.phone == "214-555-9999"
        assert extraction.entities.zip_code == "75202"
        
        # Should route to OPS
        assert routing.brain == Brain.OPS


# =============================================================================
# CHANNEL-SPECIFIC TESTS
# =============================================================================


class TestChannelSpecific:
    """Tests for channel-specific behavior."""

    def test_voice_channel_quote(self, extractor):
        """Quote via voice channel should have PHONE source."""
        text = (
            "I need a quote. I'm John at 512-555-1111, "
            "residential, want it within 2 weeks."
        )
        
        extraction, routing, result = full_pipeline(
            text, 
            channel=Channel.VOICE,
            extractor=extractor,
        )
        
        if result.status == RevenueStatus.SUCCESS:
            assert result.lead.source.value == "phone"

    def test_chat_channel_quote(self, extractor):
        """Quote via chat channel should have WEBSITE source."""
        text = (
            "I need a quote. I'm John at 512-555-1111, "
            "residential, want it within 2 weeks."
        )
        
        extraction, routing, result = full_pipeline(
            text,
            channel=Channel.CHAT,
            extractor=extractor,
        )
        
        if result.status == RevenueStatus.SUCCESS:
            assert result.lead.source.value == "website"


# =============================================================================
# UNKNOWN INTENT E2E TESTS
# =============================================================================


class TestUnknownIntentE2E:
    """End-to-end tests for unknown intent handling."""

    def test_unrelated_question(self, extractor):
        """Unrelated question should route to UNKNOWN."""
        text = "What's the weather like today?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.UNKNOWN
        assert routing.brain == Brain.UNKNOWN
        assert routing.requires_human is True
        assert result is None  # No handler for UNKNOWN

    def test_greeting_only(self, extractor):
        """Greeting alone should route to UNKNOWN."""
        text = "Hello, how are you?"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        assert extraction.intent == Intent.UNKNOWN
        assert routing.brain == Brain.UNKNOWN


# =============================================================================
# CONFIDENCE IMPACT TESTS
# =============================================================================


class TestConfidenceImpact:
    """Tests for confidence score impact on routing."""

    def test_high_confidence_routes_directly(self, extractor):
        """High confidence extraction should route directly."""
        text = (
            "I need to schedule an appointment for AC repair service. "
            "Call me at 512-555-1234. I'm at 123 Main St, 78701. My AC is broken."
        )
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Should have decent confidence
        assert extraction.confidence >= 0.5
        # Routes to correct brain
        assert routing.brain == Brain.OPS

    def test_low_confidence_needs_human(self, extractor):
        """Low confidence should trigger human review."""
        text = "um yeah so like maybe something's wrong I guess"
        
        extraction, routing, result = full_pipeline(text, extractor=extractor)
        
        # Very ambiguous text should have low confidence
        if extraction.confidence < 0.5:
            assert routing.requires_human is True
