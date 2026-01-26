#!/usr/bin/env python3
"""
HAES HVAC - Vapi Assistants Configuration Script

This script configures both Vapi assistants:
- "Riley Customer - Inbound" (Customer Line) - Customer-facing tools
  Assistant ID: fd35b574-1a9c-4052-99d8-a820e0ebabf7
  Phone: +1-972-597-1644 (8x8 forwarded)
  
- "Riley OPS" (Internal OPS Line) - Internal employee tools
  Assistant ID: (provided via VAPI_RILEY_TECH_ASSISTANT_ID or created)
  Phone: +1-855-768-3265 (Twilio)

Usage:
    python scripts/configure_vapi_assistants.py [--update-riley] [--update-riley-tech] [--dry-run]

Requirements:
    - VAPI_API_KEY environment variable set
    - VAPI_WEBHOOK_SECRET environment variable set
    - VAPI_ASSISTANT_ID (optional, defaults to fd35b574-1a9c-4052-99d8-a820e0ebabf7 for Riley Customer)
    - VAPI_RILEY_TECH_ASSISTANT_ID or VAPI_OPS_ASSISTANT_ID (optional, for Riley OPS)
"""

import json
import os
import sys
import argparse
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

# Phone numbers
CUSTOMER_LINE = "+19725971644"  # 8x8 forwarded
INTERNAL_OPS_LINE = "+18557683265"  # Twilio


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        sys.exit(1)
    return value


def load_system_prompt(prompt_path: Path) -> str:
    """Load system prompt from file."""
    if not prompt_path.exists():
        print(f"Error: System prompt not found at {prompt_path}")
        sys.exit(1)
    
    with open(prompt_path, "r") as f:
        return f.read()


def load_tool_schema(tool_path: Path) -> dict[str, Any] | None:
    """Load a tool schema from JSON file."""
    try:
        with open(tool_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {tool_path.name}: {e}")
        return None


def extract_tool_definition(schema: dict[str, Any], server_url: str = SERVER_URL) -> dict[str, Any] | None:
    """Extract tool definition from schema JSON (matches add_vapi_tools.py pattern)."""
    tool_def = schema.get("tool_definition", {})
    if not tool_def:
        return None
    
    # Extract function name
    function = tool_def.get("function", {})
    tool_name = function.get("name")
    if not tool_name:
        return None
    
    # Build tool payload for Vapi API (matches add_vapi_tools.py pattern)
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


def get_assistant(api_key: str, assistant_id: str) -> dict[str, Any]:
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
        return {}


def attach_tools_to_assistant(api_key: str, assistant_id: str, tool_ids: list[str], server_url: str = SERVER_URL) -> bool:
    """Attach tools to assistant by replacing the tools array (matches attach_tools_to_assistant.py pattern)."""
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
    
    # Build tool definitions from tool IDs (fetch each tool to get full definition)
    tool_definitions = []
    for tool_id in tool_ids:
        # Skip dry-run placeholders
        if isinstance(tool_id, str) and tool_id.startswith("DRY_RUN_"):
            continue
            
        tool_url = f"{VAPI_API_BASE}/tool/{tool_id}"
        try:
            tool_resp = httpx.get(tool_url, headers=headers, timeout=30.0)
            tool_resp.raise_for_status()
            tool_data = tool_resp.json()
            
            # Convert standalone tool to inline tool definition (matches attach_tools_to_assistant.py)
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
    
    if not tool_definitions:
        print("Warning: No tool definitions to attach")
        return False
    
    # Update assistant with new tools (preserve existing model config)
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


def update_assistant_system_prompt(api_key: str, assistant_id: str, system_prompt: str) -> bool:
    """Update assistant system prompt (matches configure_vapi_assistant.py pattern)."""
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
    
    # Update system message (preserve existing model config)
    messages = model.get("messages", [])
    # Find and update system message, or add new one
    system_message_updated = False
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            messages[i] = {"role": "system", "content": system_prompt}
            system_message_updated = True
            break
    
    if not system_message_updated:
        messages.insert(0, {"role": "system", "content": system_prompt})
    
    model["messages"] = messages
    payload = {"model": model}
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"Error updating assistant system prompt: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"Error updating assistant system prompt: {e}")
        return False


def process_tools_from_directory(
    api_key: str,
    webhook_secret: str,
    tools_dir: Path,
    dry_run: bool = False,
) -> list[str]:
    """Process all tool JSON files from a directory and return tool IDs."""
    if not tools_dir.exists():
        print(f"Warning: Tools directory not found: {tools_dir}")
        return []
    
    # Recursively find all JSON files (matches add_vapi_tools.py pattern)
    tool_files = sorted(tools_dir.rglob("*.json"))
    if not tool_files:
        print(f"Warning: No tool JSON files found in {tools_dir}")
        return []
    
    print(f"  Found {len(tool_files)} tool schema files")
    
    tool_ids = []
    
    for tool_file in tool_files:
        tool_name = tool_file.stem
        print(f"  Processing: {tool_name}...")
        
        # Load schema
        schema = load_tool_schema(tool_file)
        if not schema:
            print(f"    ❌ Failed to load schema")
            continue
        
        # Extract tool definition
        tool_payload = extract_tool_definition(schema, SERVER_URL)
        if not tool_payload:
            print(f"    ❌ Invalid tool definition")
            continue
        
        # Get tool name from function.name
        function = tool_payload.get("function", {})
        tool_name_from_schema = function.get("name")
        if not tool_name_from_schema:
            print(f"    ❌ Missing tool name")
            continue
        
        if dry_run:
            print(f"    [DRY RUN] Would create/update: {tool_name_from_schema}")
            tool_ids.append(f"DRY_RUN_{tool_name_from_schema}")
            continue
        
        # Check if tool already exists
        existing_tool_id = find_tool_by_name(api_key, tool_name_from_schema)
        
        if existing_tool_id:
            # Update existing tool
            result = update_tool(api_key, existing_tool_id, webhook_secret, tool_payload)
            if result:
                tool_ids.append(existing_tool_id)
                print(f"    ✓ Updated: {tool_name_from_schema}")
            else:
                print(f"    ❌ Update failed")
            # Add delay to avoid rate limits (1 second between tool updates)
            time.sleep(1.0)
        else:
            # Create new tool
            result = create_tool(api_key, webhook_secret, tool_payload)
            if result:
                new_tool_id = result.get("id")
                if new_tool_id:
                    tool_ids.append(new_tool_id)
                    print(f"    ✓ Created: {tool_name_from_schema} ({new_tool_id})")
                else:
                    print(f"    ❌ Created but no ID returned")
            else:
                print(f"    ❌ Creation failed")
            # Add delay to avoid rate limits (1 second between tool creations)
            time.sleep(1.0)
    
    return tool_ids


def configure_assistant(
    api_key: str,
    webhook_secret: str,
    assistant_id: str | None,
    assistant_name: str,
    system_prompt_path: Path,
    tools_dir: Path,
    create_new: bool = False,
    dry_run: bool = False,
) -> str | None:
    """Configure an assistant with system prompt and tools."""
    print(f"\n{'=' * 60}")
    print(f"Configuring {assistant_name}")
    print(f"{'=' * 60}")
    
    # Load system prompt
    print(f"\n[1/3] Loading system prompt...")
    system_prompt = load_system_prompt(system_prompt_path)
    print(f"      Loaded {len(system_prompt)} characters")
    
    # Process tools
    print(f"\n[2/3] Processing tools from {tools_dir.name}...")
    tool_ids = process_tools_from_directory(api_key, webhook_secret, tools_dir, dry_run)
    print(f"      Processed {len(tool_ids)} tools")
    
    if not assistant_id and not create_new:
        print(f"\n[3/3] Skipping assistant update (no assistant ID provided)")
        print(f"      To create assistant, set create_new=True or provide assistant ID")
        return None
    
    if dry_run:
        print(f"\n[3/3] [DRY RUN] Would configure assistant")
        return None
    
    # Get or create assistant
    if not assistant_id:
        # Create new assistant
        print(f"\n[3/3] Creating new assistant: {assistant_name}...")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "name": assistant_name,
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": system_prompt}
                ],
                "tools": []
            },
            "serverUrl": SERVER_URL,
            "serverUrlSecret": webhook_secret,
            "serverMessages": [
                "tool-calls",
                "transfer-destination-request",
                "end-of-call-report",
                "status-update",
                "conversation-update"
            ]
        }
        
        url = f"{VAPI_API_BASE}/assistant"
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            assistant_data = response.json()
            assistant_id = assistant_data.get("id")
            print(f"      ✓ Created assistant: {assistant_id}")
        except Exception as e:
            print(f"      ❌ Failed to create assistant: {e}")
            return None
    else:
        print(f"\n[3/3] Updating assistant: {assistant_id}...")
    
    # Update system prompt
    print(f"      Updating system prompt...")
    if update_assistant_system_prompt(api_key, assistant_id, system_prompt):
        print(f"      ✓ System prompt updated")
    else:
        print(f"      ⚠ System prompt update failed")
    
    # Attach tools
    if tool_ids:
        print(f"      Attaching {len(tool_ids)} tools...")
        if attach_tools_to_assistant(api_key, assistant_id, tool_ids, SERVER_URL):
            print(f"      ✓ Tools attached")
        else:
            print(f"      ⚠ Tools attachment failed")
    
    print(f"\n      ✅ {assistant_name} configuration complete!")
    return assistant_id


def main():
    """Main configuration function."""
    parser = argparse.ArgumentParser(description="Configure Vapi assistants (Riley and Riley Tech)")
    parser.add_argument(
        "--update-riley",
        action="store_true",
        help="Update Riley assistant (Customer Line)",
    )
    parser.add_argument(
        "--update-riley-tech",
        action="store_true",
        help="Update/create Riley Tech assistant (Internal OPS Line)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making API calls",
    )
    args = parser.parse_args()
    
    # Default: update both if no flags specified
    if not args.update_riley and not args.update_riley_tech:
        args.update_riley = True
        args.update_riley_tech = True
    
    print("=" * 60)
    print("HAES HVAC - Vapi Assistants Configuration")
    print("=" * 60)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No API calls will be made")
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    webhook_secret = get_env_var("VAPI_WEBHOOK_SECRET")
    
    # Assistant IDs from Vapi dashboard
    # Riley Customer - Inbound: fd35b574-1a9c-4052-99d8-a820e0ebabf7 (or from env)
    # Riley OPS: (from env var VAPI_RILEY_TECH_ASSISTANT_ID or VAPI_OPS_ASSISTANT_ID)
    riley_assistant_id = os.environ.get("VAPI_ASSISTANT_ID") or "fd35b574-1a9c-4052-99d8-a820e0ebabf7"
    riley_tech_assistant_id = os.environ.get("VAPI_RILEY_TECH_ASSISTANT_ID") or os.environ.get("VAPI_OPS_ASSISTANT_ID")
    
    # Debug: Show what IDs we're using
    print(f"\nAssistant IDs from environment:")
    print(f"  VAPI_ASSISTANT_ID: {os.environ.get('VAPI_ASSISTANT_ID', 'NOT SET')} (using: {riley_assistant_id})")
    print(f"  VAPI_RILEY_TECH_ASSISTANT_ID: {os.environ.get('VAPI_RILEY_TECH_ASSISTANT_ID', 'NOT SET')}")
    print(f"  VAPI_OPS_ASSISTANT_ID: {os.environ.get('VAPI_OPS_ASSISTANT_ID', 'NOT SET')}")
    if riley_tech_assistant_id:
        print(f"  → Using Riley OPS ID: {riley_tech_assistant_id}")
    else:
        print(f"  → Will create new Riley OPS assistant")
    print()
    
    project_root = Path(__file__).parent.parent
    
    # Configure Riley (Customer Line)
    if args.update_riley:
        customer_tools_dir = project_root / "doc" / "vapi" / "tools" / "customer_facing"
        riley_prompt_path = project_root / "doc" / "vapi" / "system_prompt_customer_inbound.md"
        
        print(f"\n  Using Assistant ID: {riley_assistant_id} (Riley Customer - Inbound)")
        
        riley_id = configure_assistant(
            api_key=api_key,
            webhook_secret=webhook_secret,
            assistant_id=riley_assistant_id,
            assistant_name="Riley Customer - Inbound",
            system_prompt_path=riley_prompt_path,
            tools_dir=customer_tools_dir,
            create_new=False,  # Don't create new, only update existing
            dry_run=args.dry_run,
        )
        
        if riley_id:
            print(f"\n  📞 Riley Customer Assistant ID: {riley_id}")
            print(f"  📱 Customer Line: {CUSTOMER_LINE}")
            print(f"  💡 Save this ID: export VAPI_ASSISTANT_ID={riley_id}")
    
    # Configure Riley Tech (Internal OPS Line)
    if args.update_riley_tech:
        internal_tools_dir = project_root / "doc" / "vapi" / "tools" / "internal_ops"
        riley_tech_prompt_path = project_root / "doc" / "vapi" / "system_prompt_internal_ops.md"
        
        if riley_tech_assistant_id:
            print(f"\n  Using Assistant ID: {riley_tech_assistant_id} (Riley OPS)")
        else:
            print(f"\n  No Assistant ID provided - will create new 'Riley OPS' assistant")
        
        riley_tech_id = configure_assistant(
            api_key=api_key,
            webhook_secret=webhook_secret,
            assistant_id=riley_tech_assistant_id,
            assistant_name="Riley OPS",
            system_prompt_path=riley_tech_prompt_path,
            tools_dir=internal_tools_dir,
            create_new=True,  # Create new if ID not provided
            dry_run=args.dry_run,
        )
        
        if riley_tech_id:
            print(f"\n  📞 Riley OPS Assistant ID: {riley_tech_id}")
            print(f"  📱 Internal OPS Line: {INTERNAL_OPS_LINE}")
            print(f"  💡 Save this ID: export VAPI_RILEY_TECH_ASSISTANT_ID={riley_tech_id}")
            print(f"     or: export VAPI_OPS_ASSISTANT_ID={riley_tech_id}")
    
    print("\n" + "=" * 60)
    print("Configuration Complete!")
    print("=" * 60)
    
    # Summary of configured assistants
    print("\nAssistant IDs:")
    if args.update_riley:
        print(f"  ✅ Riley Customer - Inbound: {riley_assistant_id}")
    if args.update_riley_tech and riley_tech_id:
        print(f"  ✅ Riley OPS: {riley_tech_id}")
    
    print("\nNext Steps:")
    print("1. Associate phone numbers with assistants in Vapi dashboard")
    if args.update_riley:
        print(f"   - Customer Line ({CUSTOMER_LINE}) → Riley Customer - Inbound ({riley_assistant_id})")
    if args.update_riley_tech and riley_tech_id:
        print(f"   - Internal OPS Line ({INTERNAL_OPS_LINE}) → Riley OPS ({riley_tech_id})")
    print("2. Test assistants by making calls")
    print("3. Monitor logs: fly logs --app haes-hvac")
    
    print("\nEnvironment Variables to Save:")
    if args.update_riley:
        print(f"  export VAPI_ASSISTANT_ID={riley_assistant_id}")
    if args.update_riley_tech and riley_tech_id:
        print(f"  export VAPI_RILEY_TECH_ASSISTANT_ID={riley_tech_id}")
        print(f"  export VAPI_OPS_ASSISTANT_ID={riley_tech_id}")
    print()


if __name__ == "__main__":
    main()
