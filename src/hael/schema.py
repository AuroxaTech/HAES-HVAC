"""
HAES HVAC - HAEL Command Schema

Pydantic models for the HAEL command envelope, intents, and entities.
These schemas define the contract for all commands flowing through the system.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Channel(str, Enum):
    """Input channel for the command."""
    VOICE = "voice"
    CHAT = "chat"
    SYSTEM = "system"


class Brain(str, Enum):
    """Target brain for command routing."""
    CORE = "core"
    OPS = "ops"
    REVENUE = "revenue"
    PEOPLE = "people"
    UNKNOWN = "unknown"


class Intent(str, Enum):
    """Command intent classification."""
    # OPS-BRAIN intents
    SERVICE_REQUEST = "service_request"
    SCHEDULE_APPOINTMENT = "schedule_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    STATUS_UPDATE_REQUEST = "status_update_request"

    # REVENUE-BRAIN intents
    QUOTE_REQUEST = "quote_request"

    # CORE-BRAIN intents
    BILLING_INQUIRY = "billing_inquiry"
    PAYMENT_TERMS_INQUIRY = "payment_terms_inquiry"
    INVOICE_REQUEST = "invoice_request"
    INVENTORY_INQUIRY = "inventory_inquiry"
    PURCHASE_REQUEST = "purchase_request"

    # PEOPLE-BRAIN intents
    HIRING_INQUIRY = "hiring_inquiry"
    ONBOARDING_INQUIRY = "onboarding_inquiry"
    PAYROLL_INQUIRY = "payroll_inquiry"

    # Unknown/fallback
    UNKNOWN = "unknown"


class UrgencyLevel(str, Enum):
    """Urgency classification for service requests."""
    EMERGENCY = "emergency"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Entity(BaseModel):
    """
    Extracted entities from user input.

    All fields are optional as extraction may be partial.
    Missing required fields will trigger requires_human=true.
    """
    # Identity
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None

    # Location
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    state: str | None = None

    # Service details
    problem_description: str | None = None
    system_type: str | None = None
    urgency_level: UrgencyLevel = UrgencyLevel.UNKNOWN

    # Scheduling
    preferred_time_windows: list[str] = Field(default_factory=list)
    appointment_date: str | None = None

    # Quote/property details
    property_type: str | None = None  # residential, commercial
    square_footage: int | None = None
    system_age_years: int | None = None
    budget_range: str | None = None
    timeline: str | None = None

    # Additional context
    temperature_mentioned: int | None = None  # For emergency qualification


class HaelCommand(BaseModel):
    """
    HAEL Command envelope.

    This is the standardized command object that flows through
    the system after extraction and routing.
    """
    # Identification
    request_id: str = Field(..., description="Unique request identifier")
    channel: Channel = Field(..., description="Input channel")
    raw_text: str = Field(..., description="Original user input")

    # Classification
    intent: Intent = Field(..., description="Classified intent")
    brain: Brain = Field(..., description="Target brain for routing")
    entities: Entity = Field(default_factory=Entity, description="Extracted entities")

    # Quality indicators
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    requires_human: bool = Field(..., description="Whether human intervention is needed")
    missing_fields: list[str] = Field(default_factory=list, description="Required fields that are missing")

    # Deduplication
    idempotency_key: str = Field(..., description="Key for request deduplication")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class HaelExtractionResult(BaseModel):
    """Result from the extraction phase before routing."""
    intent: Intent
    entities: Entity
    confidence: float
    raw_signals: dict[str, Any] = Field(default_factory=dict)


class HaelRoutingResult(BaseModel):
    """Result from the routing phase."""
    brain: Brain
    requires_human: bool
    missing_fields: list[str]
    routing_reason: str

