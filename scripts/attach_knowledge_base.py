#!/usr/bin/env python3
"""
HAES HVAC - Attach Knowledge Base to Assistants

This script attaches existing Knowledge Bases to Vapi assistants.

Usage:
    python scripts/attach_knowledge_base.py [--kb-id <id>] [--assistant-id <id>]
"""

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

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


# Configuration
VAPI_API_BASE = "https://api.vapi.ai"

# Assistant IDs
RILEY_CUSTOMER_ID = os.environ.get("VAPI_ASSISTANT_ID") or "f639ba5f-7c38-4949-9479-ec2a40428d76"
RILEY_OPS_ID = os.environ.get("VAPI_RILEY_TECH_ASSISTANT_ID") or os.environ.get("VAPI_OPS_ASSISTANT_ID") or "fd35b574-1a9c-4052-99d8-a820e0ebabf7"


def get_env_var(name: str, required: bool = True) -> str | None:
    """Get environment variable with error handling."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Error: {name} environment variable not set")
        sys.exit(1)
    return value


def get_all_knowledge_bases(api_key: str) -> list[dict[str, Any]]:
    """Get all knowledge bases from Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/knowledge-base"
    
    try:
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching knowledge bases: {e}")
        return []


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


def attach_kb_to_assistant(api_key: str, assistant_id: str, kb_id: str) -> bool:
    """Attach knowledge base to assistant."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/assistant/{assistant_id}"
    
    payload = {
        "knowledgeBase": {
            "id": kb_id
        }
    }
    
    try:
        response = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        print(f"Error attaching KB: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"Error attaching KB: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Attach Knowledge Base to assistants")
    parser.add_argument("--kb-id", help="Knowledge Base ID to attach")
    parser.add_argument("--assistant-id", help="Assistant ID (default: both assistants)")
    parser.add_argument("--list", action="store_true", help="List all knowledge bases")
    args = parser.parse_args()
    
    print("=" * 60)
    print("HAES HVAC - Knowledge Base Attachment")
    print("=" * 60)
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    
    # List KBs if requested
    if args.list:
        print("\nFetching knowledge bases...")
        kbs = get_all_knowledge_bases(api_key)
        print(f"\nFound {len(kbs)} knowledge bases:\n")
        for kb in kbs:
            print(f"  ID: {kb.get('id')}")
            print(f"  Name: {kb.get('name')}")
            print(f"  Files: {len(kb.get('files', []))}")
            print()
        return
    
    # Get all KBs
    kbs = get_all_knowledge_bases(api_key)
    
    if not kbs:
        print("\n⚠️  No knowledge bases found in Vapi.")
        print("\nTo create a Knowledge Base:")
        print("1. Go to Vapi dashboard → Knowledge Base")
        print("2. Click 'Create Knowledge Base'")
        print("3. Upload files from doc/vapi/kb/")
        print("   - Customer: customer_faq.txt, policies.txt")
        print("   - OPS: ops_intake_and_call_policy.txt, policies.txt")
        print("4. Note the KB ID and run this script with --kb-id")
        return
    
    print(f"\nFound {len(kbs)} knowledge base(s):")
    for i, kb in enumerate(kbs, 1):
        print(f"  {i}. {kb.get('name')} (ID: {kb.get('id')})")
    
    # Use provided KB ID or first one
    kb_id = args.kb_id
    if not kb_id and kbs:
        kb_id = kbs[0].get('id')
        print(f"\nUsing first KB: {kbs[0].get('name')} ({kb_id})")
    
    if not kb_id:
        print("\n❌ No knowledge base ID provided")
        return
    
    # Attach to assistant(s)
    if args.assistant_id:
        assistant_ids = [args.assistant_id]
        assistant_names = ["Custom Assistant"]
    else:
        assistant_ids = [RILEY_CUSTOMER_ID, RILEY_OPS_ID]
        assistant_names = ["Riley Customer - Inbound", "Riley OPS"]
    
    print(f"\nAttaching KB to assistant(s)...")
    for assistant_id, assistant_name in zip(assistant_ids, assistant_names):
        print(f"\n  {assistant_name} ({assistant_id})...", end=" ")
        
        # Check current KB
        assistant = get_assistant(api_key, assistant_id)
        current_kb = assistant.get('knowledgeBase', {})
        current_kb_id = current_kb.get('id') if current_kb else None
        
        if current_kb_id == kb_id:
            print("✅ Already attached")
            continue
        
        if attach_kb_to_assistant(api_key, assistant_id, kb_id):
            print("✅ Attached")
        else:
            print("❌ Failed")
    
    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
