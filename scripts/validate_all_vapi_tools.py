#!/usr/bin/env python3
"""
Validate all Vapi tools with production URL.
Tests each tool one by one to ensure they work correctly.
"""

import json
import time
import subprocess
from typing import Any

PROD_URL = "https://haes-hvac.fly.dev/vapi/server"

# Test parameters for each tool
TOOL_TEST_PARAMS = {
    # OPS tools
    "create_service_request": {
        "phone": "+1234567890",
        "address": "123 Main St, Dallas, TX 75201",
        "issue_description": "AC not working",
        "urgency": "high",
        "customer_name": "Test Customer",
        "property_type": "residential"
    },
    "schedule_appointment": {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "address": "123 Main St, Dallas, TX 75201",
        "preferred_date": "2026-01-20",
        "preferred_time": "10:00",
        "service_type": "Maintenance"
    },
    "check_availability": {
        "date": "2026-01-20",
        "time_slot": "10:00-12:00"
    },
    "reschedule_appointment": {
        "appointment_id": "test-apt-123",
        "new_date": "2026-01-21",
        "new_time": "14:00",
        "customer_name": "Test Customer",
        "phone": "+1234567890"
    },
    "cancel_appointment": {
        "appointment_id": "test-apt-123",
        "customer_name": "Test Customer",
        "phone": "+1234567890"
    },
    "check_appointment_status": {
        "appointment_id": "test-apt-123",
        "customer_name": "Test Customer",
        "phone": "+1234567890"
    },
    
    # REVENUE tools
    "request_quote": {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "email": "test@example.com",
        "address": "123 Main St, Dallas, TX 75201",
        "property_type": "residential",
        "square_footage": 2000,
        "system_age_years": 10,
        "service_type": "Installation"
    },
    "check_lead_status": {
        "lead_id": "2702",
        "customer_name": "Test Customer",
        "phone": "+1234567890"
    },
    "request_membership_enrollment": {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "email": "test@example.com",
        "address": "123 Main St, Dallas, TX 75201",
        "property_type": "residential"
    },
    
    # CORE tools
    "billing_inquiry": {
        "customer_name": "Test Customer",
        "phone": "+1234567890"
    },
    "payment_terms_inquiry": {
        "customer_name": "Test Customer",
        "phone": "+1234567890"
    },
    "invoice_request": {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "email": "test@example.com"
    },
    "inventory_inquiry": {
        "part_name": "Air Filter",
        "quantity": 1
    },
    "purchase_request": {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "part_name": "Air Filter",
        "quantity": 1
    },
    "get_pricing": {
        "service_type": "Diagnostic",
        "property_type": "residential",
        "is_emergency": False
    },
    "create_complaint": {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "complaint_description": "Service was unsatisfactory",
        "service_id": "test-service-123"
    },
    
    # PEOPLE tools
    "hiring_inquiry": {
        "inquiry_type": "application_status",
        "applicant_name": "John Doe",
        "applicant_email": "john@example.com"
    },
    "onboarding_inquiry": {
        "employee_name": "John Doe",
        "employee_email": "john@example.com",
        "inquiry_type": "documents"
    },
    "payroll_inquiry": {
        "employee_name": "John Doe",
        "employee_id": "EMP001",
        "inquiry_type": "pay_stub"
    },
    
    # UTILS tools
    "check_business_hours": {},
    "get_service_area_info": {},
    "get_maintenance_plans": {
        "property_type": "residential"
    }
}


def test_tool(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Test a single tool with the production URL."""
    print(f"\n{'='*80}")
    print(f"Testing: {tool_name}")
    print(f"{'='*80}")
    
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {"id": f"test-call-{tool_name}-{int(time.time())}"},
            "toolWithToolCallList": [{
                "name": tool_name,
                "toolCall": {
                    "id": f"test-tool-call-{tool_name}-{int(time.time())}",
                    "parameters": parameters
                }
            }]
        }
    }
    
    print(f"Parameters: {json.dumps(parameters, indent=2)}")
    
    # Use curl to test
    payload_json = json.dumps(payload)
    
    cmd = [
        "curl",
        "-X", "POST",
        PROD_URL,
        "-H", "Content-Type: application/json",
        "-d", payload_json,
        "--max-time", "35",
        "-s",  # Silent mode
        "-w", "\nHTTP_CODE:%{http_code}\nTIME:%{time_total}\n"  # Get status code and time
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=40
        )
        
        # Parse output
        output = result.stdout
        stderr = result.stderr
        
        # Extract HTTP code and time from output
        http_code = None
        response_time = None
        
        if "HTTP_CODE:" in output:
            lines = output.split("\n")
            for line in lines:
                if line.startswith("HTTP_CODE:"):
                    http_code = int(line.split(":")[1])
                elif line.startswith("TIME:"):
                    response_time = float(line.split(":")[1])
        
        # Extract JSON response (everything before HTTP_CODE)
        json_output = output.split("HTTP_CODE:")[0].strip()
        
        try:
            response_data = json.loads(json_output) if json_output else {}
        except json.JSONDecodeError:
            response_data = {"raw_response": json_output}
        
        result_info = {
            "tool_name": tool_name,
            "http_code": http_code,
            "response_time": response_time,
            "response": response_data,
            "success": http_code == 200,
            "error": stderr if stderr else None
        }
        
        # Print results
        if http_code == 200:
            print(f"✅ SUCCESS - Status: {http_code}, Time: {response_time:.2f}s")
            if "results" in response_data and response_data["results"]:
                result_obj = json.loads(response_data["results"][0].get("result", "{}"))
                print(f"   Action: {result_obj.get('action', 'unknown')}")
                print(f"   Speak: {result_obj.get('speak', '')[:100]}...")
            else:
                print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
        else:
            print(f"❌ FAILED - Status: {http_code}, Time: {response_time:.2f}s" if response_time else f"❌ FAILED - Status: {http_code}")
            if json_output:
                print(f"   Response: {json_output[:300]}...")
            if stderr:
                print(f"   Error: {stderr[:200]}...")
        
        return result_info
        
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT - Request exceeded 40 seconds")
        return {
            "tool_name": tool_name,
            "success": False,
            "error": "Timeout"
        }
    except Exception as e:
        print(f"❌ ERROR - {type(e).__name__}: {e}")
        return {
            "tool_name": tool_name,
            "success": False,
            "error": str(e)
        }


def main():
    """Test all tools one by one."""
    print("="*80)
    print("VAPI TOOLS VALIDATION - PRODUCTION URL")
    print("="*80)
    print(f"Testing against: {PROD_URL}")
    print(f"Total tools to test: {len(TOOL_TEST_PARAMS)}")
    print("="*80)
    
    results = []
    
    # Test each tool
    for tool_name, parameters in TOOL_TEST_PARAMS.items():
        result = test_tool(tool_name, parameters)
        results.append(result)
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"   - {r['tool_name']} ({r.get('response_time', 0):.2f}s)")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"   - {r['tool_name']}: {r.get('error', 'Unknown error')}")
    
    print("\n" + "="*80)
    
    # Save results to file
    with open("tool_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: tool_validation_results.json")
    
    return len(failed) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
