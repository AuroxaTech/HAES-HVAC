"""
HAES HVAC - CORE Brain Pricing Catalog

Literal pricing tables from RDD Section 3.
No hidden calculations - all values explicit.
"""

from dataclasses import dataclass
from src.brains.core.schema import PricingTier


@dataclass
class TierPricing:
    """Pricing structure for a tier."""
    tier: PricingTier
    diagnostic_fee: float
    trip_charge: float
    emergency_premium: float      # Added to diagnostic
    after_hours_premium: float    # Added to diagnostic (after 6pm)
    weekend_premium: float        # Added to diagnostic (Sat/Sun)


# Pricing catalog from RDD Section 3
# Values are explicit from the document
PRICING_CATALOG: dict[PricingTier, TierPricing] = {
    PricingTier.DEFAULT_PM: TierPricing(
        tier=PricingTier.DEFAULT_PM,
        diagnostic_fee=89.0,
        trip_charge=0.0,
        emergency_premium=50.0,
        after_hours_premium=35.0,
        weekend_premium=35.0,
    ),
    PricingTier.RETAIL: TierPricing(
        tier=PricingTier.RETAIL,
        diagnostic_fee=129.0,
        trip_charge=0.0,
        emergency_premium=75.0,
        after_hours_premium=50.0,
        weekend_premium=50.0,
    ),
    PricingTier.COM: TierPricing(
        tier=PricingTier.COM,
        diagnostic_fee=149.0,
        trip_charge=0.0,
        emergency_premium=100.0,
        after_hours_premium=75.0,
        weekend_premium=75.0,
    ),
    PricingTier.COM_LESSEN: TierPricing(
        tier=PricingTier.COM_LESSEN,
        diagnostic_fee=99.0,
        trip_charge=0.0,
        emergency_premium=50.0,
        after_hours_premium=35.0,
        weekend_premium=35.0,
    ),
    PricingTier.COM_HOTELS: TierPricing(
        tier=PricingTier.COM_HOTELS,
        diagnostic_fee=119.0,
        trip_charge=0.0,
        emergency_premium=75.0,
        after_hours_premium=50.0,
        weekend_premium=50.0,
    ),
}


def get_tier_pricing(tier: PricingTier) -> TierPricing:
    """Get pricing for a specific tier."""
    return PRICING_CATALOG[tier]


def get_default_tier() -> PricingTier:
    """Get the default pricing tier (Retail for unknown customers)."""
    return PricingTier.RETAIL


# Install pricing ranges from RDD (for quotes)
INSTALL_PRICING_RANGES = {
    "residential_ac_replacement": {
        "min": 4500,
        "max": 12000,
        "unit": "per_unit",
        "notes": "Varies by tonnage, SEER rating, and complexity",
    },
    "residential_furnace_replacement": {
        "min": 3000,
        "max": 8000,
        "unit": "per_unit",
        "notes": "Varies by BTU rating and efficiency",
    },
    "residential_full_system": {
        "min": 8000,
        "max": 20000,
        "unit": "per_system",
        "notes": "AC + Furnace + Ductwork modifications",
    },
    "commercial_rooftop": {
        "min": 8000,
        "max": 50000,
        "unit": "per_unit",
        "notes": "Varies significantly by tonnage and configuration",
    },
}


# Maintenance plan pricing from RDD
MAINTENANCE_PLANS = {
    "residential_basic": {
        "name": "Residential Basic PM",
        "annual_fee": 199,
        "visits_per_year": 2,
        "includes": ["AC tune-up", "Heating tune-up", "Filter check"],
    },
    "residential_premium": {
        "name": "Residential Premium PM",
        "annual_fee": 349,
        "visits_per_year": 2,
        "includes": [
            "AC tune-up",
            "Heating tune-up",
            "Priority scheduling",
            "15% repair discount",
            "No diagnostic fee",
        ],
    },
    "commercial_basic": {
        "name": "Commercial Basic PM",
        "annual_fee": 399,
        "visits_per_year": 4,
        "includes": ["Quarterly inspections", "Filter changes"],
    },
}

