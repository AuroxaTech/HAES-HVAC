#!/usr/bin/env python3
"""
Validate Fly.io secrets for haes-hvac app.

Fetches secret names from Fly (values are never exposed by Fly API).
Checks that required secrets exist and optionally that .env has the same keys set.
Does not compare values (Fly does not expose secret values).

Usage:
    fly secrets list --app haes-hvac -j | python scripts/validate_fly_secrets.py
    # Or run this script (it runs fly for you):
    python scripts/validate_fly_secrets.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Load .env for local check (keys only, no values printed)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    from dotenv import dotenv_values
    _env_keys = set(dotenv_values(_env_path).keys())
else:
    _env_keys = set()

# Required for /vapi/server webhook signing and Test B.9 script
REQUIRED_FOR_VAPI = [
    "VAPI_WEBHOOK_SECRET",  # Must match Vapi dashboard; without it, signed requests get 401
    "VAPI_API_KEY",
]

# Other expected secrets (documented in DEPLOYMENT.md)
EXPECTED = [
    "ENVIRONMENT",
    "DATABASE_URL",
    "ODOO_BASE_URL",
    "ODOO_DB",
    "ODOO_USERNAME",
    "ODOO_PASSWORD",
    "VAPI_API_KEY",
    "VAPI_WEBHOOK_SECRET",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "WEBHOOK_BASE_URL",
]


def get_fly_secrets(app: str = "haes-hvac") -> list[dict]:
    """Run fly secrets list -j and return parsed JSON."""
    try:
        out = subprocess.run(
            ["fly", "secrets", "list", "--app", app, "-j"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if out.returncode != 0:
            print(f"fly secrets list failed: {out.stderr or out.stdout}", file=sys.stderr)
            return []
        return json.loads(out.stdout) if out.stdout.strip() else []
    except FileNotFoundError:
        print("fly CLI not found. Install: https://fly.io/docs/hands-on/install-flyctl/", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Failed to parse fly output: {e}", file=sys.stderr)
        return []


def main() -> None:
    # Allow piping: fly secrets list -j | python validate_fly_secrets.py
    secrets = []
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            try:
                secrets = json.loads(raw)
            except json.JSONDecodeError:
                print("Invalid JSON from stdin", file=sys.stderr)
                sys.exit(1)
    if not secrets:
        print("Fetching Fly.io secrets for app haes-hvac...")
        secrets = get_fly_secrets("haes-hvac")

    if not secrets:
        print("No secrets returned. Is fly logged in? Run: fly auth login")
        sys.exit(1)

    names = {s.get("name") for s in secrets if s.get("name")}
    status_by_name = {s.get("name"): s.get("status") for s in secrets if s.get("name")}

    print("\n--- Fly.io secrets validation (haes-hvac) ---\n")
    print(f"Total secrets on Fly: {len(names)}\n")

    # Required for Vapi / Test B.9
    missing_vapi = [k for k in REQUIRED_FOR_VAPI if k not in names]
    if missing_vapi:
        print("Missing required for /vapi/server and Test B.9 script:")
        for k in missing_vapi:
            print(f"  - {k}")
        print("\nFix: set on Fly (use same value as in Vapi dashboard and .env):")
        print('  fly secrets set VAPI_WEBHOOK_SECRET="<your-webhook-secret>" --app haes-hvac')
        print()
    else:
        print("Required for Vapi: all present (VAPI_WEBHOOK_SECRET, VAPI_API_KEY).")

    # Expected list
    missing_expected = [k for k in EXPECTED if k not in names]
    if missing_expected:
        print("\nExpected but missing on Fly:")
        for k in missing_expected:
            print(f"  - {k}")
    else:
        print("Expected secrets: all present.")

    # .env comparison (key presence only)
    if _env_keys:
        missing_in_env = [k for k in REQUIRED_FOR_VAPI if k not in _env_keys]
        if missing_in_env:
            print("\n.env: missing keys (add to .env for local Test B.9 script):", missing_in_env)
        else:
            print("\n.env: has required keys for Test B.9 (VAPI_WEBHOOK_SECRET, etc.).")
    else:
        print("\n.env: not found or empty; cannot check.")

    # Summary
    if missing_vapi:
        print("\n❌ Validation failed: set VAPI_WEBHOOK_SECRET on Fly and re-run Test B.9.")
        sys.exit(1)
    print("\n✅ Validation passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
