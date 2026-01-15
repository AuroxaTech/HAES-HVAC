#!/usr/bin/env python3
"""
HAES HVAC - Add All Vapi Tools Script

This script reads all tool JSON schemas from doc/vapi/tools/ and creates/updates
them in Vapi. It also optionally attaches all tools to the assistant.

Usage:
    python scripts/add_vapi_tools.py [--attach-to-assistant] [--dry-run]

Requirements:
    - VAPI_API_KEY environment variable set
    - VAPI_WEBHOOK_SECRET environment variable set
    - VAPI_ASSISTANT_ID environment variable set (if using --attach-to-assistant)
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, but that's okay - user can export vars manually
    pass


# Configuration
VAPI_API_BASE = "https://api.vapi.ai"
SERVER_URL = "https://haes-hvac.fly.dev/vapi/server"
TOOLS_DIR = Path(__file__).parent.parent / "doc" / "vapi" / "tools"


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        print(f"Please set it in your .env file or export it")
        sys.exit(1)
    return value


def load_tool_schema(tool_path: Path) -> dict[str, Any] | None:
    """Load a tool schema from JSON file."""
    try:
        with open(tool_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {tool_path.name}: {e}")
        return None


def extract_tool_definition(schema: dict[str, Any], server_url: str = SERVER_URL) -> dict[str, Any] | None:
    """Extract tool definition from schema JSON."""
    tool_def = schema.get("tool_definition", {})
    if not tool_def:
        return None
    
    # Extract function name
    function = tool_def.get("function", {})
    tool_name = function.get("name")
    if not tool_name:
        return None
    
    # Build tool payload for Vapi API
    # Vapi expects: type, async, messages, function, server
    # Note: "name" is NOT included at top level - Vapi derives it from function.name
    payload = {
        "type": tool_def.get("type", "function"),
        "async": tool_def.get("async", False),
        "messages": tool_def.get("messages", [
            {"type": "request-start", "content": "Let me check that for you."},
            {"type": "request-complete", "content": ""},
            {"type": "request-failed", "content": "I'm having trouble processing that request. Let me try again."},
            {"type": "request-response-delayed", "content": "This is taking a moment. Please hold.", "timingMilliseconds": 3000}
        ]),
        "function": function,
        "server": {
            "url": server_url,
            "timeoutSeconds": 30
        }
    }
    
    return payload


def find_tool_by_name(api_key: str, tool_name: str) -> str | None:
    """Find a tool by name and return its ID."""
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
            if func.get("name") == tool_name or tool.get("name") == tool_name:
                return tool.get("id")
        return None
    except Exception as e:
        print(f"Warning: Could not list tools: {e}")
        return None


def create_tool(api_key: str, webhook_secret: str, tool_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Create a new tool in Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Add webhook secret to server config
    tool_payload["server"]["secret"] = webhook_secret
    
    url = f"{VAPI_API_BASE}/tool"
    
    try:
        response = httpx.post(url, headers=headers, json=tool_payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error creating tool: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error creating tool: {e}")
        return None


def update_tool(api_key: str, tool_id: str, webhook_secret: str, tool_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Update an existing tool in Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # For PATCH, only include fields that can be updated (not name/type)
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
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error updating tool: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error updating tool: {e}")
        return None


def get_assistant_tools(api_key: str, assistant_id: str) -> list[dict[str, Any]]:
    """Get current tools attached to assistant."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        assistant = response.json()
        model = assistant.get("model", {})
        if isinstance(model, dict):
            return model.get("tools", [])
        return []
    except Exception as e:
        print(f"Warning: Could not get assistant tools: {e}")
        return []


def attach_tools_to_assistant(api_key: str, assistant_id: str, tool_ids: list[str], server_url: str = SERVER_URL) -> bool:
    """Attach tools to assistant by replacing the tools array."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Get current assistant config
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        assistant = response.json()
    except Exception as e:
        print(f"Error: Could not get assistant config: {e}")
        return False
    
    # Get current model config
    model = assistant.get("model", {})
    if not isinstance(model, dict):
        print("Error: Assistant model config is not a dict")
        return False
    
    # Build tool definitions from tool IDs
    # We need to fetch each tool to get its full definition
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
                    "url": tool_data.get("server", {}).get("url", server_url),
                }
            }
            tool_definitions.append(tool_def)
        except Exception as e:
            print(f"Warning: Could not fetch tool {tool_id}: {e}")
            continue
    
    # Update assistant with new tools
    model["tools"] = tool_definitions
    payload = {"model": model}
    
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
    print("HAES HVAC - Add All Vapi Tools")
    print("=" * 60)
    print()
    
    parser = argparse.ArgumentParser(description="Add all Vapi tools from JSON schemas")
    parser.add_argument(
        "--attach-to-assistant",
        action="store_true",
        help="Attach all tools to the assistant (requires VAPI_ASSISTANT_ID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making API calls",
    )
    parser.add_argument(
        "--server-url",
        default=SERVER_URL,
        help=f"Server URL for tools (default: {SERVER_URL})",
    )
    args = parser.parse_args()
    
    # Use provided server URL or default
    server_url = args.server_url
    
    # Load environment variables
    api_key = get_env_var("VAPI_API_KEY")
    webhook_secret = get_env_var("VAPI_WEBHOOK_SECRET")
    assistant_id = None
    if args.attach_to_assistant:
        assistant_id = get_env_var("VAPI_ASSISTANT_ID")
    
    # Find all tool JSON files
    if not TOOLS_DIR.exists():
        print(f"Error: Tools directory not found: {TOOLS_DIR}")
        sys.exit(1)
    
    tool_files = sorted(TOOLS_DIR.glob("*.json"))
    if not tool_files:
        print(f"Error: No tool JSON files found in {TOOLS_DIR}")
        sys.exit(1)
    
    print(f"Found {len(tool_files)} tool schema files")
    print(f"Server URL: {server_url}")
    print()
    
    if args.dry_run:
        print("DRY RUN MODE - No API calls will be made")
        print()
    
    # Process each tool
    results = {
        "created": [],
        "updated": [],
        "failed": [],
        "skipped": [],
    }
    
    tool_ids = []
    
    for tool_file in tool_files:
        tool_name = tool_file.stem
        print(f"Processing: {tool_name}...")
        
        # Load schema
        schema = load_tool_schema(tool_file)
        if not schema:
            results["failed"].append((tool_name, "Failed to load schema"))
            print(f"  ❌ Failed to load schema")
            continue
        
        # Extract tool definition
        tool_payload = extract_tool_definition(schema, server_url)
        if not tool_payload:
            results["failed"].append((tool_name, "Invalid tool definition"))
            print(f"  ❌ Invalid tool definition")
            continue
        
        # Get tool name from function.name (not top-level name)
        function = tool_payload.get("function", {})
        tool_name_from_schema = function.get("name")
        if not tool_name_from_schema:
            results["failed"].append((tool_name, "Missing tool name in schema"))
            print(f"  ❌ Missing tool name")
            continue
        
        if args.dry_run:
            print(f"  [DRY RUN] Would create/update tool: {tool_name_from_schema}")
            tool_ids.append(f"DRY_RUN_{tool_name_from_schema}")
            results["skipped"].append(tool_name_from_schema)
            continue
        
        # Check if tool already exists
        existing_tool_id = find_tool_by_name(api_key, tool_name_from_schema)
        
        if existing_tool_id:
            # Update existing tool
            print(f"  Found existing tool: {existing_tool_id}")
            result = update_tool(api_key, existing_tool_id, webhook_secret, tool_payload)
            if result:
                tool_ids.append(existing_tool_id)
                results["updated"].append(tool_name_from_schema)
                print(f"  ✓ Updated successfully")
            else:
                results["failed"].append((tool_name_from_schema, "Update failed"))
                print(f"  ❌ Update failed")
        else:
            # Create new tool
            result = create_tool(api_key, webhook_secret, tool_payload)
            if result:
                new_tool_id = result.get("id")
                if new_tool_id:
                    tool_ids.append(new_tool_id)
                    results["created"].append(tool_name_from_schema)
                    print(f"  ✓ Created: {new_tool_id}")
                else:
                    results["failed"].append((tool_name_from_schema, "No ID in response"))
                    print(f"  ❌ Created but no ID returned")
            else:
                results["failed"].append((tool_name_from_schema, "Creation failed"))
                print(f"  ❌ Creation failed")
        
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total tools processed: {len(tool_files)}")
    print(f"Created: {len(results['created'])}")
    print(f"Updated: {len(results['updated'])}")
    print(f"Failed: {len(results['failed'])}")
    if args.dry_run:
        print(f"Skipped (dry run): {len(results['skipped'])}")
    print()
    
    if results["created"]:
        print("Created tools:")
        for name in results["created"]:
            print(f"  ✓ {name}")
        print()
    
    if results["updated"]:
        print("Updated tools:")
        for name in results["updated"]:
            print(f"  ✓ {name}")
        print()
    
    if results["failed"]:
        print("Failed tools:")
        for name, reason in results["failed"]:
            print(f"  ❌ {name}: {reason}")
        print()
    
    # Attach tools to assistant if requested
    if args.attach_to_assistant and not args.dry_run and tool_ids:
        print("=" * 60)
        print("Attaching Tools to Assistant")
        print("=" * 60)
        print()
        
        print(f"Attaching {len(tool_ids)} tools to assistant {assistant_id}...")
        success = attach_tools_to_assistant(api_key, assistant_id, tool_ids, server_url)
        
        if success:
            print("✓ Tools attached to assistant successfully")
        else:
            print("❌ Failed to attach tools to assistant")
            print("You may need to attach them manually in the Vapi dashboard")
        print()
    
    # Next steps
    print("=" * 60)
    print("Next Steps")
    print("=" * 60)
    print()
    
    if not args.dry_run:
        if args.attach_to_assistant:
            print("✓ Tools have been added and attached to the assistant")
        else:
            print("✓ Tools have been added to Vapi")
            print("To attach them to the assistant, run:")
            print("  python scripts/add_vapi_tools.py --attach-to-assistant")
        print()
        print("To verify:")
        print("1. Check Vapi dashboard: https://dashboard.vapi.ai")
        print("2. Test the assistant by making a call")
        print("3. Monitor logs: fly logs --app haes-hvac")
        print()
    else:
        print("This was a dry run. To actually add tools, run without --dry-run")
        print()


if __name__ == "__main__":
    main()
