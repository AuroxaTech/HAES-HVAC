#!/usr/bin/env python3
"""
HAES HVAC - Production Checklist Script

Validates configuration and readiness for production deployment.
Run this before deploying to production.
"""

import os
import sys
from typing import NamedTuple


class CheckResult(NamedTuple):
    """Result of a configuration check."""
    name: str
    passed: bool
    message: str
    critical: bool = False


def check_environment() -> CheckResult:
    """Check ENVIRONMENT is set to production."""
    env = os.environ.get("ENVIRONMENT", "")
    if env == "production":
        return CheckResult("ENVIRONMENT", True, "Set to production")
    elif env:
        return CheckResult("ENVIRONMENT", False, f"Set to '{env}' (should be 'production')", critical=True)
    else:
        return CheckResult("ENVIRONMENT", False, "Not set (should be 'production')", critical=True)


def check_database_url() -> CheckResult:
    """Check DATABASE_URL is configured for production."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return CheckResult("DATABASE_URL", False, "Not configured", critical=True)
    
    if "localhost" in url or "127.0.0.1" in url:
        return CheckResult("DATABASE_URL", False, "Points to localhost (use production database)", critical=True)
    
    if "password" not in url.lower() and "@" not in url:
        return CheckResult("DATABASE_URL", False, "May be missing authentication", critical=True)
    
    return CheckResult("DATABASE_URL", True, "Configured (ends with: ...{})".format(url[-20:]))


def check_odoo_credentials() -> CheckResult:
    """Check Odoo credentials are configured."""
    url = os.environ.get("ODOO_BASE_URL", "")
    db = os.environ.get("ODOO_DB", "")
    user = os.environ.get("ODOO_USERNAME", "")
    pwd = os.environ.get("ODOO_PASSWORD", "")
    
    if not all([url, db, user, pwd]):
        missing = []
        if not url: missing.append("ODOO_BASE_URL")
        if not db: missing.append("ODOO_DB")
        if not user: missing.append("ODOO_USERNAME")
        if not pwd: missing.append("ODOO_PASSWORD")
        return CheckResult("Odoo Credentials", False, f"Missing: {', '.join(missing)}", critical=True)
    
    return CheckResult("Odoo Credentials", True, f"All configured (URL: {url[:30]}...)")


def check_vapi_config() -> CheckResult:
    """Check Vapi configuration."""
    api_key = os.environ.get("VAPI_API_KEY", "")
    webhook_secret = os.environ.get("VAPI_WEBHOOK_SECRET", "")
    
    if not api_key:
        return CheckResult("Vapi API Key", False, "VAPI_API_KEY not set", critical=True)
    
    if not webhook_secret:
        return CheckResult("Vapi Webhook Secret", False, "VAPI_WEBHOOK_SECRET not set (webhook verification disabled)")
    
    return CheckResult("Vapi Configuration", True, "API key and webhook secret configured")


def check_twilio_config() -> CheckResult:
    """Check Twilio configuration."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    phone = os.environ.get("TWILIO_PHONE_NUMBER", "")
    
    if not all([sid, token, phone]):
        missing = []
        if not sid: missing.append("TWILIO_ACCOUNT_SID")
        if not token: missing.append("TWILIO_AUTH_TOKEN")
        if not phone: missing.append("TWILIO_PHONE_NUMBER")
        return CheckResult("Twilio Config", False, f"Missing: {', '.join(missing)} (SMS disabled)")
    
    return CheckResult("Twilio Configuration", True, f"All configured (phone: {phone})")


def check_log_level() -> CheckResult:
    """Check LOG_LEVEL is appropriate for production."""
    level = os.environ.get("LOG_LEVEL", "INFO")
    
    if level == "DEBUG":
        return CheckResult("LOG_LEVEL", False, "Set to DEBUG (should be INFO or WARNING in production)")
    
    return CheckResult("LOG_LEVEL", True, f"Set to {level}")


def check_rate_limiting() -> CheckResult:
    """Check rate limiting is enabled."""
    enabled = os.environ.get("RATE_LIMIT_ENABLED", "true")
    
    if enabled.lower() in ("false", "0", "no"):
        return CheckResult("Rate Limiting", False, "Disabled (should be enabled in production)")
    
    return CheckResult("Rate Limiting", True, "Enabled")


def check_no_dotenv_in_production() -> CheckResult:
    """Check that .env file is not present in production."""
    if os.path.exists(".env"):
        return CheckResult(".env File", False, "Found in directory (use environment variables only)")
    
    return CheckResult(".env File", True, "Not present (good - using environment variables)")


def run_checks() -> list[CheckResult]:
    """Run all production checks."""
    checks = [
        check_environment,
        check_database_url,
        check_odoo_credentials,
        check_vapi_config,
        check_twilio_config,
        check_log_level,
        check_rate_limiting,
        check_no_dotenv_in_production,
    ]
    
    return [check() for check in checks]


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("HAES HVAC Production Checklist")
    print("=" * 60)
    print()
    
    results = run_checks()
    
    passed = 0
    warnings = 0
    critical_failures = 0
    
    for result in results:
        if result.passed:
            status = "✓ PASS"
            passed += 1
        elif result.critical:
            status = "✗ FAIL (CRITICAL)"
            critical_failures += 1
        else:
            status = "⚠ WARN"
            warnings += 1
        
        print(f"{status}: {result.name}")
        print(f"       {result.message}")
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {warnings} warnings, {critical_failures} critical failures")
    print("=" * 60)
    
    if critical_failures > 0:
        print("\n❌ PRODUCTION DEPLOYMENT NOT RECOMMENDED")
        print("   Fix critical issues before deploying.")
        return 1
    elif warnings > 0:
        print("\n⚠️  PRODUCTION DEPLOYMENT POSSIBLE WITH WARNINGS")
        print("   Some features may be disabled.")
        return 0
    else:
        print("\n✅ PRODUCTION DEPLOYMENT READY")
        return 0


if __name__ == "__main__":
    sys.exit(main())

