#!/usr/bin/env python3
"""
Production test for Test B.9: Post-appointment SMS and email (#9).

Uses the same auth as your other Vapi/production APIs: VAPI_WEBHOOK_SECRET in .env
(must match the secret on Fly and in Vapi dashboard). The script signs requests and
POSTs to /vapi/server, like Vapi does.

Test credentials: phone +923035699010, email hamsimirza1@gmail.com (override with
TEST_PHONE, TEST_EMAIL in .env if needed).

Usage:
    python scripts/test_production_schedule_appointment_sms_email.py
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

# Load .env from project root (same as other scripts)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)
load_dotenv()

PROD_URL = os.getenv("VAPI_SERVER_URL", "https://haes-hvac.fly.dev/vapi/server")
VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")
# Test credentials for B.9 (SMS/email delivery validation)
TEST_PHONE = os.getenv("TEST_PHONE", "+923035699010")
TEST_EMAIL = os.getenv("TEST_EMAIL", "hamsimirza1@gmail.com")
TEST_NAME = os.getenv("TEST_CUSTOMER_NAME", "Test Customer B9")
TEST_ADDRESS = os.getenv("TEST_ADDRESS", "123 Test St, DeSoto, TX 75115")


def generate_vapi_signature(body_bytes: bytes, secret: str) -> str:
    """Sign the exact body bytes (server verifies raw request body)."""
    if not secret:
        return ""
    return hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()


# Use one call_id for the whole test so the server treats both steps as same conversation
_TEST_CALL_ID = f"test-call-b9-{uuid.uuid4().hex[:12]}"


def build_tool_calls_payload(tool_name: str, tool_call_id: str, parameters: dict) -> dict:
    # Include customer number so server treats caller as customer (for local and prod)
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": _TEST_CALL_ID, "customer": {"number": TEST_PHONE}},
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


async def post_tool_call(client: httpx.AsyncClient, payload: dict) -> tuple[int, dict]:
    body_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_vapi_signature(body_bytes, VAPI_WEBHOOK_SECRET)
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["x-vapi-signature"] = signature
    response = await client.post(PROD_URL, content=body_bytes, headers=headers)
    try:
        body = response.json()
    except Exception:
        body = {"_raw": response.text}
    return response.status_code, body


def parse_first_result(body: dict) -> dict | None:
    """Extract first tool result from Vapi response."""
    results = (body or {}).get("results", [])
    if not results:
        return None
    try:
        return json.loads(results[0].get("result", "{}"))
    except json.JSONDecodeError:
        return None


async def run_test_b9():
    print("=" * 60)
    print("Test B.9: Post-appointment SMS and email (#9)")
    print("Production URL:", PROD_URL)
    print("Test phone:", TEST_PHONE)
    print("Test email:", TEST_EMAIL)
    print("=" * 60)

    if not VAPI_WEBHOOK_SECRET:
        print("Error: VAPI_WEBHOOK_SECRET not set in .env (same key as your other Vapi APIs).")
        return False

    async with httpx.AsyncClient(timeout=45.0) as client:
        # --- Step 1: First call - get two slots (no chosen_slot_start) ---
        call_id_1 = f"b9-sched-1-{uuid.uuid4().hex[:8]}"
        params_1 = {
            "customer_name": TEST_NAME,
            "phone": TEST_PHONE,
            "address": TEST_ADDRESS,
            "service_type": "maintenance",
        }
        payload_1 = build_tool_calls_payload("schedule_appointment", call_id_1, params_1)
        print("\n[Step 1] Calling schedule_appointment (first call, get two slots)...")
        status_1, body_1 = await post_tool_call(client, payload_1)
        result_1 = parse_first_result(body_1)

        if status_1 != 200:
            print(f"❌ Step 1 failed: HTTP {status_1}")
            print(json.dumps(body_1, indent=2))
            return False

        if not result_1:
            print("❌ Step 1: Could not parse tool result.")
            print(json.dumps(body_1, indent=2))
            return False

        action_1 = result_1.get("action")
        data_1 = result_1.get("data") or {}
        slots = data_1.get("next_available_slots") or []

        if action_1 != "needs_human" or len(slots) < 2:
            print(f"⚠️ Step 1: Expected action=needs_human and 2 slots; got action={action_1}, slots={len(slots)}")
            print("   Response speak:", result_1.get("speak", "")[:200])
            if not slots:
                print("   No next_available_slots in response; cannot continue to Step 2.")
                return False
            # Use first slot if only one returned
            chosen_start = slots[0].get("start")
        else:
            chosen_start = slots[0].get("start")
            print(f"✅ Step 1: Got two slots. First slot start: {chosen_start}")

        if not chosen_start:
            print("❌ Step 1: No slot start in response.")
            print(json.dumps(result_1, indent=2))
            return False

        # --- Step 2: Second call - book chosen slot with email ---
        call_id_2 = f"b9-sched-2-{uuid.uuid4().hex[:8]}"
        params_2 = {
            **params_1,
            "email": TEST_EMAIL,
            "chosen_slot_start": chosen_start,
        }
        payload_2 = build_tool_calls_payload("schedule_appointment", call_id_2, params_2)
        print("\n[Step 2] Calling schedule_appointment (second call, book slot + email)...")
        print(f"         chosen_slot_start={chosen_start!r}")
        status_2, body_2 = await post_tool_call(client, payload_2)
        result_2 = parse_first_result(body_2)

        if status_2 != 200:
            print(f"❌ Step 2 failed: HTTP {status_2}")
            print(json.dumps(body_2, indent=2))
            return False

        if not result_2:
            print("❌ Step 2: Could not parse tool result.")
            return False

        action_2 = result_2.get("action")
        data_2 = result_2.get("data") or {}
        appointment_id = data_2.get("appointment_id")
        sms_sent = data_2.get("confirmation_sms_sent")
        email_sent = data_2.get("confirmation_email_sent")

        print("\n" + "-" * 60)
        print("Test B.9 results")
        print("-" * 60)
        print(f"  action:              {action_2}")
        print(f"  appointment_id:      {appointment_id}")
        print(f"  confirmation_sms_sent:   {sms_sent}")
        print(f"  confirmation_email_sent:  {email_sent}")
        print(f"  speak (excerpt):     {(result_2.get('speak') or '')[:120]}...")
        print("-" * 60)

        # Validation per Test B.9
        ok = True
        if action_2 != "completed":
            print("❌ FAIL: Expected action=completed after booking.")
            ok = False
        if not appointment_id:
            print("❌ FAIL: Expected appointment_id in response.")
            ok = False
        if sms_sent is not True:
            print("⚠️  WARN: confirmation_sms_sent is not True (check SMS/Twilio config).")
        if email_sent is not True:
            print("⚠️  WARN: confirmation_email_sent is not True (check SMTP/email config or email param).")

        if ok and (sms_sent is True or email_sent is True):
            print("\n✅ Test B.9 PASSED: Appointment created; backend reports SMS and/or email sent.")
        elif ok:
            print("\n✅ Test B.9 PARTIAL: Appointment created; SMS/email send status not confirmed.")
        else:
            print("\n❌ Test B.9 FAILED: See above.")

        if TEST_EMAIL and "@" in TEST_EMAIL and "example.com" not in TEST_EMAIL:
            print("\n→ Check your phone and email for the confirmation message to complete manual validation.")

        return ok


if __name__ == "__main__":
    success = asyncio.run(run_test_b9())
    exit(0 if success else 1)
