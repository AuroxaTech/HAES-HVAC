"""
HAES HVAC - Database Smoke Tests

Basic database connectivity and schema tests.
Skipped if DATABASE_URL is not properly configured.
"""

import os
import pytest
from sqlalchemy import inspect, text


# Skip all tests in this module if DATABASE_URL is not set or is default
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or "localhost" not in os.environ.get("DATABASE_URL", ""),
    reason="DATABASE_URL not configured for testing"
)


class TestDatabaseConnectivity:
    """Tests for database connectivity."""

    def test_can_connect_to_database(self, db_session):
        """Should be able to connect to the database."""
        result = db_session.execute(text("SELECT 1"))
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1

    def test_can_get_current_timestamp(self, db_session):
        """Should be able to get current timestamp from database."""
        result = db_session.execute(text("SELECT NOW()"))
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None


class TestDatabaseSchema:
    """Tests for database schema existence."""

    def test_idempotency_keys_table_exists(self, db_session):
        """idempotency_keys table should exist."""
        inspector = inspect(db_session.get_bind())
        tables = inspector.get_table_names()
        assert "idempotency_keys" in tables

    def test_audit_log_table_exists(self, db_session):
        """audit_log table should exist."""
        inspector = inspect(db_session.get_bind())
        tables = inspector.get_table_names()
        assert "audit_log" in tables

    def test_jobs_table_exists(self, db_session):
        """jobs table should exist."""
        inspector = inspect(db_session.get_bind())
        tables = inspector.get_table_names()
        assert "jobs" in tables

    def test_report_runs_table_exists(self, db_session):
        """report_runs table should exist."""
        inspector = inspect(db_session.get_bind())
        tables = inspector.get_table_names()
        assert "report_runs" in tables

    def test_report_deliveries_table_exists(self, db_session):
        """report_deliveries table should exist."""
        inspector = inspect(db_session.get_bind())
        tables = inspector.get_table_names()
        assert "report_deliveries" in tables


class TestAuditLogOperations:
    """Tests for audit_log table operations."""

    def test_can_insert_audit_log(self, db_session):
        """Should be able to insert into audit_log."""
        from src.db.models import AuditLog

        log = AuditLog(
            request_id="test-request-123",
            channel="system",
            actor="test_db_smoke.py",
            status="received",
        )
        db_session.add(log)
        db_session.flush()
        assert log.id is not None

    def test_can_read_audit_log(self, db_session):
        """Should be able to read from audit_log."""
        from src.db.models import AuditLog

        # Insert
        log = AuditLog(
            request_id="test-request-456",
            channel="system",
            actor="test_db_smoke.py",
            status="received",
        )
        db_session.add(log)
        db_session.flush()

        # Read back
        fetched = db_session.query(AuditLog).filter_by(id=log.id).first()
        assert fetched is not None
        assert fetched.request_id == "test-request-456"
        assert fetched.channel == "system"

