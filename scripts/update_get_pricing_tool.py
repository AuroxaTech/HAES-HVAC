#!/usr/bin/env python3
"""
Update get_pricing tool in Vapi with corrected schema.
"""

import json
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

VAPI_API_BASE = "https://api.vapi.ai"
SERVER_URL = "https://haes-hvac.fly.dev/vapi/server"
TOOL_SCHEMA_PATH = Path(__file__).parent.parent / "doc" / "vapi" / "tools" / "static" / "get_pricing.json"

def get_env_var(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} not set")
        sys.exit(1)
    return value

def load_tool_schema() -> dict:
    with open(TOOL_SCHEMA_PATH) as f:
        return json.load(f)

def extract_tool_definition(schema: dict) -> dict:
    tool_def = schema.get("tool_definition", {})
    if not tool_def:
        return None
    
    function = tool_def.get("function", {})
    if not function:
        return None
    
    return {
        "type": tool_def.get("type", "function"),
        "async": tool_def.get("async", False),
        "messages": tool_def.get("messages", []),
        "function": function,
        "server": {
            "url": tool_def.get("server", {}).get("url", SERVER_URL),
            "timeoutSeconds": 30,
        }
    }

def find_tool_by_name(api_key: str, tool_name: str) -> str | None:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/tool"
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        tools = response.json()
        if isinstance(tools, list):
            for tool in tools:
                if tool.get("function", {}).get("name") == tool_name:
                    return tool.get("id")
        return None
    except Exception as e:
        print(f"Error finding tool: {e}")
        return None

def update_tool(api_key: str, tool_id: str, webhook_secret: str, tool_payload: dict) -> bool:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "async": tool_payload.get("async", False),
        "messages": tool_payload.get("messages", []),
        "function": tool_payload.get("function", {}),
        "server": {
            **tool_payload.get("server", {}),
            "secret": webhook_secret,
        },
    }
    
    url = f"{VAPI_API_BASE}/tool/{tool_id}"
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        print(f"✅ Successfully updated tool: {tool_payload['function']['name']}")
        return True
    except httpx.HTTPStatusError as e:
        print(f"❌ Error updating tool: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Error updating tool: {e}")
        return False

def main():
    print("Updating get_pricing tool in Vapi...")
    
    api_key = get_env_var("VAPI_API_KEY")
    webhook_secret = get_env_var("VAPI_WEBHOOK_SECRET")
    
    # Load schema
    schema = load_tool_schema()
    tool_payload = extract_tool_definition(schema)
    
    if not tool_payload:
        print("❌ Failed to extract tool definition")
        sys.exit(1)
    
    tool_name = tool_payload["function"]["name"]
    print(f"Tool name: {tool_name}")
    
    # Find existing tool
    tool_id = find_tool_by_name(api_key, tool_name)
    if not tool_id:
        print(f"❌ Tool '{tool_name}' not found in Vapi")
        sys.exit(1)
    
    print(f"Found tool ID: {tool_id}")
    
    # Update tool
    success = update_tool(api_key, tool_id, webhook_secret, tool_payload)
    
    if success:
        print("\n✅ Tool updated successfully!")
        print(f"Verify at: https://dashboard.vapi.ai/tools/{tool_id}")
    else:
        print("\n❌ Failed to update tool")
        sys.exit(1)

if __name__ == "__main__":
    main()
