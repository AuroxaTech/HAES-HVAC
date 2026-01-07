"""
HAES HVAC - CORE Brain Approval Tests

Tests for approval threshold rules.
"""

import pytest

from src.brains.core.approval_rules import get_approval_decision, ApprovalType


class TestQuoteApprovals:
    """Tests for quote approval thresholds."""

    def test_quote_under_20k_auto(self):
        """Quotes under $20k should be auto-approved."""
        result = get_approval_decision(ApprovalType.QUOTE, 15000)
        assert result.approval_required is False

    def test_quote_20k_to_1m_linda(self):
        """Quotes $20k-$1M require Linda's approval."""
        result = get_approval_decision(ApprovalType.QUOTE, 50000)
        assert result.approval_required is True
        assert result.approver == "Linda"

    def test_quote_over_1m_junior(self):
        """Quotes over $1M require Junior's approval."""
        result = get_approval_decision(ApprovalType.QUOTE, 1500000)
        assert result.approval_required is True
        assert result.approver == "Junior"


class TestPOApprovals:
    """Tests for purchase order approval thresholds."""

    def test_po_under_100_auto(self):
        """POs under $100 should be auto-approved."""
        result = get_approval_decision(ApprovalType.PURCHASE_ORDER, 50)
        assert result.approval_required is False

    def test_po_100_to_500_linda(self):
        """POs $100-$500 require Linda's approval."""
        result = get_approval_decision(ApprovalType.PURCHASE_ORDER, 250)
        assert result.approval_required is True
        assert result.approver == "Linda"

    def test_po_over_500_junior(self):
        """POs over $500 require Junior's approval."""
        result = get_approval_decision(ApprovalType.PURCHASE_ORDER, 750)
        assert result.approval_required is True
        assert result.approver == "Junior"

    def test_capital_equipment_override(self):
        """Capital equipment over $350 requires Junior."""
        result = get_approval_decision(
            ApprovalType.PURCHASE_ORDER, 400, is_capital_equipment=True
        )
        assert result.approval_required is True
        assert result.approver == "Junior"


class TestRefundApprovals:
    """Tests for refund approval thresholds."""

    def test_refund_1_to_99_anna(self):
        """Refunds $1-$99 require Anna's approval."""
        result = get_approval_decision(ApprovalType.REFUND, 50)
        assert result.approval_required is True
        assert result.approver == "Anna"

    def test_refund_over_100_linda(self):
        """Refunds over $100 require Linda's approval."""
        result = get_approval_decision(ApprovalType.REFUND, 150)
        assert result.approval_required is True
        assert result.approver == "Linda"


class TestDiscountApprovals:
    """Tests for discount approval thresholds."""

    def test_discount_up_to_5_auto(self):
        """Discounts up to 5% should be auto-approved."""
        result = get_approval_decision(ApprovalType.DISCOUNT, 5)
        assert result.approval_required is False

    def test_discount_6_to_10_linda(self):
        """Discounts 6-10% require Linda's approval."""
        result = get_approval_decision(ApprovalType.DISCOUNT, 8)
        assert result.approval_required is True
        assert result.approver == "Linda"

    def test_discount_over_10_junior(self):
        """Discounts over 10% require Junior's approval."""
        result = get_approval_decision(ApprovalType.DISCOUNT, 15)
        assert result.approval_required is True
        assert result.approver == "Junior"

