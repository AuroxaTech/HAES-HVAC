#!/usr/bin/env python3
"""
HAES HVAC - Odoo Capabilities Discovery Script

Discovers which Odoo models and fields are available for integration.
Outputs a capability report to .cursor/odoo_discovery.json.

Usage:
    # Set environment variables first
    uv run python scripts/discover_odoo_capabilities.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, ".")

from src.config.settings import get_settings
from src.integrations.odoo import OdooClient

# Candidate models to check
CANDIDATE_MODELS = [
    # Contacts
    ("res.partner", "Contacts/Partners", ["name", "email", "phone", "street", "city"]),
    ("res.users", "Users", ["name", "login", "email"]),
    # CRM / Sales
    ("crm.lead", "CRM Leads/Opportunities", ["name", "partner_id", "stage_id", "expected_revenue"]),
    ("sale.order", "Sales Orders/Quotes", ["name", "partner_id", "state", "amount_total"]),
    # Field Service / Projects
    ("project.task", "Project Tasks", ["name", "project_id", "stage_id", "user_ids"]),
    ("project.project", "Projects", ["name", "partner_id", "stage_id"]),
    # Accounting
    ("account.move", "Invoices/Journal Entries", ["name", "partner_id", "state", "amount_total"]),
    ("account.payment.term", "Payment Terms", ["name", "line_ids"]),
    ("account.tax", "Taxes", ["name", "amount", "type_tax_use"]),
    # Purchase
    ("purchase.order", "Purchase Orders", ["name", "partner_id", "state", "amount_total"]),
    # Inventory
    ("product.product", "Products", ["name", "default_code", "list_price"]),
    ("product.template", "Product Templates", ["name", "list_price", "type"]),
    ("stock.quant", "Inventory Quantities", ["product_id", "quantity", "location_id"]),
    # HR
    ("hr.employee", "Employees", ["name", "work_email", "department_id"]),
    ("hr.applicant", "Applicants", ["name", "partner_name", "stage_id"]),
    ("hr.payslip", "Payslips", ["employee_id", "state", "date_from", "date_to"]),
    # Activities
    ("mail.activity", "Activities/Tasks", ["res_model", "res_id", "activity_type_id", "summary"]),
    # Calendar
    ("calendar.event", "Calendar Events", ["name", "start", "stop", "partner_ids"]),
]


async def check_model_access(
    client: OdooClient, model: str, key_fields: list[str]
) -> dict:
    """
    Check if a model is accessible and which fields are available.

    Returns:
        Dictionary with accessibility and field info
    """
    result = {
        "accessible": False,
        "fields_checked": key_fields,
        "available_fields": [],
        "error": None,
    }

    try:
        # Try to get field definitions
        fields = await client.fields_get(model, attributes=["type", "string"])
        result["accessible"] = True
        result["available_fields"] = [f for f in key_fields if f in fields]
        result["total_fields"] = len(fields)
    except Exception as e:
        result["accessible"] = False
        result["error"] = str(e)

    return result


async def main() -> int:
    """Run Odoo capabilities discovery."""
    print("=" * 60)
    print("HAES HVAC - Odoo Capabilities Discovery")
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
        return 1

    print(f"\nOdoo URL: {settings.ODOO_BASE_URL}")
    print(f"Database: {settings.ODOO_DB}")

    client = OdooClient(
        base_url=settings.ODOO_BASE_URL,
        db=settings.ODOO_DB,
        username=settings.ODOO_USERNAME,
        password=settings.ODOO_PASSWORD,
        timeout_seconds=settings.ODOO_TIMEOUT_SECONDS,
        verify_ssl=settings.ODOO_VERIFY_SSL,
    )

    try:
        # Authenticate
        print("\nAuthenticating...")
        uid = await client.authenticate()
        print(f"✓ Authenticated as uid={uid}")

        # Discover capabilities
        print("\n" + "-" * 60)
        print("Model Discovery Results")
        print("-" * 60)

        discovery_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "odoo_base_url": settings.ODOO_BASE_URL,
            "odoo_db": settings.ODOO_DB,
            "uid": uid,
            "models": {},
        }

        accessible_count = 0
        for model, description, key_fields in CANDIDATE_MODELS:
            result = await check_model_access(client, model, key_fields)
            discovery_results["models"][model] = {
                "description": description,
                **result,
            }

            status = "✓" if result["accessible"] else "✗"
            fields_info = f"{len(result['available_fields'])}/{len(key_fields)} key fields" if result["accessible"] else result["error"][:50] if result["error"] else "Not accessible"

            print(f"  {status} {model:25} | {fields_info}")

            if result["accessible"]:
                accessible_count += 1

        # Summary
        print("\n" + "-" * 60)
        print(f"Summary: {accessible_count}/{len(CANDIDATE_MODELS)} models accessible")
        print("-" * 60)

        # Write discovery report
        output_path = Path(".cursor/odoo_discovery.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(discovery_results, f, indent=2, default=str)
        print(f"\n✓ Discovery report written to: {output_path}")

        # Print accessible models for easy reference
        print("\nAccessible models for HAES integration:")
        for model, info in discovery_results["models"].items():
            if info["accessible"]:
                print(f"  - {model}: {info['description']}")

        print("\n" + "=" * 60)
        print("PASS - Odoo capabilities discovery completed")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Discovery failed: {e}")
        return 1

    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

