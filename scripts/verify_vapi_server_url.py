#!/usr/bin/env python3
"""
HAES HVAC - Vapi Server URL Verification Script

Sends sample payloads to the Vapi Server URL endpoint and validates responses.
Can be run locally or against production.

Usage:
    # Local (development)
    python scripts/verify_vapi_server_url.py
    
    # Production
    python scripts/verify_vapi_server_url.py --prod
    
    # With signature (production)
    VAPI_WEBHOOK_SECRET=your_secret python scripts/verify_vapi_server_url.py --prod --signed
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# Default URLs
LOCAL_URL = "http://localhost:8000"
PROD_URL = "https://haes-hvac.fly.dev"


def generate_signature(body: bytes, secret: str) -> tuple[str, str]:
    """Generate Vapi-compatible signature."""
    timestamp = str(int(time.time()))
    payload = f"{timestamp}.".encode() + body
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return signature, timestamp


def make_request(
    base_url: str,
    payload: dict,
    secret: str | None = None,
    timeout: int = 10,
) -> tuple[int, dict]:
    """Make request to Vapi Server URL endpoint."""
    url = f"{base_url}/vapi/server"
    body = json.dumps(payload).encode()
    
    headers = {"Content-Type": "application/json"}
    
    if secret:
        signature, timestamp = generate_signature(body, secret)
        headers["X-Vapi-Signature"] = signature
        headers["X-Vapi-Timestamp"] = timestamp
    
    try:
        response = httpx.post(url, content=body, headers=headers, timeout=timeout)
        return response.status_code, response.json()
    except Exception as e:
        return -1, {"error": str(e)}


def test_tool_calls_service_request(base_url: str, secret: str | None) -> bool:
    """Test service request via tool-calls."""
    print("\n[TEST] Tool-calls: Service Request")
    
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "test_call_001"},
            "toolCallList": [
                {
                    "id": "tc_service_001",
                    "name": "hael_route",
                    "parameters": {
                        "user_text": "My AC stopped working. I'm John at 123 Main St Dallas. It's an emergency, it's over 90 degrees.",
                        "conversation_context": "Customer called about AC failure, high temperature emergency"
                    }
                }
            ]
        }
    }
    
    status, response = make_request(base_url, payload, secret)
    
    if status != 200:
        print(f"  ✗ Failed: status={status}, response={response}")
        return False
    
    if "results" not in response or len(response["results"]) == 0:
        print(f"  ✗ Failed: no results in response")
        return False
    
    result = json.loads(response["results"][0]["result"])
    print(f"  Action: {result.get('action')}")
    print(f"  Speak: {result.get('speak', '')[:100]}...")
    
    if result.get("action") in ["completed", "needs_human"]:
        print("  ✓ Passed")
        return True
    else:
        print(f"  ✗ Failed: unexpected action")
        return False


def test_tool_calls_quote_request(base_url: str, secret: str | None) -> bool:
    """Test quote request via tool-calls (REVENUE brain)."""
    print("\n[TEST] Tool-calls: Quote Request")
    
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "test_call_002"},
            "toolWithToolCallList": [
                {
                    "name": "hael_route",
                    "toolCall": {
                        "id": "tc_quote_001",
                        "parameters": {
                            "user_text": "I need a quote for a new AC system for my 2500 sqft home",
                            "conversation_context": "New installation inquiry, residential"
                        }
                    }
                }
            ]
        }
    }
    
    status, response = make_request(base_url, payload, secret)
    
    if status != 200:
        print(f"  ✗ Failed: status={status}, response={response}")
        return False
    
    result = json.loads(response["results"][0]["result"])
    print(f"  Action: {result.get('action')}")
    print(f"  Speak: {result.get('speak', '')[:100]}...")
    print("  ✓ Passed")
    return True


def test_tool_calls_billing_inquiry(base_url: str, secret: str | None) -> bool:
    """Test billing inquiry via tool-calls (CORE brain)."""
    print("\n[TEST] Tool-calls: Billing Inquiry")
    
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": "test_call_003"},
            "toolCallList": [
                {
                    "id": "tc_billing_001",
                    "name": "hael_route",
                    "parameters": {
                        "user_text": "What are your payment terms? Do you accept credit cards?",
                        "conversation_context": "Customer asking about billing"
                    }
                }
            ]
        }
    }
    
    status, response = make_request(base_url, payload, secret)
    
    if status != 200:
        print(f"  ✗ Failed: status={status}, response={response}")
        return False
    
    result = json.loads(response["results"][0]["result"])
    print(f"  Action: {result.get('action')}")
    print(f"  Speak: {result.get('speak', '')[:100]}...")
    print("  ✓ Passed")
    return True


def test_transfer_business_hours(base_url: str, secret: str | None) -> bool:
    """Test transfer destination request."""
    print("\n[TEST] Transfer Destination Request")
    
    payload = {
        "message": {
            "type": "transfer-destination-request",
            "call": {"id": "test_call_transfer"}
        }
    }
    
    status, response = make_request(base_url, payload, secret)
    
    if status != 200:
        print(f"  ✗ Failed: status={status}, response={response}")
        return False
    
    if "destination" in response:
        print(f"  Destination: {response['destination']}")
        print("  (Business hours - transfer available)")
    elif "error" in response and response["error"] == "after_hours":
        print(f"  After-hours message: {response.get('message', {}).get('content', '')[:80]}...")
        print("  (After hours - callback mode)")
    
    print("  ✓ Passed")
    return True


def test_end_of_call_report(base_url: str, secret: str | None) -> bool:
    """Test end-of-call-report handling."""
    print("\n[TEST] End of Call Report")
    
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "test_call_end"},
            "summary": "Test call completed successfully",
            "durationSeconds": 60,
            "endedReason": "customer-hung-up"
        }
    }
    
    status, response = make_request(base_url, payload, secret)
    
    if status != 200:
        print(f"  ✗ Failed: status={status}, response={response}")
        return False
    
    if response.get("status") == "ok":
        print("  ✓ Passed")
        return True
    else:
        print(f"  ✗ Failed: unexpected response")
        return False


def test_health_check(base_url: str) -> bool:
    """Test health check endpoint."""
    print("\n[TEST] Health Check")
    
    url = f"{base_url}/vapi/server/health"
    
    try:
        response = httpx.get(url, timeout=10)
        if response.status_code != 200:
            print(f"  ✗ Failed: status={response.status_code}")
            return False
        
        data = response.json()
        print(f"  Status: {data.get('status')}")
        print(f"  Business Hours: {data.get('business_hours')}")
        print(f"  Transfer Number: {data.get('transfer_number')}")
        print("  ✓ Passed")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verify Vapi Server URL endpoint")
    parser.add_argument("--prod", action="store_true", help="Test against production")
    parser.add_argument("--signed", action="store_true", help="Sign requests with VAPI_WEBHOOK_SECRET")
    parser.add_argument("--url", help="Custom base URL")
    args = parser.parse_args()
    
    # Determine base URL
    if args.url:
        base_url = args.url.rstrip("/")
    elif args.prod:
        base_url = PROD_URL
    else:
        base_url = LOCAL_URL
    
    # Get secret if signing
    secret = None
    if args.signed:
        secret = os.environ.get("VAPI_WEBHOOK_SECRET")
        if not secret:
            print("Error: VAPI_WEBHOOK_SECRET environment variable required for --signed")
            sys.exit(1)
    
    print("=" * 60)
    print("HAES HVAC - Vapi Server URL Verification")
    print("=" * 60)
    print(f"Target: {base_url}")
    print(f"Signed: {args.signed}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Run tests
    results = []
    
    results.append(("Health Check", test_health_check(base_url)))
    results.append(("Service Request", test_tool_calls_service_request(base_url, secret)))
    results.append(("Quote Request", test_tool_calls_quote_request(base_url, secret)))
    results.append(("Billing Inquiry", test_tool_calls_billing_inquiry(base_url, secret)))
    results.append(("Transfer Request", test_transfer_business_hours(base_url, secret)))
    results.append(("End of Call", test_end_of_call_report(base_url, secret)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
