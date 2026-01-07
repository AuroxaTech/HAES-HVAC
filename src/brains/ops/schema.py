"""
HAES HVAC - OPS Brain Schema

Pydantic models for OPS brain operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OpsStatus(str, Enum):
    """Status of an OPS brain operation."""
    SUCCESS = "success"
    NEEDS_HUMAN = "needs_human"
    UNSUPPORTED_INTENT = "unsupported_intent"
    ERROR = "error"


class WorkOrderStatus(str, Enum):
    """Work order status states."""
    PENDING_SCHEDULE = "pending_schedule"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServicePriority(str, Enum):
    """Service priority levels."""
    EMERGENCY = "emergency"  # Immediate dispatch
    URGENT = "urgent"       # Same day
    HIGH = "high"          # Next available
    NORMAL = "normal"      # Standard scheduling
    LOW = "low"            # Flexible timing


class TechnicianAssignment(BaseModel):
    """Technician assignment details."""
    technician_id: str | None = None
    technician_name: str | None = None
    skill_level: str | None = None
    phone: str | None = None


class ScheduleSlot(BaseModel):
    """Available schedule slot."""
    start_time: datetime
    end_time: datetime
    technician: TechnicianAssignment | None = None
    is_available: bool = True


class WorkOrderData(BaseModel):
    """Work order information."""
    work_order_id: str | None = None
    odoo_record_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    address: str | None = None
    zip_code: str | None = None
    problem_description: str | None = None
    service_type: str | None = None
    priority: ServicePriority = ServicePriority.NORMAL
    status: WorkOrderStatus = WorkOrderStatus.PENDING_SCHEDULE
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    technician: TechnicianAssignment | None = None
    notes: str | None = None
    created_at: datetime | None = None


class OpsResult(BaseModel):
    """Result from OPS brain operations."""
    status: OpsStatus
    message: str
    requires_human: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    work_order: WorkOrderData | None = None
    available_slots: list[ScheduleSlot] = Field(default_factory=list)
    suggested_action: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ServiceRequest(BaseModel):
    """Validated service request input."""
    customer_phone: str | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    address: str | None = None
    zip_code: str | None = None
    problem_description: str
    urgency_level: str
    preferred_times: list[str] = Field(default_factory=list)
    system_type: str | None = None

