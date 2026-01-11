#!/usr/bin/env python3
"""
Script to find recent appointments created in Odoo.
Helps verify that appointment scheduling is working correctly.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.odoo import create_odoo_client_from_settings
from src.config.settings import get_settings


async def find_recent_appointments():
    """Find recent calendar events created in Odoo."""
    try:
        client = create_odoo_client_from_settings()
        await client.authenticate()
        
        # Search for appointments created in the last 7 days
        date_from = (datetime.now(timezone.utc) - timedelta(days=7)).replace(tzinfo=None)
        date_to = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        
        domain = [
            ("active", "=", True),
            ("start", ">=", date_from.strftime("%Y-%m-%d %H:%M:%S")),
            ("start", "<=", date_to.strftime("%Y-%m-%d %H:%M:%S")),
        ]
        
        print(f"\n🔍 Searching for appointments from {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}...\n")
        
        # Search for calendar events
        events = await client.search_read(
            "calendar.event",
            domain,
            fields=[
                "id",
                "name",
                "start",
                "stop",
                "duration",
                "partner_ids",
                "user_id",
                "location",
                "description",
                "res_id",
                "res_model",
                "active",
                "create_date",
            ],
            limit=50,
            order="create_date desc",  # Most recent first
        )
        
        if not events:
            print("❌ No recent appointments found.")
            print("\n💡 Tips:")
            print("   1. Check if you're connected to the correct Odoo database")
            print("   2. Verify the date range - appointments might be older")
            print("   3. Check if appointments were created in a different environment")
            print("   4. Try searching for specific appointment IDs (5167, 5166, etc.)")
            return
        
        print(f"✅ Found {len(events)} appointment(s):\n")
        print("=" * 100)
        
        for event in events:
            event_id = event.get("id")
            name = event.get("name", "N/A")
            start = event.get("start", "N/A")
            stop = event.get("stop", "N/A")
            duration = event.get("duration", "N/A")
            create_date = event.get("create_date", "N/A")
            
            # Get partner names
            partner_ids = event.get("partner_ids", [])
            partner_names = []
            if partner_ids:
                if isinstance(partner_ids[0], list) and len(partner_ids[0]) > 1:
                    partner_names = [p[1] for p in partner_ids if isinstance(p, list)]
                else:
                    # Fetch partner details
                    try:
                        partners = await client.read("res.partner", partner_ids, ["name", "phone", "email"])
                        partner_names = [f"{p.get('name', 'N/A')} ({p.get('phone', 'N/A')})" for p in partners]
                    except:
                        partner_names = [str(pid) for pid in partner_ids]
            
            # Get responsible user
            user_id = event.get("user_id")
            user_name = "N/A"
            if user_id:
                if isinstance(user_id, list) and len(user_id) > 1:
                    user_name = user_id[1]
                else:
                    try:
                        users = await client.read("res.users", [user_id], ["name"])
                        if users:
                            user_name = users[0].get("name", "N/A")
                    except:
                        user_name = str(user_id)
            
            # Check if linked to lead
            res_model = event.get("res_model")
            res_id = event.get("res_id")
            linked_to = ""
            if res_model == "crm.lead" and res_id:
                try:
                    leads = await client.read("crm.lead", [res_id], ["name"])
                    if leads:
                        linked_to = f" → Linked to Lead: {leads[0].get('name', 'N/A')} (ID: {res_id})"
                except:
                    linked_to = f" → Linked to Lead ID: {res_id}"
            
            location = event.get("location", "N/A")
            active = event.get("active", True)
            status = "✅ Active" if active else "❌ Cancelled"
            
            print(f"\n📅 Appointment ID: {event_id}")
            print(f"   Name: {name}")
            print(f"   Start: {start}")
            print(f"   End: {stop}")
            print(f"   Duration: {duration} hours")
            print(f"   Created: {create_date}")
            print(f"   Status: {status}")
            print(f"   Customer(s): {', '.join(partner_names) if partner_names else 'N/A'}")
            print(f"   Assigned To: {user_name}")
            print(f"   Location: {location}")
            if linked_to:
                print(f"   {linked_to}")
            print("-" * 100)
        
        print("\n" + "=" * 100)
        print(f"\n✅ Total: {len(events)} appointment(s) found")
        print("\n💡 To view in Odoo:")
        print("   1. Go to Calendar → Meetings")
        print("   2. Clear any date filters")
        print("   3. Search for appointment IDs or customer names")
        print("   4. Filter by 'Created Date' = Last 7 days")
        
    except Exception as e:
        print(f"\n❌ Error finding appointments: {e}")
        import traceback
        traceback.print_exc()


async def search_by_id(appointment_ids: list[int]):
    """Search for specific appointment IDs."""
    try:
        client = create_odoo_client_from_settings()
        await client.authenticate()
        
        print(f"\n🔍 Searching for appointment IDs: {appointment_ids}\n")
        
        events = await client.read(
            "calendar.event",
            appointment_ids,
            [
                "id",
                "name",
                "start",
                "stop",
                "partner_ids",
                "user_id",
                "location",
                "res_id",
                "res_model",
                "active",
                "create_date",
            ],
        )
        
        if not events:
            print(f"❌ No appointments found with IDs: {appointment_ids}")
            return
        
        print(f"✅ Found {len(events)} appointment(s):\n")
        for event in events:
            print(f"   ID: {event.get('id')} | Name: {event.get('name')} | Start: {event.get('start')} | Active: {event.get('active')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # If IDs don't exist, they might have been deleted or are in different DB
        if "does not exist" in str(e).lower():
            print("\n💡 These appointment IDs don't exist. Possible reasons:")
            print("   - They were created in a different Odoo database/environment")
            print("   - They were deleted or cancelled")
            print("   - The test ran against a different Odoo instance")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find recent appointments in Odoo")
    parser.add_argument(
        "--ids",
        type=int,
        nargs="+",
        help="Search for specific appointment IDs (e.g., --ids 5167 5166)",
    )
    
    args = parser.parse_args()
    
    if args.ids:
        asyncio.run(search_by_id(args.ids))
    else:
        asyncio.run(find_recent_appointments())
