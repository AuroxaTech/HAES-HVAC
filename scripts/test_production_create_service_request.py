#!/usr/bin/env python3
"""
Test create_service_request tool against production /vapi/server.

Sends a valid tool call (phone, address, issue_description + optional fields),
prints full request and response for debugging Vapi issues.

Usage:
    python scripts/test_production_create_service_request.py
"""

import asyncio
import hmac
import hashlib
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
import httpx

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)
load_dotenv()

PROD_URL = os.getenv("VAPI_SERVER_URL", "https://haes-hvac.fly.dev/vapi/server")
VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")
TEST_PHONE = os.getenv("TEST_PHONE", "+15551234567")


def generate_vapi_signature(body_bytes: bytes, secret: str) -> str:
    if not secret:
        return ""
    return hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()


async def main():
    print("=" * 60)
    print("Production test: create_service_request")
    print("URL:", PROD_URL)
    print("=" * 60)

    if not VAPI_WEBHOOK_SECRET:
        print("ERROR: VAPI_WEBHOOK_SECRET not set in .env")
        return 1

    # Required: phone, address, issue_description (per handler)
    parameters = {
        "customer_name": "Prod Test Service Request",
        "phone": TEST_PHONE,
        "address": "123 Test St, DeSoto, TX 75115",
        "issue_description": "AC not cooling properly",
        "urgency": "medium",
        "property_type": "residential",
        "lead_source": "Other",
    }

    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": f"test-csr-{uuid.uuid4().hex[:12]}", "customer": {"number": TEST_PHONE}},
            "toolWithToolCallList": [
                {
                    "name": "create_service_request",
                    "toolCall": {
                        "id": f"tc-{uuid.uuid4().hex[:8]}",
                        "parameters": parameters,
                    },
                }
            ],
        }
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_vapi_signature(body_bytes, VAPI_WEBHOOK_SECRET)
    headers = {"Content-Type": "application/json", "x-vapi-signature": signature}

    print("\n--- Request (parameters) ---")
    print(json.dumps(parameters, indent=2))
    print()

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(PROD_URL, content=body_bytes, headers=headers)

    print("--- Response ---")
    print("Status:", response.status_code)
    try:
        body = response.json()
        print("Body:", json.dumps(body, indent=2))
    except Exception:
        print("Body (raw):", response.text[:2000])

    if response.status_code != 200:
        print("\n❌ FAIL: Non-200 status")
        return 1

    results = (body or {}).get("results", [])
    if not results:
        print("\n❌ FAIL: No results in response")
        return 1

    try:
        result = json.loads(results[0].get("result", "{}"))
    except json.JSONDecodeError:
        print("\n❌ FAIL: First result not valid JSON")
        return 1

    speak = result.get("speak", "")
    action = result.get("action", "")
    data = result.get("data", {})

    print("\n--- Parsed result ---")
    print("action:", action)
    print("speak:", speak[:300] + ("..." if len(speak) > 300 else ""))
    print("data keys:", list(data.keys()) if isinstance(data, dict) else data)

    if "speak" not in result or "action" not in result:
        print("\n❌ FAIL: Result missing speak or action")
        return 1

    print("\n✅ create_service_request production test completed (check action/speak above)")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
