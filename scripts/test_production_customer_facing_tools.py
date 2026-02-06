#!/usr/bin/env python3
"""
Test all customer-facing Vapi tools against production /vapi/server.

Uses VAPI_WEBHOOK_SECRET from .env to sign requests. Sends one tool call per tool
with minimal parameters and validates: HTTP 200, result has "speak" and "action".

Usage:
    python scripts/test_production_customer_facing_tools.py
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


def load_customer_facing_tool_names() -> list[str]:
    """Return sorted list of tool names from doc/vapi/tools/customer_facing/**/*.json."""
    tools_dir = Path(__file__).resolve().parent.parent / "doc" / "vapi" / "tools" / "customer_facing"
    if not tools_dir.exists():
        return []
    names = []
    for f in sorted(tools_dir.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        td = data.get("tool_definition") or data
        func = td.get("function", {})
        name = func.get("name")
        if name:
            names.append(name)
    return sorted(set(names))


# Minimal parameters per tool so we get a valid response (200 + speak + action).
# Tools may return action=needs_human or completed; both are valid.
MINIMAL_PARAMS: dict[str, dict] = {
    "check_business_hours": {},
    "check_availability": {"service_type": "maintenance", "zip_code": "75115"},
    "get_maintenance_plans": {},
    "get_pricing": {"property_type": "residential"},
    "get_service_area_info": {},
    "lookup_customer_profile": {"phone": TEST_PHONE},
    "create_service_request": {
        "customer_name": "Prod Test Customer",
        "phone": TEST_PHONE,
        "address": "123 Test St, DeSoto, TX 75115",
        "issue_description": "Test run",
        "property_type": "residential",
    },
    "schedule_appointment": {
        "customer_name": "Prod Test Customer",
        "phone": TEST_PHONE,
        "address": "123 Test St, DeSoto, TX 75115",
    },
    "reschedule_appointment": {"phone": TEST_PHONE},
    "cancel_appointment": {"phone": TEST_PHONE},
    "check_appointment_status": {"phone": TEST_PHONE},
    "request_quote": {
        "customer_name": "Prod Test Customer",
        "phone": TEST_PHONE,
        "address": "123 Test St, DeSoto, TX 75115",
        "property_type": "residential",
    },
    "check_lead_status": {"phone": TEST_PHONE},
    "request_membership_enrollment": {
        "customer_name": "Prod Test Customer",
        "phone": TEST_PHONE,
        "address": "123 Test St, DeSoto, TX 75115",
        "property_type": "residential",
    },
    "billing_inquiry": {},
    "invoice_request": {},
    "payment_terms_inquiry": {},
    "create_complaint": {
        "customer_name": "Prod Test Customer",
        "phone": TEST_PHONE,
        "complaint_description": "Test complaint from script",
    },
}


def build_payload(tool_name: str, parameters: dict) -> dict:
    call_id = f"test-cf-{uuid.uuid4().hex[:12]}"
    tool_call_id = f"tc-{uuid.uuid4().hex[:8]}"
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": call_id, "customer": {"number": TEST_PHONE}},
            "toolWithToolCallList": [
                {
                    "name": tool_name,
                    "toolCall": {
                        "id": tool_call_id,
                        "parameters": parameters,
                    },
                }
            ],
        }
    }


async def test_tool(client: httpx.AsyncClient, tool_name: str) -> tuple[bool, str]:
    params = MINIMAL_PARAMS.get(tool_name, {})
    payload = build_payload(tool_name, params)
    body_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_vapi_signature(body_bytes, VAPI_WEBHOOK_SECRET)
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["x-vapi-signature"] = signature

    try:
        response = await client.post(PROD_URL, content=body_bytes, headers=headers)
    except Exception as e:
        return False, str(e)

    if response.status_code != 200:
        try:
            body = response.json()
            err = body.get("error") or body.get("detail") or json.dumps(body)[:200]
        except Exception:
            err = response.text[:200]
        return False, f"HTTP {response.status_code}: {err}"

    try:
        body = response.json()
    except Exception:
        return False, "Response not JSON"

    results = (body or {}).get("results", [])
    if not results:
        return False, "No results in response"

    try:
        result = json.loads(results[0].get("result", "{}"))
    except json.JSONDecodeError:
        return False, "First result not valid JSON"

    if not isinstance(result, dict):
        return False, "Result is not a dict"

    if "speak" not in result:
        return False, "Missing 'speak' in result"
    if "action" not in result:
        return False, "Missing 'action' in result"

    action = result.get("action")
    if action not in ("completed", "needs_human", "error"):
        return False, f"Unexpected action: {action!r}"

    return True, f"action={action}"


async def main():
    print("=" * 60)
    print("Production: Customer-facing tools validation")
    print("URL:", PROD_URL)
    print("=" * 60)

    if not VAPI_WEBHOOK_SECRET:
        print("ERROR: VAPI_WEBHOOK_SECRET not set in .env")
        return 1

    tool_names = load_customer_facing_tool_names()
    if not tool_names:
        print("ERROR: No tools found under doc/vapi/tools/customer_facing/")
        return 1

    print(f"Testing {len(tool_names)} tools: {', '.join(tool_names)}\n")

    passed = 0
    failed = 0

    async with httpx.AsyncClient(timeout=35.0) as client:
        for name in tool_names:
            ok, msg = await test_tool(client, name)
            if ok:
                print(f"  ✅ {name}: {msg}")
                passed += 1
            else:
                print(f"  ❌ {name}: {msg}")
                failed += 1

    print()
    print("-" * 60)
    print(f"Result: {passed} passed, {failed} failed (total {len(tool_names)})")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
