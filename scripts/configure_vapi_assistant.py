#!/usr/bin/env python3
"""
HAES HVAC - Vapi Assistant & Tool Configuration Script

This script configures the Vapi assistant "Riley" and the hael_route tool
to use the Server URL integration.

Usage:
    python scripts/configure_vapi_assistant.py

Requirements:
    - VAPI_API_KEY environment variable set
    - VAPI_ASSISTANT_ID environment variable set
    - VAPI_WEBHOOK_SECRET environment variable set

Optional:
    - VAPI_TOOL_ID environment variable (if tool already exists)
"""

import json
import os
import sys
import argparse
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# Configuration
VAPI_API_BASE = "https://api.vapi.ai"
SERVER_URL = "https://haes-hvac.fly.dev/vapi/server"
TOOL_NAME = "hael_route"


def load_system_prompt() -> str:
    """Load the system prompt from doc/vapi/system_prompt.md"""
    prompt_path = Path(__file__).parent.parent / "doc" / "vapi" / "system_prompt.md"
    
    if not prompt_path.exists():
        print(f"Error: System prompt not found at {prompt_path}")
        sys.exit(1)
    
    with open(prompt_path, "r") as f:
        return f.read()


def load_tool_schema() -> dict:
    """Load the tool schema from doc/vapi/tool_schema.json"""
    schema_path = Path(__file__).parent.parent / "doc" / "vapi" / "tool_schema.json"
    
    if not schema_path.exists():
        print(f"Warning: Tool schema not found at {schema_path}, using defaults")
        return {}
    
    with open(schema_path, "r") as f:
        return json.load(f)


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        print(f"Please set it in your .env file or export it")
        sys.exit(1)
    return value


def create_tool_definition() -> dict:
    """Create the hael_route tool definition for Vapi assistant.
    
    Loads parameters from doc/vapi/tool_schema.json to ensure consistency.
    """
    # Try to load from schema file first
    schema = load_tool_schema()
    tool_def = schema.get("tool_definition", {})
    
    if tool_def:
        # Use schema-defined tool but ensure server URL is correct
        result = {
            "type": tool_def.get("type", "function"),
            "async": tool_def.get("async", False),
            "messages": tool_def.get("messages", [
                {"type": "request-start", "content": "Let me check that for you."},
                {"type": "request-complete", "content": ""},
                {"type": "request-failed", "content": "I'm having trouble processing that request. Let me try again."},
                {"type": "request-response-delayed", "content": "This is taking a moment. Please hold.", "timingMilliseconds": 3000}
            ]),
            "function": tool_def.get("function", {}),
            "server": {"url": SERVER_URL}
        }
        return result
    
    # Fallback to hardcoded default (should not normally be reached)
    return {
        "type": "function",
        "async": False,
        "messages": [
            {"type": "request-start", "content": "Let me check that for you."},
            {"type": "request-complete", "content": ""},
            {"type": "request-failed", "content": "I'm having trouble processing that request. Let me try again."},
            {"type": "request-response-delayed", "content": "This is taking a moment. Please hold.", "timingMilliseconds": 3000}
        ],
        "function": {
            "name": TOOL_NAME,
            "description": "Submit a customer service request to the HAES system. Call this after collecting name, phone, address, and issue details.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        "server": {"url": SERVER_URL}
    }


def get_standalone_tool_payload() -> dict:
    """Create payload for standalone tool (PATCH /tool/{id}).
    
    Loads parameters from doc/vapi/tool_schema.json to ensure consistency.
    """
    # Load from schema file
    schema = load_tool_schema()
    tool_def = schema.get("tool_definition", {})
    function_def = tool_def.get("function", {})
    messages = tool_def.get("messages", [
        {"type": "request-start", "content": "Let me check that for you."},
        {"type": "request-complete", "content": ""},
        {"type": "request-failed", "content": "I'm having trouble processing that request. Let me try again."},
        {"type": "request-response-delayed", "content": "This is taking a moment. Please hold.", "timingMilliseconds": 3000}
    ])
    
    return {
        "name": TOOL_NAME,
        "type": "function",
        "async": False,
        "messages": messages,
        "function": {
            "name": function_def.get("name", TOOL_NAME),
            "description": function_def.get("description", "Submit a customer service request to the HAES system."),
            "parameters": function_def.get("parameters", {
                "type": "object",
                "properties": {},
                "required": []
            })
        },
        "server": {
            "url": SERVER_URL,
            "timeoutSeconds": 30
        }
    }


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


def update_tool(api_key: str, tool_id: str, webhook_secret: str) -> dict:
    """Update an existing tool configuration."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # For PATCH, only include fields that can be updated (not name/type)
    tool_def = get_standalone_tool_payload()
    payload = {
        "async": tool_def.get("async", False),
        "messages": tool_def.get("messages", []),
        "function": tool_def.get("function", {}),
        "server": {
            **tool_def.get("server", {}),
            "secret": webhook_secret,
        },
    }
    
    url = f"{VAPI_API_BASE}/tool/{tool_id}"
    
    print(f"Updating tool {tool_id}...")
    print(f"  Server URL: {SERVER_URL}")
    
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error updating tool: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return {}
    except Exception as e:
        print(f"Error updating tool: {e}")
        return {}


def create_tool(api_key: str, webhook_secret: str) -> dict:
    """Create a new tool."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = get_standalone_tool_payload()
    payload["server"]["secret"] = webhook_secret
    url = f"{VAPI_API_BASE}/tool"
    
    print(f"Creating tool {TOOL_NAME}...")
    print(f"  Server URL: {SERVER_URL}")
    
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error creating tool: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return {}
    except Exception as e:
        print(f"Error creating tool: {e}")
        return {}


def update_assistant(
    api_key: str,
    assistant_id: str,
    webhook_secret: str,
    system_prompt: str,
) -> dict:
    """Update the Vapi assistant configuration."""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Create tool definition
    tool_def = create_tool_definition()
    
    # Assistant update payload
    payload = {
        "model": {
            "provider": "openai",
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ],
            "tools": [tool_def]
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
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    print(f"Updating assistant {assistant_id}...")
    print(f"Server URL: {SERVER_URL}")
    print(f"Tool: hael_route")
    
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def verify_assistant(api_key: str, assistant_id: str) -> dict:
    """Verify the assistant configuration."""
    
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
        print(f"Warning: Could not verify assistant: {e}")
        return {}


def upload_file(api_key: str, file_path: Path) -> str | None:
    """Upload a file to Vapi and return file ID."""
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    url = f"{VAPI_API_BASE}/file"

    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            resp = httpx.post(url, headers=headers, files=files, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("id")
    except Exception as e:
        print(f"Warning: Failed to upload {file_path.name}: {e}")
        return None


def create_knowledge_base(api_key: str, name: str, file_ids: list[str]) -> str | None:
    """Create a Vapi knowledge base and return knowledgeBaseId."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{VAPI_API_BASE}/knowledge-base"

    # Keep createPlan minimal — advanced chunking options can cause provider errors in some orgs.
    payload = {
        "name": name,
        "provider": "trieve",
        "searchPlan": {
            "searchType": "semantic",
            "topK": 3,
            "removeStopWords": True,
            "scoreThreshold": 0.7,
        },
        "createPlan": {
            "type": "create",
            "chunkPlans": [
                {
                    "fileIds": file_ids,
                }
            ],
        },
    }

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("id")
    except Exception as e:
        print(f"Warning: Failed to create knowledge base: {e}")
        return None


def attach_knowledge_base_to_assistant(api_key: str, assistant_id: str, knowledge_base_id: str) -> dict:
    """Attach an existing knowledge base to an assistant while preserving current model settings."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    current = verify_assistant(api_key, assistant_id)
    model = current.get("model", {}) if isinstance(current.get("model"), dict) else {}
    if not model:
        raise RuntimeError("Could not read current assistant model to attach knowledge base.")

    # Vapi PATCH validates model.provider/model fields; send the full model object with only kb id changed.
    model["knowledgeBaseId"] = knowledge_base_id
    payload = {"model": model}

    resp = httpx.patch(url, headers=headers, json=payload, timeout=60.0)
    resp.raise_for_status()
    return resp.json()


def main():
    print("=" * 60)
    print("HAES HVAC - Vapi Assistant & Tool Configuration")
    print("=" * 60)
    print()

    parser = argparse.ArgumentParser(description="Configure Vapi tool/assistant for HAES HVAC.")
    parser.add_argument(
        "--update-assistant",
        action="store_true",
        help="Update the assistant system prompt + inline tool definition. WARNING: may reset some assistant settings.",
    )
    parser.add_argument(
        "--tool-only",
        action="store_true",
        help="Only update/create the standalone tool (recommended; will not touch assistant settings).",
    )
    parser.add_argument(
        "--sync-kb",
        action="store_true",
        help="Upload local KB markdown files (doc/vapi/kb/*.md), create a Vapi knowledge base, and attach it to the assistant.",
    )
    parser.add_argument(
        "--kb-name",
        default="hvac-r-finest-kb",
        help="Knowledge base name when using --sync-kb (default: hvac-r-finest-kb).",
    )
    parser.add_argument(
        "--knowledge-base-id",
        default=os.environ.get("VAPI_KNOWLEDGE_BASE_ID", ""),
        help="Attach an existing knowledge base ID to the assistant (no upload). Can also be set via VAPI_KNOWLEDGE_BASE_ID.",
    )
    args = parser.parse_args()

    # Default behavior: tool-only (safe). Assistant update must be explicitly requested.
    if not args.update_assistant:
        args.tool_only = True
    
    # Load environment variables
    api_key = get_env_var("VAPI_API_KEY")
    assistant_id = get_env_var("VAPI_ASSISTANT_ID")
    webhook_secret = get_env_var("VAPI_WEBHOOK_SECRET")
    tool_id = os.environ.get("VAPI_TOOL_ID")  # Optional
    
    # Load system prompt
    system_prompt = ""
    if args.update_assistant:
        print("[1/4] Loading system prompt...")
        system_prompt = load_system_prompt()
        print(f"      Loaded {len(system_prompt)} characters")
    else:
        print("[1/4] Skipping system prompt load (tool-only mode)")
    
    # Find or create/update the standalone tool
    print("\n[2/4] Configuring standalone tool...")
    if not tool_id:
        # Try to find existing tool by name
        tool_id = find_tool_by_name(api_key, TOOL_NAME)
        if tool_id:
            print(f"      Found existing tool: {tool_id}")
    
    if tool_id:
        # Update existing tool
        tool_result = update_tool(api_key, tool_id, webhook_secret)
        if tool_result:
            print("      ✓ Tool updated successfully")
            print(f"      Server URL: {tool_result.get('server', {}).get('url', 'N/A')}")
        else:
            print("      ⚠ Tool update failed (continuing with assistant update)")
    else:
        # Create new tool
        tool_result = create_tool(api_key, webhook_secret)
        if tool_result:
            tool_id = tool_result.get('id')
            print(f"      ✓ Tool created: {tool_id}")
            print(f"      Server URL: {tool_result.get('server', {}).get('url', 'N/A')}")
        else:
            print("      ⚠ Tool creation failed (tool may need manual setup)")
    
    # Update assistant (optional; can reset settings because it overwrites model/tools)
    if args.update_assistant:
        print("\n[3/4] Updating Vapi assistant...")
        _ = update_assistant(api_key, assistant_id, webhook_secret, system_prompt)
        print("      ✓ Assistant updated successfully")
    else:
        print("\n[3/4] Skipping assistant update (tool-only mode)")

    # Knowledge Base setup (optional)
    if args.sync_kb or args.knowledge_base_id:
        print("\n[KB] Configuring Knowledge Base...")
        kb_id = args.knowledge_base_id.strip() if args.knowledge_base_id else ""

        if args.sync_kb:
            kb_dir = Path(__file__).parent.parent / "doc" / "vapi" / "kb"
            kb_files = sorted(kb_dir.glob("*.md"))
            if not kb_files:
                print(f"Warning: No KB files found in {kb_dir}")
            else:
                print(f"Uploading {len(kb_files)} KB files...")
                uploaded_ids: list[str] = []
                for fp in kb_files:
                    file_id = upload_file(api_key, fp)
                    if file_id:
                        print(f"  ✓ {fp.name} -> {file_id}")
                        uploaded_ids.append(file_id)
                if uploaded_ids:
                    kb_id = create_knowledge_base(api_key, args.kb_name, uploaded_ids) or ""
                    if kb_id:
                        print(f"✓ Knowledge base created: {kb_id}")

        if kb_id:
            try:
                attach_knowledge_base_to_assistant(api_key, assistant_id, kb_id)
                print(f"✓ Attached knowledge base to assistant: {kb_id}")
                print(f"  export VAPI_KNOWLEDGE_BASE_ID={kb_id}")
            except Exception as e:
                print(f"Warning: Failed to attach knowledge base: {e}")
        else:
            print("Warning: No knowledge base ID available to attach.")
    
    # Verify configuration
    print("\n[4/4] Verifying configuration...")
    config = verify_assistant(api_key, assistant_id)
    
    if config:
        print("      ✓ Configuration verified")
        print()
        print("Assistant Details:")
        print(f"  - ID: {config.get('id', 'N/A')}")
        print(f"  - Name: {config.get('name', 'N/A')}")
        print(f"  - Server URL: {config.get('serverUrl', 'N/A')}")
        print(f"  - Server Messages: {', '.join(config.get('serverMessages', []))}")
        
        # Check if tool is configured
        model = config.get('model', {})
        tools = model.get('tools', [])
        if tools:
            print(f"  - Assistant Tools: {len(tools)} configured")
            for tool in tools:
                func = tool.get('function', {})
                server = tool.get('server', {})
                tool_url = server.get('url', 'N/A')
                print(f"    • {func.get('name', 'unnamed')} -> {tool_url}")
        else:
            print("  - Assistant Tools: None configured")
    
    if tool_id:
        print()
        print("Standalone Tool Details:")
        print(f"  - Tool ID: {tool_id}")
        print(f"  - Tool Name: {TOOL_NAME}")
        print(f"  - Server URL: {SERVER_URL}")
    
    print()
    print("=" * 60)
    print("Configuration Complete!")
    print("=" * 60)
    print()
    print("IMPORTANT: The standalone tool has been updated to point to the correct")
    print(f"Server URL: {SERVER_URL}")
    print()
    print("Next Steps:")
    print("1. Test the assistant by making a call to your Vapi phone number")
    print("2. Monitor logs: fly logs --app haes-hvac --no-tail")
    print("3. Check for successful POST /vapi/server requests (status 200)")
    print()
    print("Troubleshooting:")
    print("- If you get 401 errors, verify VAPI_WEBHOOK_SECRET matches in Fly.io")
    print("- If you get 422 errors, check the tool parameters in Vapi dashboard")
    print("- If no requests arrive, verify the assistant is using the correct tool")
    print()
    print("To save the tool ID for future use:")
    if tool_id:
        print(f"  export VAPI_TOOL_ID={tool_id}")
    print()


if __name__ == "__main__":
    main()
