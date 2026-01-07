"""Initial schema - idempotency_keys, audit_log, jobs, report tables

Revision ID: 0001
Revises:
Create Date: 2026-01-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # idempotency_keys table
    # ==========================================================================
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("key", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("response_hash", sa.String(64), nullable=True),
        sa.Column("response_json", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_idempotency_keys_scope_key",
        "idempotency_keys",
        ["scope", "key"],
        unique=True,
    )
    op.create_index(
        "ix_idempotency_keys_expires_at",
        "idempotency_keys",
        ["expires_at"],
    )

    # ==========================================================================
    # audit_log table
    # ==========================================================================
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="system"),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("intent", sa.String(100), nullable=True),
        sa.Column("brain", sa.String(50), nullable=True),
        sa.Column("command_json", postgresql.JSONB, nullable=True),
        sa.Column("odoo_result_json", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])
    op.create_index("ix_audit_log_channel", "audit_log", ["channel"])
    op.create_index("ix_audit_log_intent", "audit_log", ["intent"])
    op.create_index("ix_audit_log_status", "audit_log", ["status"])

    # ==========================================================================
    # jobs table
    # ==========================================================================
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("payload_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
    )
    op.create_index("ix_jobs_status_run_at", "jobs", ["status", "run_at"])
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_correlation_id", "jobs", ["correlation_id"])

    # ==========================================================================
    # report_runs table
    # ==========================================================================
    op.create_table(
        "report_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="generated"),
        sa.Column("report_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("summary_text", sa.Text, nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
    )
    op.create_index("ix_report_runs_type_period", "report_runs", ["report_type", "period_start"])
    op.create_index("ix_report_runs_created_at", "report_runs", ["created_at"])

    # ==========================================================================
    # report_deliveries table
    # ==========================================================================
    op.create_table(
        "report_deliveries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "report_run_id",
            sa.Integer,
            sa.ForeignKey("report_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_report_deliveries_run_channel",
        "report_deliveries",
        ["report_run_id", "channel"],
    )


def downgrade() -> None:
    op.drop_table("report_deliveries")
    op.drop_table("report_runs")
    op.drop_table("jobs")
    op.drop_table("audit_log")
    op.drop_table("idempotency_keys")

