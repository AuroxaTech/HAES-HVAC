#!/usr/bin/env python3
"""
HAES HVAC - Odoo Connection Verification Script

Verifies connectivity to the Odoo 18 Enterprise instance.

Usage:
    # Set environment variables first:
    export ODOO_BASE_URL=https://example.odoo.com
    export ODOO_DB=mydb
    export ODOO_USERNAME=user@example.com
    export ODOO_PASSWORD=api_key_or_password

    uv run python scripts/verify_odoo_connection.py
"""

import asyncio
import sys

# Add project root to path
sys.path.insert(0, ".")

from src.config.settings import get_settings
from src.integrations.odoo import OdooClient


async def main() -> int:
    """Run Odoo connection verification."""
    print("=" * 60)
    print("HAES HVAC - Odoo Connection Verification")
    print("=" * 60)

    settings = get_settings()

    # Check required settings
    print("\n[1/4] Checking environment configuration...")
    missing = []
    if not settings.ODOO_BASE_URL:
        missing.append("ODOO_BASE_URL")
    if not settings.ODOO_DB:
        missing.append("ODOO_DB")
    if not settings.ODOO_USERNAME:
        missing.append("ODOO_USERNAME")
    if not settings.ODOO_PASSWORD:
        missing.append("ODOO_PASSWORD")

    if missing:
        print(f"  ✗ Missing required environment variables: {', '.join(missing)}")
        return 1

    print(f"  ✓ ODOO_BASE_URL: {settings.ODOO_BASE_URL}")
    print(f"  ✓ ODOO_DB: {settings.ODOO_DB}")
    print(f"  ✓ ODOO_USERNAME: {settings.ODOO_USERNAME}")
    print(f"  ✓ ODOO_PASSWORD: ***CONFIGURED***")
    print(f"  ✓ ODOO_TIMEOUT_SECONDS: {settings.ODOO_TIMEOUT_SECONDS}")
    print(f"  ✓ ODOO_VERIFY_SSL: {settings.ODOO_VERIFY_SSL}")

    # Create client
    client = OdooClient(
        base_url=settings.ODOO_BASE_URL,
        db=settings.ODOO_DB,
        username=settings.ODOO_USERNAME,
        password=settings.ODOO_PASSWORD,
        timeout_seconds=settings.ODOO_TIMEOUT_SECONDS,
        verify_ssl=settings.ODOO_VERIFY_SSL,
    )

    try:
        # Test authentication
        print("\n[2/4] Testing Odoo authentication...")
        try:
            uid = await client.authenticate()
            print(f"  ✓ Authentication successful")
            print(f"  ✓ User ID (uid): {uid}")
        except Exception as e:
            print(f"  ✗ Authentication failed: {e}")
            return 1

        # Test reading current user
        print("\n[3/4] Testing read access (res.users)...")
        try:
            users = await client.read("res.users", [uid], fields=["name", "login", "email"])
            if users:
                user = users[0]
                print(f"  ✓ Current user name: {user.get('name')}")
                print(f"  ✓ Current user login: {user.get('login')}")
                print(f"  ✓ Current user email: {user.get('email', 'N/A')}")
            else:
                print("  ✗ Failed to read user data")
                return 1
        except Exception as e:
            print(f"  ✗ Read failed: {e}")
            return 1

        # Test searching contacts
        print("\n[4/4] Testing search access (res.partner)...")
        try:
            partners = await client.search_read(
                "res.partner",
                [("is_company", "=", True)],
                fields=["name"],
                limit=3,
            )
            print(f"  ✓ Found {len(partners)} company partner(s)")
            for p in partners[:3]:
                print(f"    - {p.get('name')}")
        except Exception as e:
            print(f"  ✗ Search failed: {e}")
            return 1

        print("\n" + "=" * 60)
        print("PASS - Odoo connection verification completed successfully")
        print("=" * 60)
        return 0

    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

