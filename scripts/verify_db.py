#!/usr/bin/env python3
"""
HAES HVAC - Database Verification Script

Verifies database connectivity and table existence.

Usage:
    uv run python scripts/verify_db.py
"""

import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.engine import get_engine
from src.db.models import AuditLog


def main() -> int:
    """Run database verification checks."""
    print("=" * 60)
    print("HAES HVAC - Database Verification")
    print("=" * 60)

    settings = get_settings()
    print(f"\nEnvironment: {settings.ENVIRONMENT}")
    print(f"Database URL: {settings.DATABASE_URL[:50]}...")

    # Test 1: Basic connectivity
    print("\n[1/3] Testing database connectivity...")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("  ✓ SELECT 1 successful")
            else:
                print("  ✗ SELECT 1 returned unexpected result")
                return 1
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return 1

    # Test 2: Check required tables exist
    print("\n[2/3] Checking required tables...")
    required_tables = ["idempotency_keys", "audit_log", "jobs", "report_runs", "report_deliveries"]
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        all_present = True
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✓ Table '{table}' exists")
            else:
                print(f"  ✗ Table '{table}' NOT FOUND")
                all_present = False
        if not all_present:
            print("\n  Run migrations: uv run alembic upgrade head")
            return 1
    except Exception as e:
        print(f"  ✗ Table check failed: {e}")
        return 1

    # Test 3: Insert and read from audit_log
    print("\n[3/3] Testing audit_log insert/read...")
    try:
        from src.db.session import get_session_factory

        session_factory = get_session_factory()
        session: Session = session_factory()
        try:
            # Insert test record
            test_log = AuditLog(
                request_id="verify_db_test",
                channel="system",
                actor="verify_db.py",
                status="received",
            )
            session.add(test_log)
            session.commit()
            test_id = test_log.id
            print(f"  ✓ Inserted audit_log record (id={test_id})")

            # Read it back
            fetched = session.query(AuditLog).filter_by(id=test_id).first()
            if fetched and fetched.request_id == "verify_db_test":
                print(f"  ✓ Read back audit_log record successfully")
            else:
                print("  ✗ Failed to read back inserted record")
                return 1

            # Clean up test record
            session.delete(fetched)
            session.commit()
            print("  ✓ Cleaned up test record")

        finally:
            session.close()
    except Exception as e:
        print(f"  ✗ Insert/read test failed: {e}")
        return 1

    print("\n" + "=" * 60)
    print("PASS - All database checks completed successfully")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

