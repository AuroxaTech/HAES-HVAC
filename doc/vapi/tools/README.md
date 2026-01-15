# Vapi Tools Organization

This directory contains JSON tool definitions for all 22 Vapi tools, organized by integration type.

## Directory Structure

### `/odoo/` - Direct Odoo Integration Tools (10 tools)
These tools directly interact with Odoo to create, update, or query data:

- **Leads/CRM:**
  - `create_service_request.json` - Creates service request leads in Odoo
  - `create_complaint.json` - Creates escalation/complaint leads in Odoo
  - `check_lead_status.json` - Queries lead status from Odoo
  - `request_quote.json` - Creates quote leads in Odoo
  - `request_membership_enrollment.json` - Creates membership enrollment leads in Odoo

- **Appointments:**
  - `schedule_appointment.json` - Creates appointments in Odoo
  - `reschedule_appointment.json` - Updates appointments in Odoo
  - `cancel_appointment.json` - Cancels appointments in Odoo
  - `check_appointment_status.json` - Queries appointment status from Odoo
  - `check_availability.json` - Queries available appointment slots from Odoo

### `/brain_handlers/` - Brain Handler Tools (8 tools)
These tools use brain handlers (OPS/CORE/REVENUE/PEOPLE) which may query Odoo or use business logic:

- **CORE Brain:**
  - `billing_inquiry.json` - Billing information lookup (may query Odoo invoices)
  - `invoice_request.json` - Invoice requests (may query Odoo invoices)
  - `payment_terms_inquiry.json` - Payment terms information
  - `inventory_inquiry.json` - Inventory inquiries (may query Odoo inventory)
  - `purchase_request.json` - Purchase requests (may create Odoo purchase orders)

- **PEOPLE Brain:**
  - `hiring_inquiry.json` - Hiring process information
  - `onboarding_inquiry.json` - Onboarding checklist information
  - `payroll_inquiry.json` - Payroll information

### `/static/` - Static/Utility Tools (4 tools)
These tools return static or calculated data without Odoo integration:

- `get_pricing.json` - Service pricing calculations (based on tiers)
- `get_maintenance_plans.json` - Maintenance plan information and pricing
- `get_service_area_info.json` - Service area coverage information
- `check_business_hours.json` - Business hours status (calculated from current time)

## Tool Count Summary

- **Odoo Tools:** 10 tools
- **Brain Handlers Tools:** 8 tools
- **Static Tools:** 4 tools
- **Total:** 22 tools

## Integration Status

### Fully Integrated with Odoo ✅
All tools in `/odoo/` create, update, or query real data in Odoo:
- Lead creation returns real `lead_id`
- Appointment operations affect real Odoo calendar events
- Status queries return actual Odoo data

### Brain Handlers (May Use Odoo) 🔄
Tools in `/brain_handlers/` use brain handlers that may:
- Query Odoo for customer/invoice data
- Use business logic without Odoo
- Return static information (PEOPLE brain tools)

### Static/Calculated 📊
Tools in `/static/` provide:
- Calculated pricing based on tiers
- Static configuration data
- Time-based calculations

## Python Handler Locations

The corresponding Python handlers are located in:
- `src/vapi/tools/ops/` - OPS tools
- `src/vapi/tools/revenue/` - REVENUE tools
- `src/vapi/tools/core/` - CORE tools
- `src/vapi/tools/people/` - PEOPLE tools
- `src/vapi/tools/utils/` - Utility tools

## Usage

When adding or updating tools:
1. Place JSON schema in the appropriate folder based on integration type
2. Ensure Python handler matches the folder structure in `src/vapi/tools/`
3. Register the tool in `src/vapi/tools/register_tools.py`
4. Update this README if adding new categories
