#!/usr/bin/env python3
"""
Production test for check_availability tool.

Calls production /vapi/server with a check_availability tool call (signed with
VAPI_WEBHOOK_SECRET) and verifies: 200, result has speak and next_available_slots
with at most 2 slots.

Usage:
    python scripts/test_production_check_availability.py
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


def generate_vapi_signature(body_bytes: bytes, secret: str) -> str:
    if not secret:
        return ""
    return hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()


def build_tool_calls_payload(tool_name: str, tool_call_id: str, parameters: dict) -> dict:
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": f"test-check-avail-{uuid.uuid4().hex[:12]}"},
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


async def run_test():
    print("=" * 60)
    print("Production test: check_availability tool")
    print("URL:", PROD_URL)
    print("=" * 60)

    if not VAPI_WEBHOOK_SECRET:
        print("ERROR: VAPI_WEBHOOK_SECRET not set in .env")
        return False

    payload = build_tool_calls_payload(
        "check_availability",
        f"check-avail-{uuid.uuid4().hex[:8]}",
        {
            "service_type": "maintenance",
            "zip_code": "75115",
        },
    )
    body_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_vapi_signature(body_bytes, VAPI_WEBHOOK_SECRET)
    headers = {"Content-Type": "application/json", "x-vapi-signature": signature}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(PROD_URL, content=body_bytes, headers=headers)

    status = response.status_code
    try:
        body = response.json()
    except Exception:
        body = {"_raw": response.text}

    if status != 200:
        print(f"FAIL: HTTP {status}")
        print(json.dumps(body, indent=2))
        return False

    results = (body or {}).get("results", [])
    if not results:
        print("FAIL: No results in response")
        print(json.dumps(body, indent=2))
        return False

    try:
        result = json.loads(results[0].get("result", "{}"))
    except json.JSONDecodeError:
        print("FAIL: Could not parse first result as JSON")
        print(json.dumps(body, indent=2))
        return False

    speak = result.get("speak", "")
    slots = result.get("data", {}).get("next_available_slots") or []
    action = result.get("action", "")

    print("\n--- Response ---")
    print("action:", action)
    print("speak:", (speak[:200] + "..." if len(speak) > 200 else speak))
    print("next_available_slots count:", len(slots))
    for i, s in enumerate(slots):
        print(f"  slot {i+1}: start={s.get('start')}")
    print("---")

    ok = True
    if not speak:
        print("FAIL: Missing 'speak' in result")
        ok = False
    if action != "needs_human" and not result.get("data", {}).get("no_slots_available"):
        print("WARN: Expected action=needs_human when slots returned (or no_slots_available in data)")
    if len(slots) > 2:
        print(f"FAIL: Tool returned {len(slots)} slots; expected at most 2")
        ok = False
    else:
        print("OK: Slot count <= 2")

    if ok:
        print("\ncheck_availability production test PASSED")
    else:
        print("\ncheck_availability production test FAILED")
    return ok


if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
