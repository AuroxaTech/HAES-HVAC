#!/usr/bin/env python3
"""
Simple script to update get_pricing tool in Vapi with corrected schema.
"""

import json
import os
import sys
import subprocess
from pathlib import Path

# Try to load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

VAPI_API_BASE = "https://api.vapi.ai"
TOOL_SCHEMA_PATH = Path(__file__).parent.parent / "doc" / "vapi" / "tools" / "static" / "get_pricing.json"

def get_env_var(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} not set")
        sys.exit(1)
    return value

def main():
    print("=" * 60)
    print("Updating get_pricing tool in Vapi")
    print("=" * 60)
    print()
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    webhook_secret = get_env_var("VAPI_WEBHOOK_SECRET")
    
    # Load schema
    print("Loading schema...")
    with open(TOOL_SCHEMA_PATH) as f:
        schema = json.load(f)
    
    tool_def = schema.get("tool_definition", {})
    function = tool_def.get("function", {})
    
    # Build update payload
    payload = {
        "async": tool_def.get("async", False),
        "messages": tool_def.get("messages", [
            {"type": "request-start", "content": "Let me check that for you."},
            {"type": "request-complete", "content": ""},
            {"type": "request-failed", "content": "I'm having trouble processing that request. Let me try again."},
            {"type": "request-response-delayed", "content": "This is taking a moment. Please hold.", "timingMilliseconds": 3000}
        ]),
        "function": function,
        "server": {
            "url": tool_def.get("server", {}).get("url", "https://haes-hvac.fly.dev/vapi/server"),
            "timeoutSeconds": 30,
            "secret": webhook_secret
        }
    }
    
    # Find tool ID using curl
    print("Finding tool ID...")
    find_cmd = [
        "curl", "-s", "-X", "GET", f"{VAPI_API_BASE}/tool",
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json"
    ]
    
    try:
        result = subprocess.run(find_cmd, capture_output=True, text=True, check=True)
        tools = json.loads(result.stdout)
        
        tool_id = None
        for tool in tools:
            func = tool.get("function", {})
            if func.get("name") == "get_pricing":
                tool_id = tool.get("id")
                break
        
        if not tool_id:
            print("❌ Tool 'get_pricing' not found in Vapi")
            sys.exit(1)
        
        print(f"Found tool ID: {tool_id}")
        print()
        
        # Update tool using curl
        print("Updating tool...")
        update_cmd = [
            "curl", "-s", "-w", "\nHTTP_STATUS:%{http_code}",
            "-X", "PATCH", f"{VAPI_API_BASE}/tool/{tool_id}",
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload)
        ]
        
        result = subprocess.run(update_cmd, capture_output=True, text=True, check=True)
        
        # Parse response
        lines = result.stdout.strip().split('\n')
        http_status = None
        body = ""
        
        for line in lines:
            if line.startswith("HTTP_STATUS:"):
                http_status = int(line.split(":")[1])
            else:
                body += line + "\n"
        
        body = body.strip()
        
        if http_status in [200, 201]:
            print("✅ Successfully updated get_pricing tool!")
            print(f"Tool ID: {tool_id}")
            print()
            print(f"Verify at: https://dashboard.vapi.ai/tools/{tool_id}")
        else:
            print(f"❌ Error updating tool: HTTP {http_status}")
            print(f"Response: {body}")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error calling Vapi API: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing response: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
