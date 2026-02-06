#!/usr/bin/env python3
"""
Create the lookup_customer_profile tool in Vapi's Tools Library so it appears
in the Dashboard → Tools list (searchable). The update_vapi_assistant_from_repo
script only sends inline tools, which don't show in the library.

Run once:
  uv run python scripts/create_lookup_customer_profile_tool.py

Requires: VAPI_API_KEY, and VAPI_WEBHOOK_SECRET (optional, for server secret).
"""

import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings

VAPI_API_BASE = "https://api.vapi.ai"
SERVER_URL = "https://haes-hvac.fly.dev/vapi/server"
TOOL_JSON = PROJECT_ROOT / "doc" / "vapi" / "tools" / "customer_facing" / "leads_quotes" / "lookup_customer_profile.json"


def main():
    settings = get_settings()
    api_key = settings.VAPI_API_KEY
    if not api_key:
        print("Error: VAPI_API_KEY not set (e.g. in .env)")
        sys.exit(1)

    if not TOOL_JSON.exists():
        print(f"Error: {TOOL_JSON} not found")
        sys.exit(1)

    data = json.loads(TOOL_JSON.read_text(encoding="utf-8"))
    td = data.get("tool_definition") or data
    func = td.get("function", {})
    if func.get("name") != "lookup_customer_profile":
        print("Error: JSON is not lookup_customer_profile")
        sys.exit(1)

    payload = {
        "type": td.get("type", "function"),
        "async": td.get("async", False),
        "messages": td.get("messages", [
            {"type": "request-start", "content": "Let me look that up for you."},
            {"type": "request-complete", "content": ""},
            {"type": "request-failed", "content": "I had trouble looking that up. We can continue as a new customer."},
        ]),
        "function": func,
        "server": {
            "url": (td.get("server") or data.get("server") or {}).get("url") or SERVER_URL,
            "timeoutSeconds": 30,
        },
    }
    if getattr(settings, "VAPI_WEBHOOK_SECRET", None):
        payload["server"]["secret"] = settings.VAPI_WEBHOOK_SECRET

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Check if already exists
    try:
        r = httpx.get(f"{VAPI_API_BASE}/tool", headers=headers, timeout=30.0)
        r.raise_for_status()
        for t in r.json():
            if (t.get("function") or {}).get("name") == "lookup_customer_profile":
                print(f"Tool 'lookup_customer_profile' already exists in the Tools library (ID: {t.get('id')}).")
                print("You should now see it in Dashboard → Tools when you search for it.")
                return
    except Exception as e:
        print(f"Warning: Could not list tools: {e}")

    # Create
    try:
        r = httpx.post(f"{VAPI_API_BASE}/tool", headers=headers, json=payload, timeout=30.0)
        r.raise_for_status()
        out = r.json()
        tool_id = out.get("id")
        print(f"Created tool 'lookup_customer_profile' in the Tools library.")
        print(f"Tool ID: {tool_id}")
        print("You should now see it in Dashboard → Tools when you search for 'lookup_customer_profile'.")
        print("The assistant already uses this tool (inline); no need to re-attach unless you use standalone tools only.")
    except httpx.HTTPStatusError as e:
        print(f"Error creating tool: HTTP {e.response.status_code}")
        print(e.response.text)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
