#!/usr/bin/env python3
"""
HAES HVAC - Verify and Attach Tools to Assistants

This script verifies which tools are attached to each assistant and attaches any missing ones.

Usage:
    python scripts/verify_and_attach_tools.py [--fix]
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


def get_tool_by_name(api_key: str, tool_name: str) -> dict[str, Any] | None:
    """Get a tool by name from Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/tool"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        tools = response.json()
        
        for tool in tools:
            func = tool.get("function", {})
            if func.get("name") == tool_name:
                return tool
        return None
    except Exception as e:
        print(f"Warning: Could not list tools: {e}")
        return None


def load_tool_schemas(tools_dir: Path) -> list[dict[str, Any]]:
    """Load all tool JSON schemas from a directory."""
    schemas = []
    if not tools_dir.exists():
        return schemas
    
    for json_file in tools_dir.rglob("*.json"):
        try:
            with open(json_file, "r") as f:
                schema = json.load(f)
                tool_def = schema.get("tool_definition", {})
                function = tool_def.get("function", {})
                tool_name = function.get("name")
                if tool_name:
                    schemas.append({
                        "name": tool_name,
                        "file": str(json_file),
                        "schema": schema
                    })
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}")
    
    return schemas


def get_attached_tool_names(assistant: dict[str, Any]) -> set[str]:
    """Extract tool names from assistant configuration."""
    tool_names = set()
    model = assistant.get("model", {})
    if isinstance(model, dict):
        tools = model.get("tools", [])
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name")
            if name:
                tool_names.add(name)
    return tool_names


def attach_tools_to_assistant(api_key: str, assistant_id: str, tool_names: list[str], server_url: str = SERVER_URL) -> bool:
    """Attach tools to assistant by tool names."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Get current assistant config
    assistant = get_assistant(api_key, assistant_id)
    if not assistant:
        return False
    
    model = assistant.get("model", {})
    if not isinstance(model, dict):
        print("Error: Assistant model config is not a dict")
        return False
    
    # Build tool definitions from tool names
    tool_definitions = []
    for tool_name in tool_names:
        tool_data = get_tool_by_name(api_key, tool_name)
        if not tool_data:
            print(f"  ⚠️  Tool '{tool_name}' not found in Vapi - may need to be created")
            continue
        
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
        time.sleep(0.5)  # Rate limit protection
    
    if not tool_definitions:
        print("  ⚠️  No tool definitions to attach")
        return False
    
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


def verify_and_fix_assistant(
    api_key: str,
    assistant_id: str,
    assistant_name: str,
    expected_tools: list[str],
    fix: bool = False
):
    """Verify tools attached to assistant and optionally fix."""
    print(f"\n{'=' * 60}")
    print(f"Verifying {assistant_name}")
    print(f"{'=' * 60}")
    print(f"Assistant ID: {assistant_id}")
    
    # Get assistant config
    assistant = get_assistant(api_key, assistant_id)
    if not assistant:
        print(f"  ❌ Could not fetch assistant {assistant_id}")
        return
    
    # Get attached tools
    attached_tools = get_attached_tool_names(assistant)
    expected_set = set(expected_tools)
    
    print(f"\nExpected tools ({len(expected_tools)}):")
    for tool in sorted(expected_tools):
        status = "✅" if tool in attached_tools else "❌ MISSING"
        print(f"  {status} {tool}")
    
    print(f"\nAttached tools ({len(attached_tools)}):")
    for tool in sorted(attached_tools):
        if tool not in expected_set:
            print(f"  ⚠️  {tool} (unexpected - not in expected list)")
        else:
            print(f"  ✅ {tool}")
    
    # Find missing tools
    missing = expected_set - attached_tools
    extra = attached_tools - expected_set
    
    if missing:
        print(f"\n❌ Missing tools ({len(missing)}):")
        for tool in sorted(missing):
            print(f"  - {tool}")
    
    if extra:
        print(f"\n⚠️  Extra tools ({len(extra)}):")
        for tool in sorted(extra):
            print(f"  - {tool}")
    
    if not missing and not extra:
        print(f"\n✅ All tools correctly attached!")
        return
    
    # Fix if requested
    if fix and missing:
        print(f"\n🔧 Fixing: Attaching {len(missing)} missing tools...")
        if attach_tools_to_assistant(api_key, assistant_id, expected_tools, SERVER_URL):
            print(f"  ✅ Successfully attached all tools")
        else:
            print(f"  ❌ Failed to attach tools")
    elif fix:
        print(f"\n⚠️  No missing tools to fix")


def main():
    """Main verification function."""
    parser = argparse.ArgumentParser(description="Verify and fix tool attachments")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attach missing tools to assistants",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("HAES HVAC - Tool Attachment Verification")
    print("=" * 60)
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    
    project_root = Path(__file__).parent.parent
    
    # Load expected tools from JSON schemas
    customer_tools_dir = project_root / "doc" / "vapi" / "tools" / "customer_facing"
    internal_tools_dir = project_root / "doc" / "vapi" / "tools" / "internal_ops"
    
    customer_schemas = load_tool_schemas(customer_tools_dir)
    internal_schemas = load_tool_schemas(internal_tools_dir)
    
    customer_tool_names = [s["name"] for s in customer_schemas]
    internal_tool_names = [s["name"] for s in internal_schemas]
    
    print(f"\nLoaded tool schemas:")
    print(f"  Customer Facing: {len(customer_tool_names)} tools")
    print(f"  Internal OPS: {len(internal_tool_names)} tools")
    
    # Verify Riley Customer
    verify_and_fix_assistant(
        api_key=api_key,
        assistant_id=RILEY_CUSTOMER_ID,
        assistant_name="Riley Customer - Inbound",
        expected_tools=customer_tool_names,
        fix=args.fix
    )
    
    # Verify Riley OPS
    verify_and_fix_assistant(
        api_key=api_key,
        assistant_id=RILEY_OPS_ID,
        assistant_name="Riley OPS",
        expected_tools=internal_tool_names,
        fix=args.fix
    )
    
    print("\n" + "=" * 60)
    print("Verification Complete!")
    print("=" * 60)
    
    if args.fix:
        print("\n✅ Missing tools have been attached (if any were missing)")
    else:
        print("\n💡 To attach missing tools, run with --fix flag:")
        print("   python scripts/verify_and_attach_tools.py --fix")
    print()


if __name__ == "__main__":
    import argparse
    main()
