#!/usr/bin/env python3
"""
HAES HVAC - Delete Vapi Tools

This script deletes specified tools from Vapi by their IDs.

Usage:
    python scripts/delete_vapi_tools.py
"""

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

# Tool IDs to delete
TOOLS_TO_DELETE = [
    "5cf0afaf-0f1a-4883-a7c8-3b817334b4eb",
    "9b839c8f-5edb-4730-aaf6-d6ff4b02d81f",
    "c6e83a04-fc6c-4c46-b153-53f6cb5bdba7",
    "5b952137-93f2-4b4d-8fae-24ded0aa0b8b",
    "fc5f72be-ca93-414f-b975-951127ddbeca",
    "f8113470-4e99-4265-ba8f-3cef4ac7fb94",
    "1bf83daf-8ef3-4147-98c0-86a06661f490",
    "0fa8c0cd-460d-417f-9824-277d596d8769",
    "89970916-fbef-4d9b-8f20-68dde9741283",
    "c75df981-f22c-4c44-98d9-df0163004170",
    "eda69878-4e56-4c8c-a679-f96ea4528f18",
    "1d828609-31f1-4a56-861e-1d5debf23761",
    "faf88129-96f4-4617-be65-e241b4accce6",
    "abd11d0c-5990-45cc-9640-55df7a5dbeba",
    "148c09c3-2aa7-4fc6-937e-48f23b6e429c",
    "0f8bb950-b046-41d5-83ad-1fd228d8ac13",
    "487d1601-bfd0-4fab-9e14-8c853ad5e44b",
    "6d4d5f59-3cd0-4679-bffd-ea168855bf42",
    "ca17203f-9cfb-451f-b0da-2682d123b6a4",
    "10366b3f-fba1-4fd4-b622-9d7b74275aa3",
    "5c8a1d45-dbae-465f-8bdc-4a73648b89b9",
    "0fa2584c-d915-4754-ad80-577684f6d9a2",
    "6851e3bf-f321-4068-ad61-490023aebd4c",
]


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        sys.exit(1)
    return value


def get_tool_info(api_key: str, tool_id: str) -> dict[str, Any] | None:
    """Get tool information before deletion."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/tool/{tool_id}"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None  # Tool doesn't exist
        print(f"Error fetching tool {tool_id}: HTTP {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Error fetching tool {tool_id}: {e}")
        return None


def delete_tool(api_key: str, tool_id: str) -> bool:
    """Delete a tool from Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/tool/{tool_id}"
    
    try:
        response = httpx.delete(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"  ⚠️  Tool not found (may already be deleted)")
            return False
        print(f"  ❌ Error: HTTP {e.response.status_code}")
        print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete Vapi tools by ID")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    print("=" * 70)
    print("HAES HVAC - Delete Vapi Tools")
    print("=" * 70)
    print(f"\nTools to delete: {len(TOOLS_TO_DELETE)}")
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    
    # Get tool info first
    print("\nFetching tool information...")
    tool_info = {}
    for tool_id in TOOLS_TO_DELETE:
        info = get_tool_info(api_key, tool_id)
        if info:
            func = info.get("function", {})
            tool_name = func.get("name", "Unknown")
            tool_info[tool_id] = tool_name
        else:
            tool_info[tool_id] = "Not Found"
        time.sleep(0.5)  # Rate limit protection
    
    # Show what will be deleted
    print("\nTools to be deleted:")
    for i, tool_id in enumerate(TOOLS_TO_DELETE, 1):
        tool_name = tool_info.get(tool_id, "Unknown")
        status = "✅ Exists" if tool_name != "Not Found" else "⚠️  Not Found"
        print(f"  {i:2d}. {tool_id[:8]}... - {tool_name} ({status})")
    
    # Confirm deletion
    if not args.yes:
        print("\n" + "=" * 70)
        try:
            response = input("Do you want to proceed with deletion? (yes/no): ").strip().lower()
            if response not in ["yes", "y"]:
                print("Deletion cancelled.")
                return
        except EOFError:
            print("\n⚠️  No input available. Use --yes flag to skip confirmation.")
            print("   Example: python scripts/delete_vapi_tools.py --yes")
            return
    else:
        print("\n" + "=" * 70)
        print("Proceeding with deletion (--yes flag provided)...")
    
    # Delete tools
    print("\nDeleting tools...")
    deleted_count = 0
    failed_count = 0
    not_found_count = 0
    
    for i, tool_id in enumerate(TOOLS_TO_DELETE, 1):
        tool_name = tool_info.get(tool_id, "Unknown")
        print(f"\n[{i}/{len(TOOLS_TO_DELETE)}] Deleting {tool_id[:8]}... ({tool_name})...", end=" ")
        
        if tool_name == "Not Found":
            print("⚠️  Not Found (skipping)")
            not_found_count += 1
            continue
        
        if delete_tool(api_key, tool_id):
            print("✅ Deleted")
            deleted_count += 1
        else:
            print("❌ Failed")
            failed_count += 1
        
        # Rate limit protection
        time.sleep(1.0)
    
    # Summary
    print("\n" + "=" * 70)
    print("Deletion Summary")
    print("=" * 70)
    print(f"  ✅ Successfully deleted: {deleted_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  ⚠️  Not found: {not_found_count}")
    print(f"  📊 Total processed: {len(TOOLS_TO_DELETE)}")
    print()


if __name__ == "__main__":
    main()
