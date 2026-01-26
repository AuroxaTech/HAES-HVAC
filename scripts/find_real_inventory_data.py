#!/usr/bin/env python3
"""
HAES HVAC - Find Real Inventory Data for Testing

Queries Odoo for real product/part data that can be used for operations tool testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.integrations.odoo import create_odoo_client_from_settings


async def find_real_inventory_data():
    """Find real inventory/product data from Odoo for testing."""
    print("=" * 60)
    print("Finding Real Inventory Data for Operations Tool Testing")
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
        
        # Find product.product records (parts/equipment)
        print("-" * 60)
        print("Searching for product.product records (parts/equipment)...")
        print("-" * 60)
        
        try:
            products = await odoo_client.search_read(
                model="product.product",
                domain=[],  # All products
                fields=["id", "name", "default_code", "qty_available", "categ_id", "type"],
                limit=20,
                order="id desc",  # Most recent first
            )
            
            if products:
                print(f"Found {len(products)} product records:\n")
                valid_products = []
                for prod in products:
                    name = prod.get("name", "N/A")
                    code = prod.get("default_code", "N/A")
                    qty = prod.get("qty_available", 0)
                    category = prod.get("categ_id", [None, ""])[1] if prod.get("categ_id") else "N/A"
                    prod_type = prod.get("type", "N/A")
                    
                    print(f"  ID: {prod['id']:4} | Name: {name[:40]:40} | Code: {code:15} | Qty: {qty:6} | Type: {prod_type:10} | Category: {category[:20]:20}")
                    
                    # Collect valid products for testing
                    if name and name != "N/A":
                        valid_products.append({
                            "id": prod["id"],
                            "name": name,
                            "code": code if code != "N/A" else None,
                            "quantity_available": qty,
                            "category": category if category != "N/A" else None,
                            "type": prod_type,
                        })
                
                print(f"\n✓ Found {len(valid_products)} products for testing")
                
                # Save to JSON for use in stress test
                import json
                output_file = Path(__file__).parent.parent / ".cursor" / "real_inventory_data.json"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, "w") as f:
                    json.dump(valid_products, f, indent=2)
                
                print(f"✓ Saved inventory data to: {output_file}")
                
                # Print example usage
                if valid_products:
                    test_prod = valid_products[0]
                    print(f"\nExample test command for inventory_inquiry:")
                    print(f'curl -X POST https://haes-hvac.fly.dev/vapi/server \\')
                    print(f'  -H "Content-Type: application/json" \\')
                    print(f'  -d \'{{"message": {{"type": "tool-calls", "call": {{"customer": {{"number": "+19452260222"}}}}, "toolCallList": [{{"id": "test-inventory", "name": "inventory_inquiry", "arguments": {{"part_name": "{test_prod["name"]}"}}}}]}}}}\'')
            else:
                print("  No product records found")
        except Exception as e:
            print(f"  ✗ Error searching product.product: {e}")
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
    asyncio.run(find_real_inventory_data())
