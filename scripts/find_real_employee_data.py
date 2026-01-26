#!/usr/bin/env python3
"""
HAES HVAC - Find Real Employee Data for Testing

Queries Odoo for real employee emails and data that can be used for HR tool testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.integrations.odoo import create_odoo_client_from_settings


async def find_real_employee_data():
    """Find real employee data from Odoo for testing."""
    print("=" * 60)
    print("Finding Real Employee Data for HR Tool Testing")
    print("=" * 60)
    
    settings = get_settings()
    
    # Check required settings
    if not all([
        settings.ODOO_BASE_URL,
        settings.ODOO_DB,
        settings.ODOO_USERNAME,
        settings.ODOO_PASSWORD,
    ]):
        print("✗ Missing required Odoo environment variables")
        return
    
    print(f"\nOdoo URL: {settings.ODOO_BASE_URL}")
    print(f"Database: {settings.ODOO_DB}\n")
    
    odoo_client = create_odoo_client_from_settings()
    
    try:
        # Authenticate
        print("Authenticating...")
        uid = await odoo_client.authenticate()
        print(f"✓ Authenticated as uid={uid}\n")
        
        # Find hr.employee records
        print("-" * 60)
        print("Searching for hr.employee records...")
        print("-" * 60)
        
        try:
            employees = await odoo_client.search_read(
                model="hr.employee",
                domain=[],  # All employees
                fields=["id", "name", "work_email", "work_phone", "mobile_phone", "job_title", "department_id"],
                limit=20,
                order="id desc",  # Most recent first
            )
            
            if employees:
                print(f"Found {len(employees)} employee records:\n")
                valid_emails = []
                for emp in employees:
                    email = emp.get("work_email") or emp.get("work_phone") or "N/A"
                    phone = emp.get("mobile_phone") or emp.get("work_phone") or "N/A"
                    job = emp.get("job_title", "N/A")
                    if not job or job is False:
                        job = "N/A"
                    else:
                        job = str(job)[:25]
                    
                    dept_id = emp.get("department_id")
                    if dept_id and isinstance(dept_id, (list, tuple)) and len(dept_id) > 1:
                        dept = str(dept_id[1])[:20]
                    else:
                        dept = "N/A"
                    
                    print(f"  ID: {emp['id']:4} | Name: {emp.get('name', 'N/A'):30} | Email: {email:30} | Phone: {phone:15} | Job: {job:25} | Dept: {dept:20}")
                    
                    # Collect valid emails for testing
                    if email and email != "N/A" and "@" in email:
                        valid_emails.append({
                            "id": emp["id"],
                            "name": emp.get("name", ""),
                            "email": email,
                            "phone": phone,
                            "job_title": job,
                        })
                
                print(f"\n✓ Found {len(valid_emails)} employees with valid emails for testing")
                
                # Save to JSON for use in stress test
                import json
                output_file = Path(__file__).parent.parent / ".cursor" / "real_employee_data.json"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, "w") as f:
                    json.dump(valid_emails, f, indent=2)
                
                print(f"✓ Saved employee data to: {output_file}")
                
                # Print example usage
                if valid_emails:
                    test_emp = valid_emails[0]
                    print(f"\nExample test command for payroll_inquiry:")
                    print(f'curl -X POST https://haes-hvac.fly.dev/vapi/server \\')
                    print(f'  -H "Content-Type: application/json" \\')
                    print(f'  -d \'{{"message": {{"type": "tool-calls", "call": {{"customer": {{"number": "+18557683265"}}}}, "toolCallList": [{{"id": "test-payroll", "name": "payroll_inquiry", "arguments": {{"employee_email": "{test_emp["email"]}"}}}}]}}}}\'')
            else:
                print("  No employee records found")
        except Exception as e:
            print(f"  ✗ Error searching hr.employee: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await odoo_client.close()


if __name__ == "__main__":
    asyncio.run(find_real_employee_data())
