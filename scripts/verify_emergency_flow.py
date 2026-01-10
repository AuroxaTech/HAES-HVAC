#!/usr/bin/env python3
"""
HAES HVAC - Emergency Flow Verification Script

Verifies the complete emergency flow by sending a test request to the Vapi
Server URL endpoint and checking for expected response fields.

Usage:
    # Local testing
    python scripts/verify_emergency_flow.py
    
    # Against staging/production
    BASE_URL=https://haes-hvac.fly.dev python scripts/verify_emergency_flow.py
    
    # With SMS dry-run
    TWILIO_DRY_RUN=true python scripts/verify_emergency_flow.py

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import json
import os
import sys

import httpx


def get_base_url() -> str:
    """Get the base URL for testing."""
    return os.environ.get("BASE_URL", "http://localhost:8000")


def create_emergency_payload() -> dict:
    """
    Create a deterministic emergency test payload.
    
    Uses:
    - DeSoto address (75115) to verify Junior assignment
    - "no heat" + 54°F to trigger emergency
    - All required fields for full flow
    """
    return {
        "message": {
            "type": "tool-calls",
            "call": {"id": f"test_emergency_{int(__import__('time').time())}"},
            "toolCallList": [{
                "id": "tc_verify_emergency",
                "name": "hael_route",
                "parameters": {
                    "request_type": "service_request",
                    "customer_name": "Emergency Test User",
                    "phone": "+19725551234",
                    "email": "test@example.com",
                    "address": "123 Verification St, DeSoto, TX 75115",
                    "issue_description": "no heat - heater not working at all",
                    "urgency": "emergency",
                    "property_type": "residential",
                    "system_type": "furnace",
                    "indoor_temperature_f": 54,  # Below 55°F threshold
                }
            }]
        }
    }


def check_result(result: dict) -> list[tuple[str, bool, str]]:
    """
    Validate the response against expected values.
    
    Returns:
        List of (check_name, passed, detail) tuples
    """
    checks = []
    data = result.get("data", {})
    
    # 1. Emergency detection
    is_emergency = data.get("is_emergency")
    checks.append((
        "Emergency detected",
        is_emergency is True,
        f"is_emergency={is_emergency}"
    ))
    
    # 2. Priority label
    priority_label = data.get("priority_label")
    checks.append((
        "Priority is CRITICAL",
        priority_label == "CRITICAL",
        f"priority_label={priority_label}"
    ))
    
    # 3. ETA window
    eta_min = data.get("eta_window_hours_min")
    eta_max = data.get("eta_window_hours_max")
    checks.append((
        "ETA window present",
        eta_min is not None and eta_max is not None,
        f"eta={eta_min}-{eta_max} hours"
    ))
    checks.append((
        "ETA window 1.5-3 hours",
        eta_min == 1.5 and eta_max == 3.0,
        f"expected 1.5-3.0, got {eta_min}-{eta_max}"
    ))
    
    # 4. Pricing
    pricing = data.get("pricing", {})
    checks.append((
        "Pricing present",
        bool(pricing),
        f"pricing keys: {list(pricing.keys()) if pricing else 'none'}"
    ))
    checks.append((
        "Total fee calculated",
        pricing.get("total_base_fee", 0) > 0,
        f"total_base_fee=${pricing.get('total_base_fee', 0):.2f}"
    ))
    
    # 5. Technician assignment (DeSoto should be Junior)
    tech = data.get("assigned_technician")
    checks.append((
        "Technician assigned",
        tech is not None,
        f"tech={tech.get('name') if tech else 'none'}"
    ))
    checks.append((
        "Junior assigned for DeSoto",
        tech and tech.get("id") == "junior",
        f"tech_id={tech.get('id') if tech else 'none'}"
    ))
    
    # 6. Odoo lead (if enabled)
    odoo = data.get("odoo", {})
    if odoo:
        checks.append((
            "Odoo lead created/updated",
            odoo.get("crm_lead_id") is not None,
            f"crm_lead_id={odoo.get('crm_lead_id')}, action={odoo.get('action')}"
        ))
    else:
        checks.append((
            "Odoo lead created/updated",
            None,  # Skipped
            "Odoo not configured or disabled"
        ))
    
    # 7. Response action
    action = result.get("action")
    checks.append((
        "Action is completed",
        action == "completed",
        f"action={action}"
    ))
    
    # 8. Speak message includes ETA and pricing
    speak = result.get("speak", "")
    has_eta_mention = "hour" in speak.lower()
    has_pricing_mention = "$" in speak
    checks.append((
        "Speak mentions ETA",
        has_eta_mention,
        f"speak contains 'hour': {has_eta_mention}"
    ))
    checks.append((
        "Speak mentions pricing",
        has_pricing_mention,
        f"speak contains '$': {has_pricing_mention}"
    ))
    
    return checks


def print_results(checks: list[tuple[str, bool, str]]) -> bool:
    """Print check results and return overall pass/fail."""
    print("\n" + "=" * 60)
    print("EMERGENCY FLOW VERIFICATION RESULTS")
    print("=" * 60)
    
    all_passed = True
    
    for name, passed, detail in checks:
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
    base_url = get_base_url()
    endpoint = f"{base_url}/vapi/server"
    
    print(f"Testing against: {endpoint}")
    print()
    
    payload = create_emergency_payload()
    print("Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        response = httpx.post(
            endpoint,
            json=payload,
            timeout=30.0,
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERROR: Non-200 response: {response.text}")
            return 1
        
        response_data = response.json()
        
        # Extract the tool result
        if "results" not in response_data or not response_data["results"]:
            print("ERROR: No results in response")
            return 1
        
        result_str = response_data["results"][0]["result"]
        result = json.loads(result_str)
        
        print("\nTool Result:")
        print(json.dumps(result, indent=2))
        
        # Run checks
        checks = check_result(result)
        all_passed = print_results(checks)
        
        return 0 if all_passed else 1
        
    except httpx.RequestError as e:
        print(f"ERROR: Request failed: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON response: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
