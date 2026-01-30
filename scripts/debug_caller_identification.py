#!/usr/bin/env python3
"""
Debug script to test caller identification and RBAC.

This script helps diagnose why a caller might be identified as "customer" instead of an authorized employee.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.caller_identification import identify_caller, normalize_phone
from src.integrations.odoo import create_odoo_client_from_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_caller_identification(phone_number: str):
    """
    Test caller identification for a given phone number.
    
    Args:
        phone_number: Phone number to test (any format)
    """
    print(f"\n{'='*60}")
    print(f"Testing Caller Identification for: {phone_number}")
    print(f"{'='*60}\n")
    
    # Step 1: Normalize phone number
    normalized = normalize_phone(phone_number)
    print(f"1. Normalized phone number: {normalized}\n")
    
    if not normalized:
        print("❌ ERROR: Phone number could not be normalized!")
        return
    
    # Step 2: Check Odoo employee lookup
    print("2. Checking Odoo hr.employee records...")
    try:
        odoo_client = create_odoo_client_from_settings()
        if not odoo_client.is_authenticated:
            await odoo_client.authenticate()
        
        # Search in all phone fields
        # Note: Odoo uses "mobile_phone" not "mobile"
        domain = [
            "|",
            "|",
            ("phone", "ilike", normalized),
            ("mobile_phone", "ilike", normalized),
            ("work_phone", "ilike", normalized),
        ]
        
        employees = await odoo_client.search_read(
            model="hr.employee",
            domain=domain,
            fields=["id", "name", "job_title", "phone", "mobile_phone", "work_phone", "active"],
            limit=10,
        )
        
        if employees:
            print(f"   ✅ Found {len(employees)} employee(s) in Odoo:\n")
            for emp in employees:
                print(f"   - ID: {emp.get('id')}")
                print(f"     Name: {emp.get('name')}")
                print(f"     Job Title: {emp.get('job_title', 'N/A')}")
                print(f"     Phone: {emp.get('phone', 'N/A')}")
                print(f"     Mobile Phone: {emp.get('mobile_phone', 'N/A')}")
                print(f"     Work Phone: {emp.get('work_phone', 'N/A')}")
                print(f"     Active: {emp.get('active', True)}")
                print()
        else:
            print("   ❌ No employee found in Odoo with this phone number")
            print(f"   Searched in fields: phone, mobile_phone, work_phone")
            print(f"   Search value: {normalized}\n")
    
    except Exception as e:
        print(f"   ❌ ERROR checking Odoo: {e}\n")
    
    # Step 3: Test full identification
    print("3. Testing full caller identification...")
    try:
        identity = await identify_caller(phone_number)
        
        print(f"   Phone: {identity.phone}")
        print(f"   Role: {identity.role.value}")
        print(f"   Employee ID: {identity.employee_id or 'N/A'}")
        print(f"   Name: {identity.name or 'N/A'}")
        print(f"   Active: {identity.is_active}")
        print(f"   Permissions: {len(identity.permissions)} tools")
        
        if identity.role.value == "customer":
            print("\n   ⚠️  WARNING: Caller identified as 'customer' (unauthorized)")
            print("   This means:")
            print("   - Phone number not found in Odoo hr.employee")
            print("   - Phone number not found in static technician roster")
            print("   - Access to internal_ops tools will be DENIED")
        else:
            print(f"\n   ✅ Caller identified as '{identity.role.value}' (authorized)")
            if "ivr_close_sale" in identity.permissions:
                print("   ✅ Has access to ivr_close_sale tool")
            else:
                print("   ❌ Does NOT have access to ivr_close_sale tool")
        
        print()
        
    except Exception as e:
        print(f"   ❌ ERROR during identification: {e}\n")
    
    # Step 4: Check static roster (if applicable)
    print("4. Checking static technician roster...")
    try:
        from src.brains.ops.tech_roster import get_technician_by_phone_static
        tech = get_technician_by_phone_static(normalized)
        if tech:
            print(f"   ✅ Found in static roster:")
            print(f"      ID: {tech.id}")
            print(f"      Name: {tech.name}")
            print(f"      Phone: {tech.phone}")
        else:
            print("   ❌ Not found in static technician roster")
        print()
    except Exception as e:
        print(f"   ❌ ERROR checking static roster: {e}\n")
    
    print(f"{'='*60}\n")


async def main():
    """Main function to test caller identification."""
    print("\n" + "="*60)
    print("HAES HVAC - Caller Identification Diagnostic Tool")
    print("="*60)
    print("\nThis tool helps diagnose RBAC issues.")
    print("Enter phone numbers to test (or 'quit' to exit).\n")
    
    while True:
        phone = input("Enter phone number to test (or 'quit'): ").strip()
        
        if phone.lower() in ['quit', 'exit', 'q']:
            break
        
        if not phone:
            continue
        
        await test_caller_identification(phone)


if __name__ == "__main__":
    asyncio.run(main())
