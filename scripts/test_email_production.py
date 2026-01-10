#!/usr/bin/env python3
"""
Quick test script for email from production.
This script is designed to be run via fly ssh console.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.integrations.email_notifications import send_emergency_email


async def main():
    """Test email sending from production."""
    settings = get_settings()
    
    print("=" * 60)
    print("Production Email Test")
    print("=" * 60)
    print(f"SMTP_HOST: {settings.SMTP_HOST}")
    print(f"SMTP_FROM_EMAIL: {settings.SMTP_FROM_EMAIL}")
    print(f"SMTP_DRY_RUN: {settings.SMTP_DRY_RUN}")
    print(f"SMTP_TEST_TO_EMAIL: {settings.SMTP_TEST_TO_EMAIL}")
    print()
    
    to_email = settings.SMTP_TEST_TO_EMAIL or "hamsimirza1@gmail.com"
    
    print(f"Sending test email to: {to_email}")
    print()
    
    result = await send_emergency_email(
        to_email=to_email,
        customer_name="Production Test Customer",
        tech_name="Junior",
        eta_hours_min=1.5,
        eta_hours_max=3.0,
        total_fee=204.00,
        lead_id=9999,
        address="123 Test St, DeSoto, TX 75115",
        phone="+19725551234",
    )
    
    print(f"Status: {result.get('status')}")
    
    if result.get("status") == "sent":
        print("✅ Email sent successfully!")
        print(f"   Message ID: {result.get('message_id', 'N/A')}")
        print(f"   To: {', '.join(result.get('to', []))}")
        return 0
    elif result.get("status") == "dry_run":
        print("⏭️  Dry-run mode: Email logged but not sent")
        return 0
    else:
        print(f"❌ Failed: {result.get('error', 'unknown error')}")
        if result.get("error"):
            print(f"   Error details: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
