#!/usr/bin/env python3
"""
Create or update request_quote tool in Vapi Tools library.
Reads schema from doc/vapi/tools/customer_facing/leads_quotes/request_quote.json.
If vapi_tool_id is present, updates that tool by ID; otherwise finds by name or creates.
"""

import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings

VAPI_API_BASE = "https://api.vapi.ai"
DEFAULT_SERVER_URL = "https://haes-hvac.fly.dev/vapi/server"
TOOL_JSON = (
    PROJECT_ROOT
    / "doc"
    / "vapi"
    / "tools"
    / "customer_facing"
    / "leads_quotes"
    / "request_quote.json"
)


def main() -> None:
    settings = get_settings()
    api_key = settings.VAPI_API_KEY
    if not api_key:
        print("Error: VAPI_API_KEY is not set.")
        sys.exit(1)

    if not TOOL_JSON.exists():
        print(f"Error: Tool schema not found: {TOOL_JSON}")
        sys.exit(1)

    data = json.loads(TOOL_JSON.read_text(encoding="utf-8"))
    td = data.get("tool_definition") or data
    function = td.get("function", {})
    tool_name = function.get("name")
    if tool_name != "request_quote":
        print(f"Error: Expected request_quote, got: {tool_name}")
        sys.exit(1)

    server_url = (data.get("server") or td.get("server") or {}).get("url") or DEFAULT_SERVER_URL
    payload = {
        "type": td.get("type", "function"),
        "async": data.get("async", td.get("async", False)),
        "messages": td.get(
            "messages",
            [
                {"type": "request-start", "content": "Let me get that quote request set up for you."},
                {"type": "request-complete", "content": ""},
                {
                    "type": "request-failed",
                    "content": "I had trouble submitting that quote request. I can try again.",
                },
            ],
        ),
        "function": function,
        "server": {
            "url": server_url,
            "timeoutSeconds": 30,
        },
    }
    if settings.VAPI_WEBHOOK_SECRET:
        payload["server"]["secret"] = settings.VAPI_WEBHOOK_SECRET

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Prefer updating by vapi_tool_id if present in schema
    vapi_tool_id = data.get("vapi_tool_id")
    existing_id = None

    if vapi_tool_id:
        try:
            get_resp = httpx.get(
                f"{VAPI_API_BASE}/tool/{vapi_tool_id}",
                headers=headers,
                timeout=30.0,
            )
            if get_resp.status_code == 200:
                existing_id = vapi_tool_id
        except Exception:
            pass

    if not existing_id:
        list_resp = httpx.get(f"{VAPI_API_BASE}/tool", headers=headers, timeout=30.0)
        list_resp.raise_for_status()
        tools = list_resp.json()
        existing = next(
            (t for t in tools if (t.get("function") or {}).get("name") == "request_quote"),
            None,
        )
        if existing:
            existing_id = existing.get("id")

    if existing_id:
        patch_payload = {
            "async": payload["async"],
            "messages": payload["messages"],
            "function": payload["function"],
            "server": payload["server"],
        }
        patch_resp = httpx.patch(
            f"{VAPI_API_BASE}/tool/{existing_id}",
            headers=headers,
            json=patch_payload,
            timeout=30.0,
        )
        patch_resp.raise_for_status()
        print(f"UPDATED request_quote id={existing_id}")
    else:
        create_resp = httpx.post(
            f"{VAPI_API_BASE}/tool", headers=headers, json=payload, timeout=30.0
        )
        create_resp.raise_for_status()
        tool_id = create_resp.json().get("id")
        print(f"CREATED request_quote id={tool_id}")


if __name__ == "__main__":
    main()
