"""
HAES HVAC - REVENUE Brain Schema

Pydantic models for REVENUE brain operations (leads, quoting, sales).
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RevenueStatus(str, Enum):
    """Status of a REVENUE brain operation."""
    SUCCESS = "success"
    NEEDS_HUMAN = "needs_human"
    UNSUPPORTED_INTENT = "unsupported_intent"
    CAPABILITY_MISSING = "capability_missing"
    ERROR = "error"


class LeadQualification(str, Enum):
    """Lead qualification levels from RDD."""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class LeadSource(str, Enum):
    """Lead sources."""
    WEBSITE = "website"
    PHONE = "phone"
    REFERRAL = "referral"
    GOOGLE = "google"
    SOCIAL = "social"
    OTHER = "other"


class PipelineStage(str, Enum):
    """Pipeline stages from RDD."""
    PENDING_SCHEDULE = "pending_schedule"
    JOB_SCHEDULED = "job_scheduled"
    ON_THE_WAY = "on_the_way"
    ON_SITE = "on_site"
    ON_HOLD = "on_hold"
    PAUSED_RETURN_SAME_DAY = "paused_return_same_day"
    PENDING_QUOTE_APPROVAL = "pending_quote_approval"
    QUOTE_APPROVED_WAITING_PARTS = "quote_approved_waiting_parts"
    QUOTE_APPROVED_HOLD = "quote_approved_hold"
    COMPLETED = "completed"
    WARRANTY_REVIEW = "warranty_review"
    INVOICES_NOT_PAID = "invoices_not_paid"
    CLOSED = "closed"


class LeadData(BaseModel):
    """Lead information."""
    lead_id: str | None = None
    odoo_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    property_type: str | None = None
    property_address: str | None = None
    square_footage: int | None = None
    system_age_years: int | None = None
    budget_range: str | None = None
    timeline: str | None = None
    problem_description: str | None = None
    qualification: LeadQualification = LeadQualification.WARM
    source: LeadSource = LeadSource.PHONE
    stage: PipelineStage = PipelineStage.PENDING_QUOTE_APPROVAL
    assigned_to: str | None = None
    created_at: datetime | None = None


class FollowUpAction(BaseModel):
    """Scheduled follow-up action."""
    action_type: str  # thank_you, reminder, nurture, reactivation
    scheduled_at: datetime
    message_template: str | None = None
    channel: str = "email"  # email, sms, call


class RevenueResult(BaseModel):
    """Result from REVENUE brain operations."""
    status: RevenueStatus
    message: str
    requires_human: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    lead: LeadData | None = None
    qualification: LeadQualification | None = None
    follow_ups: list[FollowUpAction] = Field(default_factory=list)
    assigned_to: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)

