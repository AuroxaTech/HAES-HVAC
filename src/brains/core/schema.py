"""
HAES HVAC - CORE Brain Schema

Pydantic models for CORE brain operations (pricing, approvals, compliance).
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CoreStatus(str, Enum):
    """Status of a CORE brain operation."""
    SUCCESS = "success"
    NEEDS_HUMAN = "needs_human"
    UNSUPPORTED_INTENT = "unsupported_intent"
    CAPABILITY_MISSING = "capability_missing"
    ERROR = "error"


class PricingTier(str, Enum):
    """Customer pricing tiers from RDD."""
    DEFAULT_PM = "default_pm"  # Property Management / National Accounts / Portals
    RETAIL = "retail"         # Residential homeowners
    COM = "com"               # Commercial
    COM_LESSEN = "com_lessen" # National Commercial / Warranty / Flat-Rate Portal
    COM_HOTELS = "com_hotels" # Hotels & Multifamily


class ApprovalType(str, Enum):
    """Types of approvals."""
    QUOTE = "quote"
    PURCHASE_ORDER = "purchase_order"
    REFUND = "refund"
    DISCOUNT = "discount"
    WRITE_OFF = "write_off"


class ApprovalDecision(BaseModel):
    """Approval decision result."""
    approval_required: bool
    approver: str | None = None
    threshold_rule_id: str | None = None
    reason: str
    amount: float | None = None


class PricingResult(BaseModel):
    """Pricing calculation result."""
    tier: PricingTier
    diagnostic_fee: float
    trip_charge: float
    emergency_premium: float = 0.0
    after_hours_premium: float = 0.0
    weekend_premium: float = 0.0
    total_base_fee: float
    notes: list[str] = Field(default_factory=list)


class PaymentTerms(BaseModel):
    """Payment terms for a customer segment."""
    segment: str
    due_days: int
    late_fee_percent: float
    accepted_methods: list[str] = Field(default_factory=list)


class ComplianceDisclosure(BaseModel):
    """Required compliance disclosures."""
    license_number: str
    regulatory_body: str
    disclosure_text: str
    warranty_terms: str


class InvoicePolicy(BaseModel):
    """Invoice generation policy result."""
    should_generate: bool
    requires_human: bool
    reason: str
    trigger_condition: str | None = None


class CoreResult(BaseModel):
    """Result from CORE brain operations."""
    status: CoreStatus
    message: str
    requires_human: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    pricing: PricingResult | None = None
    approval: ApprovalDecision | None = None
    payment_terms: PaymentTerms | None = None
    compliance: ComplianceDisclosure | None = None
    invoice_policy: InvoicePolicy | None = None
    data: dict[str, Any] = Field(default_factory=dict)

