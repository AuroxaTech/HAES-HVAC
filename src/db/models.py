"""
HAES HVAC Database Models

SQLAlchemy ORM models for the foundational tables:
- idempotency_keys: Request deduplication
- audit_log: Action audit trail
- jobs: Background job queue
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# =============================================================================
# Idempotency Keys Table
# =============================================================================


class IdempotencyKey(Base):
    """
    Idempotency keys for request deduplication.

    Ensures that repeated requests with the same key return
    the same result without re-executing the operation.
    """

    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="in_progress"
    )  # in_progress, completed, failed
    response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_idempotency_keys_scope_key", "scope", "key", unique=True),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
    )


# =============================================================================
# Audit Log Table
# =============================================================================


class AuditLog(Base):
    """
    Audit log for tracking all system actions.

    Records every significant action including HAEL commands,
    brain operations, and Odoo interactions.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="system"
    )  # voice, chat, system
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    command_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    odoo_result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="received"
    )  # received, processed, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_request_id", "request_id"),
        Index("ix_audit_log_channel", "channel"),
        Index("ix_audit_log_intent", "intent"),
        Index("ix_audit_log_status", "status"),
    )


# =============================================================================
# Background Jobs Table
# =============================================================================


class Job(Base):
    """
    Background job queue.

    Postgres-backed job queue for async task processing
    with retry support.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )  # queued, running, succeeded, failed
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_jobs_status_run_at", "status", "run_at"),
        Index("ix_jobs_type", "type"),
        Index("ix_jobs_correlation_id", "correlation_id"),
    )


# =============================================================================
# Report Tables (Module 9)
# =============================================================================


class ReportRun(Base):
    """
    Report run artifacts.

    Stores generated report data for each scheduled or on-demand run.
    """

    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # daily, weekly, monthly, quarterly, annual
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="generated"
    )  # generated, delivered, partial, failed
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_report_runs_type_period", "report_type", "period_start"),
        Index("ix_report_runs_created_at", "created_at"),
    )


class ReportDelivery(Base):
    """
    Report delivery tracking.

    Records each delivery attempt for a report run.
    """

    __tablename__ = "report_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("report_runs.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email, sms, odoo
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # sent, failed, skipped_not_configured
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_report_deliveries_run_channel", "report_run_id", "channel"),)

