"""
HAES HVAC - PEOPLE Brain Schema

Pydantic models for PEOPLE brain operations (HR, onboarding, payroll).
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PeopleStatus(str, Enum):
    """Status of a PEOPLE brain operation."""
    SUCCESS = "success"
    NEEDS_HUMAN = "needs_human"
    UNSUPPORTED_INTENT = "unsupported_intent"
    CAPABILITY_MISSING = "capability_missing"
    ERROR = "error"


class OnboardingCategory(str, Enum):
    """Onboarding checklist categories from RDD."""
    HR_IDENTITY = "hr_identity"
    EMPLOYMENT_AGREEMENTS = "employment_agreements"
    PAYROLL_BANKING = "payroll_banking"
    SYSTEM_ACCESS = "system_access"


class OnboardingItem(BaseModel):
    """Onboarding checklist item."""
    id: str
    category: OnboardingCategory
    name: str
    description: str
    required: bool = True
    completed: bool = False
    completed_at: datetime | None = None


class TrainingTopic(BaseModel):
    """Training topic."""
    id: str
    name: str
    description: str
    duration_hours: float
    required: bool = True
    certification_required: bool = False


class TrainingProgram(BaseModel):
    """Training program structure."""
    onboarding_days: int = 14
    ramp_days: list[int] = Field(default_factory=lambda: [30, 60, 90])
    topics: list[TrainingTopic] = Field(default_factory=list)
    friday_meeting_recurring: bool = True


class PayrollPeriod(str, Enum):
    """Payroll period from RDD."""
    BIWEEKLY = "biweekly"


class CommissionRule(BaseModel):
    """Commission calculation rule."""
    type: str  # repairs, installs
    rate_percent: float
    paid_on: str  # invoice, collection, both


class PayrollCalculation(BaseModel):
    """Payroll calculation result."""
    employee_id: str
    period_start: datetime
    period_end: datetime
    repair_sales: float = 0.0
    install_sales: float = 0.0
    repair_commission: float = 0.0
    install_commission: float = 0.0
    total_commission: float = 0.0
    commission_eligible: float = 0.0
    commission_payable: float = 0.0
    requires_collection_verification: bool = False


class HiringRequirements(BaseModel):
    """Hiring requirements from RDD."""
    required_documents: list[str] = Field(default_factory=list)
    background_checks: list[str] = Field(default_factory=list)
    approvers: list[str] = Field(default_factory=list)
    interview_stages: list[str] = Field(default_factory=list)


class PeopleResult(BaseModel):
    """Result from PEOPLE brain operations."""
    status: PeopleStatus
    message: str
    requires_human: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    hiring_requirements: HiringRequirements | None = None
    onboarding_items: list[OnboardingItem] = Field(default_factory=list)
    training_program: TrainingProgram | None = None
    payroll: PayrollCalculation | None = None
    data: dict[str, Any] = Field(default_factory=dict)

