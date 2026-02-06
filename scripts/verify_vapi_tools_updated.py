#!/usr/bin/env python3
"""
Verify that create_service_request and schedule_appointment on Vapi have
the expected parameters from the repo (lead_source, caller_type, confirmed_partner_id,
chosen_slot_start for schedule).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed")
    sys.exit(1)

from src.config.settings import get_settings

VAPI_API_BASE = "https://api.vapi.ai"

EXPECTED = {
    "create_service_request": ["lead_source", "caller_type", "confirmed_partner_id"],
    "schedule_appointment": ["chosen_slot_start", "confirmed_partner_id", "caller_type"],
}


def main():
    settings = get_settings()
    api_key = settings.VAPI_API_KEY
    assistant_id = settings.VAPI_ASSISTANT_ID
    if not api_key or not assistant_id:
        print("Error: VAPI_API_KEY and VAPI_ASSISTANT_ID required")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    r = httpx.get(f"{VAPI_API_BASE}/assistant/{assistant_id}", headers=headers, timeout=30.0)
    r.raise_for_status()
    assistant = r.json()
    model = assistant.get("model", {})
    tools = model.get("tools", [])

    ok = True
    for tool_name, params in EXPECTED.items():
        found = None
        for t in tools:
            if (t.get("function") or {}).get("name") == tool_name:
                found = t
                break
        if not found:
            print(f"  FAIL: Tool '{tool_name}' not found on assistant.")
            ok = False
            continue
        props = (found.get("function") or {}).get("parameters", {}).get("properties", {})
        missing = [p for p in params if p not in props]
        if missing:
            print(f"  FAIL: '{tool_name}' missing parameters on Vapi: {missing}")
            ok = False
        else:
            print(f"  OK:   '{tool_name}' has {params}")

    if ok:
        print("\nConfirmed: create_service_request and schedule_appointment on Vapi match repo (expected params present).")
    else:
        print("\nRun: python scripts/update_vapi_assistant_from_repo.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
