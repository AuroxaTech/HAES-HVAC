#!/usr/bin/env python3
"""
HAES HVAC - Email Configuration Verification Script

Tests that SMTP email configuration is properly set up and can connect.
Supports dry-run mode for safe testing.

Usage:
    # Dry-run (safe, no actual email sent)
    python scripts/verify_email_config.py
    
    # Test actual connection (requires valid credentials)
    SMTP_DRY_RUN=false python scripts/verify_email_config.py
    
    # Test with override recipient
    SMTP_TEST_TO_EMAIL=test@example.com python scripts/verify_email_config.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.integrations.email_notifications import (
    create_email_service_from_settings,
    build_emergency_notification_email,
    send_emergency_email,
)


def check_settings() -> dict[str, tuple[bool, str]]:
    """
    Check if all required SMTP settings are configured.
    
    Returns:
        Dict mapping setting name to (is_configured, value_preview)
    """
    settings = get_settings()
    
    checks = {}
    
    checks["SMTP_HOST"] = (
        bool(settings.SMTP_HOST),
        settings.SMTP_HOST[:20] + "..." if len(settings.SMTP_HOST) > 20 else settings.SMTP_HOST or "not set"
    )
    
    checks["SMTP_PORT"] = (
        settings.SMTP_PORT > 0,
        str(settings.SMTP_PORT)
    )
    
    checks["SMTP_FROM_EMAIL"] = (
        bool(settings.SMTP_FROM_EMAIL),
        settings.SMTP_FROM_EMAIL or "not set"
    )
    
    checks["SMTP_USERNAME"] = (
        bool(settings.SMTP_USERNAME),
        settings.SMTP_USERNAME[:10] + "..." if settings.SMTP_USERNAME and len(settings.SMTP_USERNAME) > 10 else settings.SMTP_USERNAME or "not set (optional)"
    )
    
    checks["SMTP_PASSWORD"] = (
        bool(settings.SMTP_PASSWORD),
        "***" if settings.SMTP_PASSWORD else "not set (optional)"
    )
    
    checks["SMTP_USE_TLS"] = (
        True,  # Always valid
        "enabled" if settings.SMTP_USE_TLS else "disabled"
    )
    
    checks["SMTP_DRY_RUN"] = (
        True,  # Always valid
        "enabled" if settings.SMTP_DRY_RUN else "disabled"
    )
    
    return checks


def test_service_creation() -> tuple[bool, str]:
    """Test that EmailNotificationService can be created."""
    try:
        service = create_email_service_from_settings()
        if service is None:
            return False, "Service creation returned None (check SMTP_HOST and SMTP_FROM_EMAIL)"
        return True, f"Service created successfully (dry_run={service.dry_run})"
    except Exception as e:
        return False, f"Service creation failed: {e}"


def test_dry_run_email() -> tuple[bool, str]:
    """Test sending an email in dry-run mode."""
    import asyncio
    
    settings = get_settings()
    
    # Force dry-run if not already set
    original_dry_run = settings.SMTP_DRY_RUN
    if not original_dry_run:
        settings.SMTP_DRY_RUN = True
    
    try:
        result = asyncio.run(send_emergency_email(
            to_email="test@example.com",
            customer_name="Test Customer",
            tech_name="Junior",
            eta_hours_min=1.5,
            eta_hours_max=3.0,
            total_fee=204.00,
            lead_id=9999,
            address="123 Test St, DeSoto, TX 75115",
            phone="+19725551234",
        ))
        
        if result.get("status") == "dry_run":
            return True, "Dry-run email test passed (email logged, not sent)"
        elif result.get("status") == "disabled":
            return False, f"Email disabled: {result.get('reason', 'unknown')}"
        else:
            return False, f"Unexpected status: {result.get('status')}"
            
    except Exception as e:
        return False, f"Dry-run test failed: {e}"
    finally:
        settings.SMTP_DRY_RUN = original_dry_run


def test_connection() -> tuple[bool, str]:
    """Test actual SMTP connection (if dry-run is disabled)."""
    settings = get_settings()
    
    if settings.SMTP_DRY_RUN:
        return None, "Skipped (SMTP_DRY_RUN=true)"
    
    if not settings.SMTP_HOST:
        return None, "Skipped (SMTP_HOST not configured)"
    
    try:
        service = create_email_service_from_settings()
        if not service:
            return None, "Skipped (service not configured)"
        
        # Try to connect (don't send, just verify connection)
        import smtplib
        
        if service.use_tls and service.port == 587:
            server = smtplib.SMTP(service.host, service.port, timeout=10)
            server.starttls()
        elif service.port == 465:
            server = smtplib.SMTP_SSL(service.host, service.port, timeout=10)
        else:
            server = smtplib.SMTP(service.host, service.port, timeout=10)
        
        # Try to authenticate
        if service.username and service.password:
            server.login(service.username, service.password)
        
        server.quit()
        return True, "SMTP connection successful"
        
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP authentication failed: {e}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Connection test failed: {e}"


def test_email_template() -> tuple[bool, str]:
    """Test that email templates can be generated."""
    try:
        html, text = build_emergency_notification_email(
            customer_name="Template Test",
            tech_name="Junior",
            eta_hours_min=1.5,
            eta_hours_max=3.0,
            total_fee=204.00,
            lead_id=1234,
            address="123 Test St",
            phone="+19725551234",
        )
        
        if not html or not text:
            return False, "Template generated empty content"
        
        if "HVAC-R Finest" not in html or "HVAC-R Finest" not in text:
            return False, "Template missing company name"
        
        if "Junior" not in html or "Junior" not in text:
            return False, "Template missing tech name"
        
        if "$204.00" not in html or "$204.00" not in text:
            return False, "Template missing pricing"
        
        return True, f"Template OK (HTML: {len(html)} chars, Text: {len(text)} chars)"
        
    except Exception as e:
        return False, f"Template generation failed: {e}"


def print_results(results: dict[str, tuple[bool | None, str]]) -> bool:
    """Print test results and return overall pass/fail."""
    print("\n" + "=" * 60)
    print("EMAIL CONFIGURATION VERIFICATION RESULTS")
    print("=" * 60)
    
    all_passed = True
    
    for name, (passed, detail) in results.items():
        if passed is None:
            status = "⏭️  SKIP"
        elif passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_passed = False
        
        print(f"{status}  {name}")
        print(f"        → {detail}")
    
    print("\n" + "-" * 60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED")
    else:
        print("⚠️  SOME CHECKS FAILED")
    print("-" * 60)
    
    return all_passed


def main():
    """Run the verification."""
    print("=" * 60)
    print("HAES HVAC - Email Configuration Verification")
    print("=" * 60)
    print()
    
    # Check settings
    print("Checking SMTP settings...")
    settings_checks = check_settings()
    
    results = {}
    
    # Settings validation
    required_settings = ["SMTP_HOST", "SMTP_FROM_EMAIL"]
    for setting in required_settings:
        is_set, preview = settings_checks[setting]
        results[f"Setting: {setting}"] = (is_set, preview)
    
    # Optional settings
    for setting in ["SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_PORT", "SMTP_USE_TLS", "SMTP_DRY_RUN"]:
        is_set, preview = settings_checks[setting]
        results[f"Setting: {setting}"] = (True, preview)  # Optional, so always pass
    
    # Test service creation
    print("\nTesting service creation...")
    passed, detail = test_service_creation()
    results["Service Creation"] = (passed, detail)
    
    # Test email template
    print("\nTesting email templates...")
    passed, detail = test_email_template()
    results["Email Template"] = (passed, detail)
    
    # Test dry-run mode
    print("\nTesting dry-run mode...")
    passed, detail = test_dry_run_email()
    results["Dry-Run Email"] = (passed, detail)
    
    # Test actual connection (if dry-run disabled)
    settings = get_settings()
    if not settings.SMTP_DRY_RUN and settings.SMTP_HOST:
        print("\nTesting SMTP connection (this may take a moment)...")
        passed, detail = test_connection()
        results["SMTP Connection"] = (passed, detail)
    else:
        results["SMTP Connection"] = (None, "Skipped (dry-run enabled or host not configured)")
    
    # Print results
    all_passed = print_results(results)
    
    print()
    print("Configuration Summary:")
    settings = get_settings()
    print(f"  SMTP Host: {settings.SMTP_HOST or 'NOT SET'}")
    print(f"  SMTP Port: {settings.SMTP_PORT}")
    print(f"  From Email: {settings.SMTP_FROM_EMAIL or 'NOT SET'}")
    print(f"  Use TLS: {settings.SMTP_USE_TLS}")
    print(f"  Dry Run: {settings.SMTP_DRY_RUN}")
    print(f"  Test Override: {settings.SMTP_TEST_TO_EMAIL or 'none'}")
    print()
    
    if not all_passed:
        print("Troubleshooting:")
        print("1. Check .env file has SMTP_HOST, SMTP_PORT, SMTP_FROM_EMAIL set")
        print("2. Verify SMTP credentials (SMTP_USERNAME, SMTP_PASSWORD) if required")
        print("3. Test connection manually: telnet <smtp_host> <smtp_port>")
        print("4. For safe testing, enable SMTP_DRY_RUN=true")
        print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
