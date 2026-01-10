#!/usr/bin/env python3
"""
HAES HVAC - Test Email Sending

Sends a test email to verify SMTP configuration is working correctly.
This script will send an actual email if SMTP_DRY_RUN=false.

Usage:
    # Dry-run (safe, no email sent)
    python scripts/test_email_send.py
    
    # Send real email (requires valid SMTP config)
    SMTP_DRY_RUN=false python scripts/test_email_send.py
    
    # Override recipient
    SMTP_TEST_TO_EMAIL=hamsimirza1@gmail.com python scripts/test_email_send.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.integrations.email_notifications import (
    create_email_service_from_settings,
    send_emergency_email,
    send_service_confirmation_email,
)


def print_config():
    """Print current SMTP configuration."""
    settings = get_settings()
    
    print("Current SMTP Configuration:")
    print(f"  SMTP_HOST: {settings.SMTP_HOST or 'NOT SET'}")
    print(f"  SMTP_PORT: {settings.SMTP_PORT}")
    print(f"  SMTP_FROM_EMAIL: {settings.SMTP_FROM_EMAIL or 'NOT SET'}")
    print(f"  SMTP_USERNAME: {settings.SMTP_USERNAME or 'not set (optional)'}")
    print(f"  SMTP_PASSWORD: {'***' if settings.SMTP_PASSWORD else 'not set (optional)'}")
    print(f"  SMTP_USE_TLS: {settings.SMTP_USE_TLS}")
    print(f"  SMTP_DRY_RUN: {settings.SMTP_DRY_RUN}")
    print(f"  SMTP_TEST_TO_EMAIL: {settings.SMTP_TEST_TO_EMAIL or 'none'}")
    print()


def validate_config() -> tuple[bool, str]:
    """Validate SMTP configuration is complete."""
    settings = get_settings()
    
    missing = []
    if not settings.SMTP_HOST:
        missing.append("SMTP_HOST")
    if not settings.SMTP_FROM_EMAIL:
        missing.append("SMTP_FROM_EMAIL")
    
    if missing:
        return False, f"Missing required settings: {', '.join(missing)}"
    
    return True, "Configuration valid"


async def test_emergency_email():
    """Test sending emergency email."""
    settings = get_settings()
    
    # Use test email if configured, otherwise require explicit recipient
    to_email = settings.SMTP_TEST_TO_EMAIL or "test@example.com"
    
    print("=" * 60)
    print("TEST 1: Emergency Email")
    print("=" * 60)
    print(f"Recipient: {to_email}")
    print(f"Dry Run: {settings.SMTP_DRY_RUN}")
    print()
    
    try:
        result = await send_emergency_email(
            to_email=to_email,
            customer_name="Test Customer",
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
            print(f"   Subject: 🚨 Emergency Service Request - HVAC-R Finest")
            return True
        elif result.get("status") == "dry_run":
            print("⏭️  Dry-run mode: Email logged but not sent")
            print(f"   To: {', '.join(result.get('to', []))}")
            print(f"   Subject: 🚨 Emergency Service Request - HVAC-R Finest")
            return None
        elif result.get("status") == "disabled":
            print(f"❌ Email disabled: {result.get('reason', 'unknown')}")
            return False
        else:
            print(f"❌ Failed: {result.get('error', 'unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_confirmation_email():
    """Test sending service confirmation email."""
    settings = get_settings()
    
    to_email = settings.SMTP_TEST_TO_EMAIL or "test@example.com"
    
    print("\n" + "=" * 60)
    print("TEST 2: Service Confirmation Email")
    print("=" * 60)
    print(f"Recipient: {to_email}")
    print(f"Dry Run: {settings.SMTP_DRY_RUN}")
    print()
    
    try:
        result = await send_service_confirmation_email(
            to_email=to_email,
            customer_name="Test Customer",
            is_same_day=True,
        )
        
        print(f"Status: {result.get('status')}")
        
        if result.get("status") == "sent":
            print("✅ Email sent successfully!")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            print(f"   To: {', '.join(result.get('to', []))}")
            print(f"   Subject: Service Request Confirmation - HVAC-R Finest")
            return True
        elif result.get("status") == "dry_run":
            print("⏭️  Dry-run mode: Email logged but not sent")
            print(f"   To: {', '.join(result.get('to', []))}")
            return None
        elif result.get("status") == "disabled":
            print(f"❌ Email disabled: {result.get('reason', 'unknown')}")
            return False
        else:
            print(f"❌ Failed: {result.get('error', 'unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run email tests."""
    print("=" * 60)
    print("HAES HVAC - Email Sending Test")
    print("=" * 60)
    print()
    
    # Print configuration
    print_config()
    
    # Validate configuration
    is_valid, message = validate_config()
    if not is_valid:
        print(f"❌ Configuration Error: {message}")
        print()
        print("To configure SMTP, add these to your .env file:")
        print("  SMTP_HOST=smtp.gmail.com          # Or your SMTP server")
        print("  SMTP_PORT=587")
        print("  SMTP_FROM_EMAIL=your-email@gmail.com")
        print("  SMTP_USERNAME=your-email@gmail.com  # If auth required")
        print("  SMTP_PASSWORD=your-app-password      # If auth required")
        print("  SMTP_USE_TLS=true")
        print("  SMTP_DRY_RUN=false                  # Set false to send real emails")
        print("  SMTP_TEST_TO_EMAIL=hamsimirza1@gmail.com")
        print()
        print("Note: For Gmail, you need to:")
        print("  1. Enable 2-factor authentication")
        print("  2. Generate an 'App Password' (not your regular password)")
        print("  3. Use the app password in SMTP_PASSWORD")
        return 1
    
    settings = get_settings()
    
    if settings.SMTP_DRY_RUN:
        print("⚠️  WARNING: SMTP_DRY_RUN=true - emails will be logged but NOT sent")
        print("   To send real emails, set SMTP_DRY_RUN=false in .env")
        print()
    
    if not settings.SMTP_TEST_TO_EMAIL:
        print("⚠️  WARNING: SMTP_TEST_TO_EMAIL not set - using default test@example.com")
        print("   To test with your email, set SMTP_TEST_TO_EMAIL=hamsimirza1@gmail.com")
        print()
    
    # Confirm if actually sending
    if not settings.SMTP_DRY_RUN:
        print("⚠️  ATTENTION: SMTP_DRY_RUN=false - this will send REAL emails!")
        print(f"   Recipient: {settings.SMTP_TEST_TO_EMAIL or 'test@example.com'}")
        print()
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ("yes", "y"):
            print("Cancelled.")
            return 1
        print()
    
    # Run tests
    result1 = await test_emergency_email()
    result2 = await test_service_confirmation_email()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if result1 is True or result2 is True:
        print("✅ At least one email was sent successfully!")
        if settings.SMTP_DRY_RUN:
            print("   (Dry-run mode was enabled, so emails were only logged)")
        else:
            print(f"   Check inbox: {settings.SMTP_TEST_TO_EMAIL or 'test@example.com'}")
    elif result1 is None or result2 is None:
        print("⏭️  Dry-run mode: Emails were logged but not sent")
        print("   Set SMTP_DRY_RUN=false to send real emails")
    else:
        print("❌ Email sending failed")
        print("   Check SMTP configuration and try again")
    
    print("=" * 60)
    
    return 0 if (result1 is True or result2 is True) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
