#!/usr/bin/env python3
"""
HAES HVAC - Setup Knowledge Base for Vapi Assistants

This script creates and attaches Knowledge Base to Vapi assistants.

Usage:
    python scripts/setup_knowledge_base.py
"""

import os
import sys
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


def create_knowledge_base(api_key: str, name: str, files: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Create a new knowledge base in Vapi."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    url = f"{VAPI_API_BASE}/knowledge-base"
    
    payload = {
        "name": name,
        "files": files
    }
    
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error creating knowledge base: HTTP {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error creating knowledge base: {e}")
        return None


def upload_file_to_kb(api_key: str, kb_id: str, file_path: Path, file_name: str) -> bool:
    """Upload a file to a knowledge base."""
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    url = f"{VAPI_API_BASE}/knowledge-base/{kb_id}/file"
    
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (file_name, f, "text/plain")
            }
            response = httpx.post(url, headers=headers, files=files, timeout=60.0)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"Error uploading file {file_name}: {e}")
        return False


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


def read_kb_file(file_path: Path) -> str:
    """Read KB file content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def main():
    """Main function."""
    print("=" * 60)
    print("HAES HVAC - Knowledge Base Setup")
    print("=" * 60)
    
    # Get environment variables
    api_key = get_env_var("VAPI_API_KEY")
    
    project_root = Path(__file__).parent.parent
    kb_dir = project_root / "doc" / "vapi" / "kb"
    
    # Check existing KBs
    print("\nChecking existing knowledge bases...")
    existing_kbs = get_all_knowledge_bases(api_key)
    print(f"  Found {len(existing_kbs)} existing knowledge bases")
    
    # KB files for customer assistant
    customer_kb_files = [
        kb_dir / "customer_faq.txt",
        kb_dir / "policies.txt",
    ]
    
    # KB files for internal ops assistant
    ops_kb_files = [
        kb_dir / "ops_intake_and_call_policy.txt",
        kb_dir / "policies.txt",
    ]
    
    # Check if files exist
    customer_files_exist = all(f.exists() for f in customer_kb_files)
    ops_files_exist = all(f.exists() for f in ops_kb_files)
    
    print(f"\nKB Files:")
    print(f"  Customer KB files exist: {customer_files_exist}")
    print(f"  OPS KB files exist: {ops_files_exist}")
    
    if not customer_files_exist and not ops_files_exist:
        print("\n⚠️  No KB files found. Knowledge Base is optional.")
        print("   KB files should be in: doc/vapi/kb/")
        print("\n   For customer assistant:")
        print("     - customer_faq.txt")
        print("     - policies.txt")
        print("\n   For internal ops assistant:")
        print("     - ops_intake_and_call_policy.txt")
        print("     - policies.txt")
        return
    
    print("\n" + "=" * 60)
    print("NOTE: Vapi Knowledge Base API may require file uploads")
    print("      through their dashboard or different API endpoints.")
    print("=" * 60)
    print("\nTo set up Knowledge Base:")
    print("1. Go to Vapi dashboard → Knowledge Base")
    print("2. Create a new Knowledge Base")
    print("3. Upload the files from doc/vapi/kb/")
    print("4. Attach the KB to the assistant in assistant settings")
    print("\nAlternatively, check Vapi API docs for KB upload endpoints.")
    print()


if __name__ == "__main__":
    main()
