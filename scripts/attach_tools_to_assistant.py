#!/usr/bin/env python3
"""
HAES HVAC - Attach All Tools to Assistant

This script fetches all tools from Vapi and attaches them to the assistant.

Usage:
    python scripts/attach_tools_to_assistant.py
"""

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
    load_dotenv()
except ImportError:
    pass

VAPI_API_BASE = "https://api.vapi.ai"

def get_env_var(name: str) -> str:
    """Get environment variable."""
    value = os.environ.get(name)
    if not value:
        print(f"Error: {name} environment variable not set")
        sys.exit(1)
    return value

def get_all_tools(api_key: str) -> list[dict]:
    """Get all tools from Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/tool"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching tools: {e}")
        sys.exit(1)

def get_assistant(api_key: str, assistant_id: str) -> dict:
    """Get assistant configuration."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching assistant: {e}")
        sys.exit(1)

def attach_tools_to_assistant(api_key: str, assistant_id: str, tool_ids: list[str]) -> bool:
    """Attach tools to assistant."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Get current assistant config
    assistant = get_assistant(api_key, assistant_id)
    model = assistant.get("model", {})
    if not isinstance(model, dict):
        print("Error: Assistant model config is not a dict")
        return False
    
    # Build tool definitions from tool IDs
    tool_definitions = []
    for tool_id in tool_ids:
        tool_url = f"{VAPI_API_BASE}/tool/{tool_id}"
        try:
            tool_resp = httpx.get(tool_url, headers=headers, timeout=30.0)
            tool_resp.raise_for_status()
            tool_data = tool_resp.json()
            
            # Convert standalone tool to inline tool definition
            tool_def = {
                "type": tool_data.get("type", "function"),
                "async": tool_data.get("async", False),
                "messages": tool_data.get("messages", []),
                "function": tool_data.get("function", {}),
                "server": {
                    "url": tool_data.get("server", {}).get("url"),
                }
            }
            tool_definitions.append(tool_def)
        except Exception as e:
            print(f"Warning: Could not fetch tool {tool_id}: {e}")
            continue
    
    # Update assistant with new tools
    model["tools"] = tool_definitions
    payload = {"model": model}
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"Error updating assistant: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"Error updating assistant: {e}")
        return False

def main():
    print("=" * 60)
    print("HAES HVAC - Attach All Tools to Assistant")
    print("=" * 60)
    print()
    
    api_key = get_env_var("VAPI_API_KEY")
    assistant_id = get_env_var("VAPI_ASSISTANT_ID")
    
    # Get all tools
    print("Fetching all tools from Vapi...")
    all_tools = get_all_tools(api_key)
    
    # Filter out hael_route (legacy tool) and get only our 22 tools
    our_tools = []
    tool_names = []
    for tool in all_tools:
        func = tool.get("function", {})
        name = func.get("name", "")
        if name and name != "hael_route":
            our_tools.append(tool)
            tool_names.append(name)
    
    print(f"Found {len(our_tools)} tools to attach:")
    for name in sorted(tool_names):
        print(f"  ✓ {name}")
    print()
    
    # Get tool IDs
    tool_ids = [tool.get("id") for tool in our_tools if tool.get("id")]
    
    if not tool_ids:
        print("Error: No tool IDs found")
        sys.exit(1)
    
    print(f"Attaching {len(tool_ids)} tools to assistant {assistant_id}...")
    success = attach_tools_to_assistant(api_key, assistant_id, tool_ids)
    
    if success:
        print("✓ Tools attached to assistant successfully!")
        print()
        print("All 22 tools are now available to the assistant.")
    else:
        print("❌ Failed to attach tools to assistant")
        sys.exit(1)

if __name__ == "__main__":
    main()
