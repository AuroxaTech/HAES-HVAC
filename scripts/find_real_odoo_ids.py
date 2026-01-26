#!/usr/bin/env python3
"""
HAES HVAC - Find Real Odoo IDs for Testing

Queries Odoo for real sale.order and crm.lead IDs that can be used for testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.integrations.odoo import create_odoo_client_from_settings


async def find_real_ids():
    """Find real Odoo IDs for testing."""
    print("=" * 60)
    print("Finding Real Odoo IDs for Testing")
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
        
        # Find sale.order records (quotes)
        print("-" * 60)
        print("Searching for sale.order records (quotes)...")
        print("-" * 60)
        
        try:
            sale_orders = await odoo_client.search_read(
                model="sale.order",
                domain=[("state", "in", ["draft", "sent", "sale"])],  # Draft quotes, sent quotes, confirmed orders
                fields=["id", "name", "state", "partner_id", "amount_total"],
                limit=10,
                order="id desc",  # Most recent first
            )
            
            if sale_orders:
                print(f"Found {len(sale_orders)} sale.order records:\n")
                for so in sale_orders:
                    partner_name = so.get("partner_id", [None, ""])[1] if so.get("partner_id") else "N/A"
                    amount = so.get("amount_total", 0)
                    print(f"  ID: {so['id']:6} | Name: {so.get('name', 'N/A'):20} | State: {so.get('state', 'N/A'):10} | Partner: {partner_name[:30]:30} | Amount: ${amount:,.2f}")
            else:
                print("  No sale.order records found")
        except Exception as e:
            print(f"  ✗ Error searching sale.order: {e}")
        
        # Find crm.lead records (leads/opportunities)
        print("\n" + "-" * 60)
        print("Searching for crm.lead records (leads/opportunities)...")
        print("-" * 60)
        
        try:
            leads = await odoo_client.search_read(
                model="crm.lead",
                domain=[],  # All leads
                fields=["id", "name", "stage_id", "partner_id", "expected_revenue"],
                limit=10,
                order="id desc",  # Most recent first
            )
            
            if leads:
                print(f"Found {len(leads)} crm.lead records:\n")
                for lead in leads:
                    stage_name = lead.get("stage_id", [None, ""])[1] if lead.get("stage_id") else "N/A"
                    partner_name = lead.get("partner_id", [None, ""])[1] if lead.get("partner_id") else "N/A"
                    revenue = lead.get("expected_revenue", 0)
                    print(f"  ID: {lead['id']:6} | Name: {lead.get('name', 'N/A'):30} | Stage: {stage_name[:25]:25} | Partner: {partner_name[:20]:20} | Revenue: ${revenue:,.2f}")
            else:
                print("  No crm.lead records found")
        except Exception as e:
            print(f"  ✗ Error searching crm.lead: {e}")
        
        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)
        
        # Print example usage
        if sale_orders or leads:
            print("\nExample test command:")
            if sale_orders:
                test_id = sale_orders[0]['id']
                print(f'curl -X POST https://haes-hvac.fly.dev/vapi/server \\')
                print(f'  -H "Content-Type: application/json" \\')
                print(f'  -d \'{{"message": {{"type": "tool-calls", "call": {{"customer": {{"number": "+15125550002"}}}}, "toolCallList": [{{"id": "test-real-id", "name": "ivr_close_sale", "arguments": {{"quote_id": "{test_id}", "proposal_selection": "better"}}}}]}}}}\'')
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await odoo_client.close()


if __name__ == "__main__":
    asyncio.run(find_real_ids())
