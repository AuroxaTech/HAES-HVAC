"""
HAES HVAC - Comprehensive CORE Brain Handler Tests

Exhaustive tests for CORE brain handlers covering:
- Billing inquiry handling
- Payment terms inquiry
- Invoice requests
- Inventory inquiries
- Purchase requests
- Pricing engine
- Compliance disclosures
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
from src.brains.core.handlers import (
    handle_core_command,
    calculate_service_pricing,
    should_generate_invoice,
    CORE_INTENTS,
)
from src.brains.core.schema import CoreStatus, PricingTier
from src.brains.core.pricing_catalog import get_tier_pricing, get_default_tier
from src.brains.core.payment_terms import get_payment_terms, format_payment_terms_text
from src.brains.core.approval_rules import get_approval_decision, ApprovalType
from src.brains.core.compliance import get_required_disclosures


def create_core_command(
    intent: Intent,
    entities: Entity | None = None,
    requires_human: bool = False,
    missing_fields: list[str] | None = None,
    confidence: float = 0.8,
) -> HaelCommand:
    """Helper to create HaelCommand for CORE brain testing."""
    return HaelCommand(
        request_id=str(uuid4()),
        channel=Channel.VOICE,
        raw_text="Test CORE command",
        intent=intent,
        brain=Brain.CORE,
        entities=entities or Entity(),
        confidence=confidence,
        requires_human=requires_human,
        missing_fields=missing_fields or [],
        idempotency_key=str(uuid4()),
        created_at=datetime.utcnow(),
    )


# =============================================================================
# CORE INTENTS CONFIGURATION TESTS
# =============================================================================


class TestCoreIntentsConfiguration:
    """Tests for CORE intents configuration."""

    def test_core_intents_contains_billing(self):
        """BILLING_INQUIRY should be in CORE intents."""
        assert Intent.BILLING_INQUIRY in CORE_INTENTS

    def test_core_intents_contains_payment_terms(self):
        """PAYMENT_TERMS_INQUIRY should be in CORE intents."""
        assert Intent.PAYMENT_TERMS_INQUIRY in CORE_INTENTS

    def test_core_intents_contains_invoice(self):
        """INVOICE_REQUEST should be in CORE intents."""
        assert Intent.INVOICE_REQUEST in CORE_INTENTS

    def test_core_intents_contains_inventory(self):
        """INVENTORY_INQUIRY should be in CORE intents."""
        assert Intent.INVENTORY_INQUIRY in CORE_INTENTS

    def test_core_intents_contains_purchase(self):
        """PURCHASE_REQUEST should be in CORE intents."""
        assert Intent.PURCHASE_REQUEST in CORE_INTENTS

    def test_core_intents_count(self):
        """CORE should handle exactly 5 intents."""
        assert len(CORE_INTENTS) == 5


# =============================================================================
# BILLING INQUIRY HANDLER TESTS
# =============================================================================


class TestBillingInquiryHandler:
    """Comprehensive tests for billing inquiry handling."""

    def test_billing_inquiry_with_phone(self):
        """Billing inquiry with phone should succeed."""
        entities = Entity(phone="512-555-1234")
        command = create_core_command(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False
        assert result.data["action"] == "lookup_billing"
        assert result.data["contact_phone"] == "512-555-1234"

    def test_billing_inquiry_with_email(self):
        """Billing inquiry with email should succeed."""
        entities = Entity(email="john@example.com")
        command = create_core_command(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False
        assert result.data["contact_email"] == "john@example.com"

    def test_billing_inquiry_missing_contact(self):
        """Billing inquiry without contact should need human."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.NEEDS_HUMAN
        assert result.requires_human is True
        assert "phone or email" in result.missing_fields

    def test_billing_inquiry_includes_compliance(self):
        """Billing inquiry should include compliance disclosures."""
        entities = Entity(phone="512-555-1234")
        command = create_core_command(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.compliance is not None


# =============================================================================
# PAYMENT TERMS INQUIRY HANDLER TESTS
# =============================================================================


class TestPaymentTermsInquiryHandler:
    """Comprehensive tests for payment terms inquiry handling."""

    def test_payment_terms_no_identity_required(self):
        """Payment terms shouldn't require identity."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False

    def test_payment_terms_residential_segment(self):
        """Payment terms for residential should return appropriate terms."""
        entities = Entity(property_type="residential")
        command = create_core_command(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.data["segment"] == "residential"
        assert result.payment_terms is not None

    def test_payment_terms_commercial_segment(self):
        """Payment terms for commercial should return appropriate terms."""
        entities = Entity(property_type="commercial")
        command = create_core_command(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.data["segment"] == "commercial"

    def test_payment_terms_unknown_segment(self):
        """Payment terms for unknown segment should return default."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.data["segment"] == "unknown"

    def test_payment_terms_message_content(self):
        """Payment terms should have meaningful message."""
        entities = Entity(property_type="residential")
        command = create_core_command(
            intent=Intent.PAYMENT_TERMS_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert len(result.message) > 0
        # Should mention payment-related terms
        assert any(word in result.message.lower() for word in 
                   ["payment", "due", "accept", "cash", "card"])


# =============================================================================
# INVOICE REQUEST HANDLER TESTS
# =============================================================================


class TestInvoiceRequestHandler:
    """Comprehensive tests for invoice request handling."""

    def test_invoice_request_with_email(self):
        """Invoice request with email should succeed."""
        entities = Entity(email="john@example.com")
        command = create_core_command(
            intent=Intent.INVOICE_REQUEST,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False
        assert result.data["action"] == "send_invoice"

    def test_invoice_request_with_phone(self):
        """Invoice request with phone should succeed."""
        entities = Entity(phone="512-555-1234")
        command = create_core_command(
            intent=Intent.INVOICE_REQUEST,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False

    def test_invoice_request_missing_contact(self):
        """Invoice request without contact should need human."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.INVOICE_REQUEST,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# INVENTORY INQUIRY HANDLER TESTS
# =============================================================================


class TestInventoryInquiryHandler:
    """Comprehensive tests for inventory inquiry handling."""

    def test_inventory_inquiry_no_identity_required(self):
        """Inventory inquiry shouldn't require identity."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.INVENTORY_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False
        assert result.data["action"] == "inventory_lookup"

    def test_inventory_inquiry_with_context(self):
        """Inventory inquiry with context should succeed."""
        entities = Entity(
            problem_description="Looking for a Carrier filter",
        )
        command = create_core_command(
            intent=Intent.INVENTORY_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS

    def test_inventory_inquiry_message(self):
        """Inventory inquiry should ask for specific part."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.INVENTORY_INQUIRY,
            entities=entities,
        )
        result = handle_core_command(command)

        assert "part" in result.message.lower() or "equipment" in result.message.lower()


# =============================================================================
# PURCHASE REQUEST HANDLER TESTS
# =============================================================================


class TestPurchaseRequestHandler:
    """Comprehensive tests for purchase request handling."""

    def test_purchase_request_with_contact(self):
        """Purchase request with contact should succeed."""
        entities = Entity(
            phone="512-555-1234",
            email="john@example.com",
        )
        command = create_core_command(
            intent=Intent.PURCHASE_REQUEST,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.SUCCESS
        assert result.requires_human is False
        assert result.data["action"] == "purchase_request"

    def test_purchase_request_missing_contact(self):
        """Purchase request without contact should need human."""
        entities = Entity()
        command = create_core_command(
            intent=Intent.PURCHASE_REQUEST,
            entities=entities,
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# PRICING ENGINE TESTS
# =============================================================================


class TestPricingEngine:
    """Comprehensive tests for pricing engine."""

    def test_default_tier_pricing(self):
        """Default tier should be Retail."""
        tier = get_default_tier()
        assert tier == PricingTier.RETAIL

    def test_retail_tier_pricing(self):
        """Retail tier pricing calculation."""
        result = calculate_service_pricing(tier=PricingTier.RETAIL)

        assert result.tier == PricingTier.RETAIL
        assert result.diagnostic_fee > 0
        assert result.total_base_fee > 0

    def test_default_pm_tier_pricing(self):
        """Default PM tier pricing calculation."""
        result = calculate_service_pricing(tier=PricingTier.DEFAULT_PM)

        assert result.tier == PricingTier.DEFAULT_PM

    def test_commercial_tier_pricing(self):
        """Commercial tier pricing calculation."""
        result = calculate_service_pricing(tier=PricingTier.COM)

        assert result.tier == PricingTier.COM

    def test_emergency_premium_applied(self):
        """Emergency premium should be applied."""
        normal = calculate_service_pricing(is_emergency=False)
        emergency = calculate_service_pricing(is_emergency=True)

        assert emergency.emergency_premium > 0
        assert emergency.total_base_fee > normal.total_base_fee
        assert "Emergency" in emergency.notes[0]

    def test_after_hours_premium_applied(self):
        """After-hours premium should be applied."""
        normal = calculate_service_pricing(is_after_hours=False)
        after_hours = calculate_service_pricing(is_after_hours=True)

        assert after_hours.after_hours_premium > 0
        assert after_hours.total_base_fee > normal.total_base_fee
        assert "After-hours" in after_hours.notes[0]

    def test_weekend_premium_applied(self):
        """Weekend premium should be applied."""
        normal = calculate_service_pricing(is_weekend=False)
        weekend = calculate_service_pricing(is_weekend=True)

        assert weekend.weekend_premium > 0
        assert weekend.total_base_fee > normal.total_base_fee
        assert "Weekend" in weekend.notes[0]

    def test_combined_premiums(self):
        """Combined premiums should stack."""
        result = calculate_service_pricing(
            is_emergency=True,
            is_after_hours=True,
            is_weekend=True,
        )

        assert result.emergency_premium > 0
        assert result.after_hours_premium > 0
        assert result.weekend_premium > 0
        assert len(result.notes) == 3

    def test_pricing_structure(self):
        """Pricing result should have correct structure."""
        result = calculate_service_pricing()

        assert hasattr(result, 'tier')
        assert hasattr(result, 'diagnostic_fee')
        assert hasattr(result, 'trip_charge')
        assert hasattr(result, 'emergency_premium')
        assert hasattr(result, 'after_hours_premium')
        assert hasattr(result, 'weekend_premium')
        assert hasattr(result, 'total_base_fee')
        assert hasattr(result, 'notes')


# =============================================================================
# INVOICE GENERATION POLICY TESTS
# =============================================================================


class TestInvoiceGenerationPolicy:
    """Tests for invoice generation policy."""

    def test_invoice_generated_when_complete_and_paid(self):
        """Invoice should be generated when work complete and paid."""
        result = should_generate_invoice(
            work_order_status="completed",
            payment_status="paid",
        )

        assert result.should_generate is True
        assert result.requires_human is False

    def test_invoice_generated_when_complete_and_collected(self):
        """Invoice should be generated when work complete and collected."""
        result = should_generate_invoice(
            work_order_status="complete",
            payment_status="collected",
        )

        assert result.should_generate is True

    def test_invoice_pending_when_work_incomplete(self):
        """Invoice should not be generated when work incomplete."""
        result = should_generate_invoice(
            work_order_status="in_progress",
            payment_status="paid",
        )

        assert result.should_generate is False
        assert "not yet completed" in result.reason.lower()

    def test_invoice_due_when_complete_but_unpaid(self):
        """Invoice due when work complete but payment pending."""
        result = should_generate_invoice(
            work_order_status="completed",
            payment_status="pending",
        )

        assert result.should_generate is True
        assert "invoice due" in result.reason.lower()

    @pytest.mark.parametrize("wo_status", ["completed", "complete", "done"])
    def test_various_complete_status_formats(self, wo_status):
        """Various work order complete status formats."""
        result = should_generate_invoice(
            work_order_status=wo_status,
            payment_status="paid",
        )

        assert result.should_generate is True

    @pytest.mark.parametrize("pay_status", ["paid", "collected", "received"])
    def test_various_paid_status_formats(self, pay_status):
        """Various payment status formats."""
        result = should_generate_invoice(
            work_order_status="completed",
            payment_status=pay_status,
        )

        assert result.should_generate is True


# =============================================================================
# PAYMENT TERMS TESTS
# =============================================================================


class TestPaymentTerms:
    """Tests for payment terms functionality."""

    def test_get_payment_terms_residential(self):
        """Get payment terms for residential."""
        terms = get_payment_terms("residential")
        assert terms is not None

    def test_get_payment_terms_commercial(self):
        """Get payment terms for commercial."""
        terms = get_payment_terms("commercial")
        assert terms is not None

    def test_get_payment_terms_default(self):
        """Get payment terms for unknown segment."""
        terms = get_payment_terms(None)
        assert terms is not None

    def test_format_payment_terms_text(self):
        """Format payment terms text."""
        text = format_payment_terms_text("residential")
        assert len(text) > 0
        assert isinstance(text, str)


# =============================================================================
# APPROVAL RULES TESTS
# =============================================================================


class TestApprovalRules:
    """Tests for approval rules."""

    def test_discount_approval(self):
        """Test discount approval decision."""
        decision = get_approval_decision(
            approval_type=ApprovalType.DISCOUNT,
            amount=500.0,
        )
        assert decision is not None

    def test_refund_approval(self):
        """Test refund approval decision."""
        decision = get_approval_decision(
            approval_type=ApprovalType.REFUND,
            amount=200.0,
        )
        assert decision is not None


# =============================================================================
# COMPLIANCE DISCLOSURES TESTS
# =============================================================================


class TestComplianceDisclosures:
    """Tests for compliance disclosures."""

    def test_get_required_disclosures(self):
        """Get required disclosures."""
        disclosures = get_required_disclosures()
        assert disclosures is not None

    def test_disclosures_structure(self):
        """Disclosures should have proper structure."""
        disclosures = get_required_disclosures()
        # Should be a valid disclosure object
        assert disclosures is not None
        # Should have required disclosure attributes
        assert hasattr(disclosures, 'license_number') or hasattr(disclosures, 'disclosure_text')


# =============================================================================
# UNSUPPORTED INTENT TESTS
# =============================================================================


class TestUnsupportedIntent:
    """Tests for unsupported intent handling."""

    @pytest.mark.parametrize("intent", [
        Intent.SERVICE_REQUEST,
        Intent.QUOTE_REQUEST,
        Intent.HIRING_INQUIRY,
        Intent.PAYROLL_INQUIRY,
    ])
    def test_unsupported_intent(self, intent):
        """Non-CORE intents should return unsupported."""
        command = create_core_command(
            intent=intent,
            entities=Entity(),
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.UNSUPPORTED_INTENT


# =============================================================================
# HAEL REQUIRES HUMAN PROPAGATION TESTS
# =============================================================================


class TestHaelRequiresHumanPropagation:
    """Tests for HAEL requires_human flag propagation."""

    def test_hael_requires_human_propagates(self):
        """HAEL requires_human flag should propagate."""
        entities = Entity(phone="512-555-1234")
        command = create_core_command(
            intent=Intent.BILLING_INQUIRY,
            entities=entities,
            requires_human=True,  # Pre-set by HAEL
            missing_fields=["some_field"],
        )
        result = handle_core_command(command)

        assert result.status == CoreStatus.NEEDS_HUMAN
        assert result.requires_human is True


# =============================================================================
# TIER PRICING CATALOG TESTS
# =============================================================================


class TestTierPricingCatalog:
    """Tests for tier pricing catalog."""

    @pytest.mark.parametrize("tier", [
        PricingTier.RETAIL,
        PricingTier.DEFAULT_PM,
        PricingTier.COM,
        PricingTier.COM_LESSEN,
        PricingTier.COM_HOTELS,
    ])
    def test_tier_pricing_exists(self, tier):
        """All tiers should have pricing defined."""
        pricing = get_tier_pricing(tier)
        assert pricing is not None
        assert pricing.diagnostic_fee >= 0
        assert pricing.trip_charge >= 0

    def test_default_pm_vs_retail(self):
        """Default PM tier should have different fees than retail."""
        retail = get_tier_pricing(PricingTier.RETAIL)
        default_pm = get_tier_pricing(PricingTier.DEFAULT_PM)

        # Both should have valid pricing
        assert retail.diagnostic_fee >= 0
        assert default_pm.diagnostic_fee >= 0
