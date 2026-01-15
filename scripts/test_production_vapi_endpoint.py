"""
Test script to validate the production Vapi server endpoint.
"""

import asyncio
import httpx
import hmac
import hashlib
import json
import os
from dotenv import load_dotenv

load_dotenv()

PROD_URL = "https://haes-hvac.fly.dev/vapi/server"
VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")


def generate_vapi_signature(payload: str, secret: str) -> str:
    """Generate Vapi webhook signature."""
    if not secret:
        return ""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


async def test_production_endpoint():
    """Test the production /vapi/server endpoint with a create_service_request tool call."""
    
    # Sample tool-calls payload
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {
                "id": "test-call-123"
            },
            "toolWithToolCallList": [
                {
                    "name": "create_service_request",
                    "toolCall": {
                        "id": "test-tool-call-456",
                        "parameters": {
                            "customer_name": "John Doe",
                            "phone": "+1234567890",
                            "address": "123 Main St, Dallas, TX 75201",
                            "issue_description": "AC not working",
                            "urgency": "emergency",
                            "property_type": "residential"
                        }
                    }
                }
            ]
        }
    }
    
    payload_str = json.dumps(payload)
    signature = generate_vapi_signature(payload_str, VAPI_WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
    }
    
    if signature:
        headers["x-vapi-signature"] = signature
    
    print(f"Testing production endpoint: {PROD_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {headers}")
    print("-" * 80)
    
    async with httpx.AsyncClient(timeout=35.0) as client:
        try:
            response = await client.post(
                PROD_URL,
                json=payload,
                headers=headers,
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"Response Body: {json.dumps(response_data, indent=2)}")
            except Exception as e:
                print(f"Response Body (raw): {response.text}")
                print(f"Failed to parse JSON: {e}")
            
            if response.status_code == 200:
                print("\n✅ SUCCESS: Endpoint responded with 200")
            else:
                print(f"\n❌ ERROR: Endpoint returned {response.status_code}")
                
        except httpx.TimeoutException:
            print("\n❌ TIMEOUT: Request exceeded 35 seconds")
        except httpx.ReadTimeout:
            print("\n❌ READ TIMEOUT: Server took too long to respond")
        except Exception as e:
            print(f"\n❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_production_endpoint())
