#!/usr/bin/env python3
"""
HAES HVAC - Update Vapi Assistant from Repo

PATCH the existing Vapi assistant (by VAPI_ASSISTANT_ID) with:
- System prompt from doc/vapi/system_prompt_customer_inbound.md
- Tools from doc/vapi/tools/customer_facing/**/*.json

Uses get_settings() for VAPI_ASSISTANT_ID and VAPI_API_KEY.
Does not create a new assistant; only updates the one identified by VAPI_ASSISTANT_ID.

Usage:
    python scripts/update_vapi_assistant_from_repo.py

Requirements:
    - VAPI_API_KEY and VAPI_ASSISTANT_ID set in env or .env

Where to see tools in Vapi: Dashboard → Assistants → [Your assistant] → Model (or Tools).
The script sends inline tools; all 18 JSONs under customer_facing/ are included.
If a tool (e.g. lookup_customer_profile) is missing, re-run this script and check the printed list.
"""

import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings

VAPI_API_BASE = "https://api.vapi.ai"


def load_system_prompt() -> str:
    """Load system prompt from doc/vapi/system_prompt_customer_inbound.md."""
    path = PROJECT_ROOT / "doc" / "vapi" / "system_prompt_customer_inbound.md"
    if not path.exists():
        print(f"Error: System prompt not found at {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def load_tool_definitions_from_repo(server_url: str) -> list[dict]:
    """Load all tool definition JSONs from doc/vapi/tools/customer_facing/**/*.json."""
    tools_dir = PROJECT_ROOT / "doc" / "vapi" / "tools" / "customer_facing"
    if not tools_dir.exists():
        print(f"Warning: Tools directory not found: {tools_dir}")
        return []
    tool_files = sorted(tools_dir.rglob("*.json"))
    definitions = []
    for f in tool_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Failed to load {f}: {e}")
            continue
        td = data.get("tool_definition") or data
        func = td.get("function", {})
        if not func.get("name"):
            continue
        # Build inline tool for assistant (type, async, messages, function, server)
        definitions.append({
            "type": td.get("type", "function"),
            "async": td.get("async", False),
            "messages": td.get("messages", [
                {"type": "request-start", "content": "Let me check that for you."},
                {"type": "request-complete", "content": ""},
                {"type": "request-failed", "content": "I'm having trouble with that. Let me try again."},
            ]),
            "function": func,
            "server": {
                "url": (td.get("server") or {}).get("url") or server_url,
                "timeoutSeconds": 30,
            },
        })
    return definitions


def get_assistant(api_key: str, assistant_id: str) -> dict | None:
    """GET assistant by ID."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = httpx.get(f"{VAPI_API_BASE}/assistant/{assistant_id}", headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        print(f"Error fetching assistant: HTTP {e.response.status_code}")
        print(e.response.text)
        return None
    except Exception as e:
        print(f"Error fetching assistant: {e}")
        return None


def patch_assistant(api_key: str, assistant_id: str, system_prompt: str, tools: list[dict]) -> bool:
    """PATCH assistant with system prompt and tools."""
    assistant = get_assistant(api_key, assistant_id)
    if not assistant:
        return False
    model = assistant.get("model", {})
    if not isinstance(model, dict):
        print("Error: Assistant model is not a dict")
        return False

    # System message
    messages = list(model.get("messages", []))
    found = False
    for i, m in enumerate(messages):
        if m.get("role") == "system":
            messages[i] = {"role": "system", "content": system_prompt}
            found = True
            break
    if not found:
        messages.insert(0, {"role": "system", "content": system_prompt})
    model["messages"] = messages
    model["tools"] = tools

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    try:
        r = httpx.patch(url, headers=headers, json={"model": model}, timeout=60.0)
        r.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"Error PATCHing assistant: HTTP {e.response.status_code}")
        print(e.response.text)
        return False
    except Exception as e:
        print(f"Error PATCHing assistant: {e}")
        return False


def main() -> None:
    settings = get_settings()
    api_key = settings.VAPI_API_KEY
    assistant_id = settings.VAPI_ASSISTANT_ID
    if not api_key or not assistant_id:
        print("Error: VAPI_API_KEY and VAPI_ASSISTANT_ID must be set (e.g. in .env)")
        sys.exit(1)

    server_url = "https://haes-hvac.fly.dev/vapi/server"  # default; could come from settings if added

    print("Loading system prompt...")
    prompt = load_system_prompt()
    print(f"  Loaded {len(prompt)} characters")

    print("Loading tool definitions from repo...")
    tools = load_tool_definitions_from_repo(server_url)
    print(f"  Loaded {len(tools)} tools:")
    for t in tools:
        name = (t.get("function") or {}).get("name") or "?"
        print(f"    - {name}")

    if not tools:
        print("Warning: No tools loaded; assistant tools will be cleared if you continue.")

    print(f"PATCHing assistant {assistant_id}...")
    if patch_assistant(api_key, assistant_id, prompt, tools):
        print("Success: Assistant updated with prompt and tools from repo.")
    else:
        print("Failure: Could not update assistant. Check response above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
