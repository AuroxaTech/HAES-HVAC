"""
HAES HVAC - PEOPLE Brain Payroll Tests

Tests for payroll and commission rules.
"""

import pytest
from datetime import datetime

from src.brains.people.payroll_rules import (
    calculate_commission,
    get_commission_rate,
    get_payroll_summary,
)


class TestCommissionRates:
    """Tests for commission rate rules."""

    def test_repair_commission_rate(self):
        """Repairs should have 15% commission."""
        assert get_commission_rate("repair") == 15.0

    def test_install_commission_rate(self):
        """Installs should have 5% commission."""
        assert get_commission_rate("install") == 5.0

    def test_default_commission_rate(self):
        """Unknown types default to repair rate."""
        assert get_commission_rate("unknown") == 15.0


class TestCommissionCalculation:
    """Tests for commission calculations."""

    def test_repair_commission(self):
        """Should calculate repair commission correctly."""
        result = calculate_commission(
            employee_id="tech1",
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 15),
            repair_invoices=[
                {"amount": 1000, "collected": True},
                {"amount": 500, "collected": True},
            ],
            install_invoices=[],
        )
        assert result.repair_sales == 1500
        assert result.repair_commission == 225.0  # 15% of 1500
        assert result.install_commission == 0.0
        assert result.total_commission == 225.0

    def test_install_commission(self):
        """Should calculate install commission correctly."""
        result = calculate_commission(
            employee_id="tech1",
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 15),
            repair_invoices=[],
            install_invoices=[
                {"amount": 10000, "collected": True},
            ],
        )
        assert result.install_sales == 10000
        assert result.install_commission == 500.0  # 5% of 10000
        assert result.total_commission == 500.0

    def test_mixed_commission(self):
        """Should handle both repair and install."""
        result = calculate_commission(
            employee_id="tech1",
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 15),
            repair_invoices=[{"amount": 1000, "collected": True}],
            install_invoices=[{"amount": 5000, "collected": True}],
        )
        assert result.repair_commission == 150.0  # 15% of 1000
        assert result.install_commission == 250.0  # 5% of 5000
        assert result.total_commission == 400.0

    def test_collection_verification_flag(self):
        """Should flag when collection verification needed."""
        result = calculate_commission(
            employee_id="tech1",
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 15),
            repair_invoices=[
                {"amount": 1000, "collected": True},
                {"amount": 500, "collected": False},  # Not collected
            ],
            install_invoices=[],
        )
        assert result.requires_collection_verification is True
        assert result.commission_eligible > result.commission_payable


class TestPayrollSummary:
    """Tests for payroll configuration."""

    def test_pay_period_biweekly(self):
        """Pay period should be biweekly."""
        summary = get_payroll_summary()
        assert summary["pay_period"] == "biweekly"

    def test_commission_rules_present(self):
        """Commission rules should be defined."""
        summary = get_payroll_summary()
        assert len(summary["commission_rules"]) >= 2

