#!/usr/bin/env python3
"""
Create or update the create_service_request tool in Vapi's Tool Library so it
includes the full schema (including lead_source with enum). The update script
sends inline tools; if the assistant uses a library copy of this tool, that
copy must have lead_source. This script ensures the library tool is up to date.

Run:
  python scripts/create_create_service_request_tool.py

Requires: VAPI_API_KEY
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
TOOL_JSON = PROJECT_ROOT / "doc" / "vapi" / "tools" / "customer_facing" / "leads_quotes" / "create_service_request.json"


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
    if func.get("name") != "create_service_request":
        print("Error: JSON is not create_service_request")
        sys.exit(1)

    params = (func.get("parameters") or {}).get("properties") or {}
    if "lead_source" not in params:
        print("Error: Repo JSON is missing lead_source parameter. Update create_service_request.json first.")
        sys.exit(1)
    print(f"  Repo tool has lead_source with enum: {params.get('lead_source', {}).get('enum', [])}")

    payload = {
        "type": td.get("type", "function"),
        "async": td.get("async", False),
        "messages": td.get("messages", [
            {"type": "request-start", "content": "Let me create that service request for you."},
            {"type": "request-complete", "content": ""},
            {"type": "request-failed", "content": "I had trouble creating that request. A representative will follow up."},
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

    # Find existing tool by name
    tool_id = None
    try:
        r = httpx.get(f"{VAPI_API_BASE}/tool", headers=headers, timeout=30.0)
        r.raise_for_status()
        for t in r.json():
            if (t.get("function") or {}).get("name") == "create_service_request":
                tool_id = t.get("id")
                break
    except Exception as e:
        print(f"Warning: Could not list tools: {e}")

    if tool_id:
        # Update existing tool so it has lead_source. PATCH expects only function/server (no top-level "type")
        patch_body = {"function": payload["function"], "server": payload["server"]}
        if "messages" in payload:
            patch_body["messages"] = payload["messages"]
        try:
            r = httpx.patch(f"{VAPI_API_BASE}/tool/{tool_id}", headers=headers, json=patch_body, timeout=30.0)
            r.raise_for_status()
            print(f"Updated tool 'create_service_request' in the Tools library (ID: {tool_id}).")
            print("  lead_source parameter (with enum) is now on the library tool.")
        except httpx.HTTPStatusError as e:
            print(f"Error updating tool: HTTP {e.response.status_code}")
            print(e.response.text)
            sys.exit(1)
    else:
        # Create new
        try:
            r = httpx.post(f"{VAPI_API_BASE}/tool", headers=headers, json=payload, timeout=30.0)
            r.raise_for_status()
            out = r.json()
            tool_id = out.get("id")
            print(f"Created tool 'create_service_request' in the Tools library (ID: {tool_id}).")
            print("  Add this tool to your assistant in Dashboard → Assistants → Tools if needed.")
        except httpx.HTTPStatusError as e:
            print(f"Error creating tool: HTTP {e.response.status_code}")
            print(e.response.text)
            sys.exit(1)

    print("Done. Re-run update_vapi_assistant_from_repo.py to sync inline tools; assistant should then have lead_source.")


if __name__ == "__main__":
    main()
