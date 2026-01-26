#!/usr/bin/env python3
"""
HAES HVAC - Force Re-attach All Tools to Assistants

This script forces re-attachment of all tools to ensure they're properly linked.

Usage:
    python scripts/force_reattach_all_tools.py
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

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


# Configuration
VAPI_API_BASE = "https://api.vapi.ai"
SERVER_URL = "https://haes-hvac.fly.dev/vapi/server"

# Assistant IDs
RILEY_CUSTOMER_ID = os.environ.get("VAPI_ASSISTANT_ID") or "f639ba5f-7c38-4949-9479-ec2a40428d76"
RILEY_OPS_ID = os.environ.get("VAPI_RILEY_TECH_ASSISTANT_ID") or os.environ.get("VAPI_OPS_ASSISTANT_ID") or "fd35b574-1a9c-4052-99d8-a820e0ebabf7"


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        sys.exit(1)
    return value


def get_all_tools(api_key: str) -> dict[str, dict[str, Any]]:
    """Get all tools from Vapi and return as dict by tool name."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/tool"
    
    tools_by_name = {}
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        tools = response.json()
        
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name")
            if name:
                tools_by_name[name] = tool
        
        return tools_by_name
    except Exception as e:
        print(f"Error fetching tools: {e}")
        return {}


def get_assistant(api_key: str, assistant_id: str) -> dict[str, Any]:
    """Get assistant configuration from Vapi."""
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
        return {}


def load_tool_names_from_schemas(tools_dir: Path) -> list[str]:
    """Load tool names from JSON schemas."""
    tool_names = []
    if not tools_dir.exists():
        return tool_names
    
    for json_file in tools_dir.rglob("*.json"):
        try:
            with open(json_file, "r") as f:
                schema = json.load(f)
                tool_def = schema.get("tool_definition", {})
                function = tool_def.get("function", {})
                tool_name = function.get("name")
                if tool_name:
                    tool_names.append(tool_name)
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}")
    
    return sorted(tool_names)


def attach_tools_to_assistant(
    api_key: str,
    assistant_id: str,
    assistant_name: str,
    tool_names: list[str],
    all_tools: dict[str, dict[str, Any]],
    server_url: str = SERVER_URL
) -> bool:
    """Force attach all tools to assistant."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    print(f"\n{'=' * 60}")
    print(f"Re-attaching tools to {assistant_name}")
    print(f"{'=' * 60}")
    print(f"Assistant ID: {assistant_id}")
    print(f"Tools to attach: {len(tool_names)}")
    
    # Get current assistant config
    assistant = get_assistant(api_key, assistant_id)
    if not assistant:
        print(f"  ❌ Could not fetch assistant")
        return False
    
    model = assistant.get("model", {})
    if not isinstance(model, dict):
        print("  ❌ Assistant model config is not a dict")
        return False
    
    # Build tool definitions from tool names
    tool_definitions = []
    missing_tools = []
    
    print(f"\n  Fetching tool definitions...")
    for i, tool_name in enumerate(tool_names, 1):
        print(f"    [{i}/{len(tool_names)}] {tool_name}...", end=" ")
        
        if tool_name not in all_tools:
            print("❌ NOT FOUND IN VAPI")
            missing_tools.append(tool_name)
            continue
        
        tool_data = all_tools[tool_name]
        
        # Convert standalone tool to inline tool definition
        tool_def = {
            "type": tool_data.get("type", "function"),
            "async": tool_data.get("async", False),
            "messages": tool_data.get("messages", []),
            "function": tool_data.get("function", {}),
            "server": {
                "url": tool_data.get("server", {}).get("url", server_url),
            }
        }
        tool_definitions.append(tool_def)
        print("✅")
        time.sleep(1.0)  # Rate limit protection
    
    if missing_tools:
        print(f"\n  ⚠️  {len(missing_tools)} tools not found in Vapi:")
        for tool in missing_tools:
            print(f"    - {tool}")
        print(f"  Run configure_vapi_assistants.py to create these tools first")
    
    if not tool_definitions:
        print("  ❌ No tool definitions to attach")
        return False
    
    print(f"\n  Attaching {len(tool_definitions)} tools to assistant...")
    # Update assistant with new tools
    model["tools"] = tool_definitions
    payload = {"model": model}
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        print(f"  ✅ Successfully attached {len(tool_definitions)} tools!")
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            print(f"  ⏳ Rate limited. Please wait 60 seconds and retry.")
            print(f"  Response: {e.response.text}")
        else:
            print(f"  ❌ Error: HTTP {e.response.status_code}")
            print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("HAES HVAC - Force Re-attach All Tools")
    print("=" * 60)
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    
    project_root = Path(__file__).parent.parent
    
    # Load expected tools from JSON schemas
    customer_tools_dir = project_root / "doc" / "vapi" / "tools" / "customer_facing"
    internal_tools_dir = project_root / "doc" / "vapi" / "tools" / "internal_ops"
    
    customer_tool_names = load_tool_names_from_schemas(customer_tools_dir)
    internal_tool_names = load_tool_names_from_schemas(internal_tools_dir)
    
    print(f"\nExpected tools:")
    print(f"  Customer Facing: {len(customer_tool_names)} tools")
    print(f"  Internal OPS: {len(internal_tool_names)} tools")
    
    # Get all tools from Vapi
    print(f"\nFetching all tools from Vapi...")
    all_tools = get_all_tools(api_key)
    print(f"  Found {len(all_tools)} tools in Vapi")
    
    # Re-attach to Riley Customer
    success_customer = attach_tools_to_assistant(
        api_key=api_key,
        assistant_id=RILEY_CUSTOMER_ID,
        assistant_name="Riley Customer - Inbound",
        tool_names=customer_tool_names,
        all_tools=all_tools,
        server_url=SERVER_URL
    )
    
    # Wait to avoid rate limits
    if success_customer:
        print(f"\n⏳ Waiting 30 seconds before attaching to Riley OPS...")
        time.sleep(30)
    
    # Re-attach to Riley OPS
    success_ops = attach_tools_to_assistant(
        api_key=api_key,
        assistant_id=RILEY_OPS_ID,
        assistant_name="Riley OPS",
        tool_names=internal_tool_names,
        all_tools=all_tools,
        server_url=SERVER_URL
    )
    
    print("\n" + "=" * 60)
    print("Re-attachment Complete!")
    print("=" * 60)
    
    if success_customer and success_ops:
        print("\n✅ All tools successfully re-attached to both assistants!")
    elif success_customer:
        print("\n✅ Riley Customer tools re-attached")
        print("⚠️  Riley OPS tools need to be retried (rate limited)")
    elif success_ops:
        print("\n✅ Riley OPS tools re-attached")
        print("⚠️  Riley Customer tools need to be retried (rate limited)")
    else:
        print("\n⚠️  Some tools failed to attach due to rate limits")
        print("   Please wait 60 seconds and run again")
    
    print()


if __name__ == "__main__":
    main()
