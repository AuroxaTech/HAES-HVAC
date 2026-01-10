#!/usr/bin/env python3
"""
Quick test script for SMS from production.
This script is designed to be run via fly ssh console.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.integrations.twilio_sms import send_emergency_sms, create_twilio_client_from_settings


async def main():
    """Test SMS sending from production."""
    settings = get_settings()
    
    print("=" * 60)
    print("Production SMS Test")
    print("=" * 60)
    print(f"TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID[:10]}..." if settings.TWILIO_ACCOUNT_SID else "NOT SET")
    print(f"TWILIO_AUTH_TOKEN: {'***' if settings.TWILIO_AUTH_TOKEN else 'NOT SET'}")
    print(f"TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER or 'NOT SET'}")
    print(f"TWILIO_DRY_RUN: {settings.TWILIO_DRY_RUN}")
    print(f"TWILIO_TEST_TO_NUMBER: {settings.TWILIO_TEST_TO_NUMBER or 'none'}")
    print(f"FEATURE_EMERGENCY_SMS: {settings.FEATURE_EMERGENCY_SMS}")
    print()
    
    # Check if configured
    client = create_twilio_client_from_settings()
    if not client:
        print("❌ Twilio not configured! Missing credentials.")
        print()
        print("Required environment variables:")
        print("  TWILIO_ACCOUNT_SID=ACxxxxxx")
        print("  TWILIO_AUTH_TOKEN=your_auth_token")
        print("  TWILIO_PHONE_NUMBER=+1xxxxxxxxxx")
        return 1
    
    # Use test number or provided number
    to_phone = settings.TWILIO_TEST_TO_NUMBER or "+923035699010"
    
    print(f"Sending test SMS to: {to_phone}")
    print()
    
    result = await send_emergency_sms(
        to_phone=to_phone,
        customer_name="Production Test",
        tech_name="Junior",
        eta_hours_min=1.5,
        eta_hours_max=3.0,
        total_fee=204.00,
    )
    
    print(f"Status: {result.get('status')}")
    
    # Twilio statuses: "queued" (accepted, processing), "sent" (sent to carrier), "delivered" (delivered to recipient)
    # Both "queued" and "sent" are success states
    status = result.get("status", "").lower()
    
    if status == "sent" or status == "queued" or status == "delivered":
        print("✅ SMS sent successfully!")
        print(f"   Message SID: {result.get('message_sid', 'N/A')}")
        print(f"   To: {result.get('to', 'N/A')}")
        print(f"   Status: {status} (Twilio accepted the message)")
        if status == "queued":
            print("   Note: Message is queued for delivery (normal for international SMS)")
        return 0
    elif status == "dry_run":
        print("⏭️  Dry-run mode: SMS logged but not sent")
        print(f"   To: {result.get('to', 'N/A')}")
        print(f"   Body Preview: {result.get('body_preview', 'N/A')}")
        return 0
    elif status == "disabled":
        print(f"⚠️  SMS disabled: {result.get('reason', 'unknown')}")
        return 1
    else:
        error_msg = result.get('error', 'unknown error')
        print(f"❌ Failed: {error_msg}")
        print(f"   Status: {status}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
