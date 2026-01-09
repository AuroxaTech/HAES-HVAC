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


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        print(f"Please set it in your .env file or export it")
        sys.exit(1)
    return value


def create_tool_definition() -> dict:
    """Create the hael_route tool definition for Vapi assistant."""
    return {
        "type": "function",
        "async": False,
        "messages": [
            {
                "type": "request-start",
                "content": "Let me check that for you."
            },
            {
                "type": "request-complete",
                "content": ""
            },
            {
                "type": "request-failed",
                "content": "I'm having trouble processing that request. Let me try again."
            },
            {
                "type": "request-response-delayed",
                "content": "This is taking a moment. Please hold.",
                "timingMilliseconds": 3000
            }
        ],
        "function": {
            "name": TOOL_NAME,
            "description": "Routes customer requests through the HAES system for service scheduling, quotes, billing inquiries, and status updates. Call this tool after gathering required information from the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_text": {
                        "type": "string",
                        "description": "The customer's request in their own words. Include key details like name, address, problem description, and urgency."
                    },
                    "conversation_context": {
                        "type": "string",
                        "description": "Optional. Brief summary of information gathered so far (name, phone, address, issue type, urgency, etc.)."
                    }
                },
                "required": ["user_text"]
            }
        },
        "server": {
            "url": SERVER_URL
        }
    }


def get_standalone_tool_payload() -> dict:
    """Create payload for standalone tool (PATCH /tool/{id})."""
    return {
        "name": TOOL_NAME,
        "type": "function",
        "async": False,
        "messages": [
            {
                "type": "request-start",
                "content": "Let me check that for you."
            },
            {
                "type": "request-complete",
                "content": ""
            },
            {
                "type": "request-failed",
                "content": "I'm having trouble processing that request. Let me try again."
            },
            {
                "type": "request-response-delayed",
                "content": "This is taking a moment. Please hold.",
                "timingMilliseconds": 3000
            }
        ],
        "function": {
            "name": TOOL_NAME,
            "description": "Routes customer requests through the HAES system for service scheduling, quotes, billing inquiries, and status updates. Call this tool after gathering required information from the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_text": {
                        "type": "string",
                        "description": "The customer's request in their own words. Include key details like name, address, problem description, and urgency."
                    },
                    "conversation_context": {
                        "type": "string",
                        "description": "Optional. Brief summary of information gathered so far (name, phone, address, issue type, urgency, etc.)."
                    }
                },
                "required": ["user_text"]
            }
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
    payload = {
        "async": False,
        "messages": [
            {
                "type": "request-start",
                "content": "Let me check that for you."
            },
            {
                "type": "request-complete",
                "content": ""
            },
            {
                "type": "request-failed",
                "content": "I'm having trouble processing that request. Let me try again."
            },
            {
                "type": "request-response-delayed",
                "content": "This is taking a moment. Please hold.",
                "timingMilliseconds": 3000
            }
        ],
        "function": {
            "name": TOOL_NAME,
            "description": "Routes customer requests through the HAES system for service scheduling, quotes, billing inquiries, and status updates. Call this tool after gathering required information from the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_text": {
                        "type": "string",
                        "description": "The customer's request in their own words. Include key details like name, address, problem description, and urgency."
                    },
                    "conversation_context": {
                        "type": "string",
                        "description": "Optional. Brief summary of information gathered so far (name, phone, address, issue type, urgency, etc.)."
                    }
                },
                "required": ["user_text"]
            }
        },
        "server": {
            "url": SERVER_URL,
            "secret": webhook_secret,
            "timeoutSeconds": 30
        }
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


def main():
    print("=" * 60)
    print("HAES HVAC - Vapi Assistant & Tool Configuration")
    print("=" * 60)
    print()
    
    # Load environment variables
    api_key = get_env_var("VAPI_API_KEY")
    assistant_id = get_env_var("VAPI_ASSISTANT_ID")
    webhook_secret = get_env_var("VAPI_WEBHOOK_SECRET")
    tool_id = os.environ.get("VAPI_TOOL_ID")  # Optional
    
    # Load system prompt
    print("[1/4] Loading system prompt...")
    system_prompt = load_system_prompt()
    print(f"      Loaded {len(system_prompt)} characters")
    
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
    
    # Update assistant
    print("\n[3/4] Updating Vapi assistant...")
    result = update_assistant(api_key, assistant_id, webhook_secret, system_prompt)
    print("      ✓ Assistant updated successfully")
    
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
