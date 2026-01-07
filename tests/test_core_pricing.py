"""
HAES HVAC - CORE Brain Pricing Tests

Tests for pricing catalog and calculations.
"""

import pytest

from src.brains.core.pricing_catalog import (
    PRICING_CATALOG,
    get_tier_pricing,
    get_default_tier,
)
from src.brains.core.schema import PricingTier
from src.brains.core.handlers import calculate_service_pricing


class TestPricingCatalog:
    """Tests for pricing catalog values."""

    def test_all_tiers_have_pricing(self):
        """All pricing tiers should have defined pricing."""
        for tier in PricingTier:
            assert tier in PRICING_CATALOG

    def test_retail_diagnostic_fee(self):
        """Retail tier should have expected diagnostic fee."""
        pricing = get_tier_pricing(PricingTier.RETAIL)
        assert pricing.diagnostic_fee == 129.0

    def test_default_pm_diagnostic_fee(self):
        """Default PM tier should have expected diagnostic fee."""
        pricing = get_tier_pricing(PricingTier.DEFAULT_PM)
        assert pricing.diagnostic_fee == 89.0

    def test_commercial_diagnostic_fee(self):
        """Commercial tier should have expected diagnostic fee."""
        pricing = get_tier_pricing(PricingTier.COM)
        assert pricing.diagnostic_fee == 149.0

    def test_default_tier_is_retail(self):
        """Default tier should be Retail."""
        assert get_default_tier() == PricingTier.RETAIL


class TestPricingCalculations:
    """Tests for pricing calculations."""

    def test_base_pricing_no_premiums(self):
        """Base pricing without premiums."""
        result = calculate_service_pricing(
            tier=PricingTier.RETAIL,
            is_emergency=False,
            is_after_hours=False,
            is_weekend=False,
        )
        assert result.diagnostic_fee == 129.0
        assert result.emergency_premium == 0.0
        assert result.after_hours_premium == 0.0
        assert result.weekend_premium == 0.0
        assert result.total_base_fee == 129.0

    def test_emergency_premium_applied(self):
        """Emergency premium should be applied."""
        result = calculate_service_pricing(
            tier=PricingTier.RETAIL,
            is_emergency=True,
        )
        assert result.emergency_premium == 75.0
        assert result.total_base_fee == 129.0 + 75.0

    def test_after_hours_premium_applied(self):
        """After-hours premium should be applied."""
        result = calculate_service_pricing(
            tier=PricingTier.RETAIL,
            is_after_hours=True,
        )
        assert result.after_hours_premium == 50.0

    def test_weekend_premium_applied(self):
        """Weekend premium should be applied."""
        result = calculate_service_pricing(
            tier=PricingTier.RETAIL,
            is_weekend=True,
        )
        assert result.weekend_premium == 50.0

    def test_all_premiums_stack(self):
        """All premiums should stack."""
        result = calculate_service_pricing(
            tier=PricingTier.RETAIL,
            is_emergency=True,
            is_after_hours=True,
            is_weekend=True,
        )
        expected = 129.0 + 75.0 + 50.0 + 50.0
        assert result.total_base_fee == expected

