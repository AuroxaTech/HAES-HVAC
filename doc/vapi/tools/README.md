# Vapi Tools Organization

This directory contains JSON tool schemas for all Vapi voice assistant tools, organized by access level and purpose.

## Structure

```
doc/vapi/tools/
├── customer_facing/          # Customer-facing tools (17 tools)
│   ├── appointments/          # Appointment scheduling tools (5 tools)
│   ├── leads_quotes/         # Lead and quote tools (4 tools)
│   ├── billing/              # Billing and payment tools (3 tools)
│   ├── information/           # Information lookup tools (4 tools)
│   └── complaints/           # Complaint handling (1 tool)
├── internal_ops/             # Internal employee tools (6+ tools)
│   ├── technician/           # Technician-specific tools (1 tool)
│   ├── hr/                   # HR tools (3 tools)
│   └── operations/           # Operations tools (2+ tools)
└── README.md                 # This file
```

## Tool Count

- **Total Tools**: 23
  - **Customer Facing**: 17 tools
  - **Internal OPS**: 6+ tools

## Customer Facing Tools (17 tools)

These tools are available to customers calling the Customer Line (+1-972-597-1644) via the "Riley" assistant.

### Appointments (5 tools)

- `schedule_appointment.json` - Schedule a new appointment
- `reschedule_appointment.json` - Reschedule an existing appointment
- `cancel_appointment.json` - Cancel an appointment
- `check_appointment_status.json` - Check status of an appointment
- `check_availability.json` - Check technician availability

**Python Handlers**: `src/vapi/tools/ops/`

### Leads & Quotes (4 tools)

- `create_service_request.json` - Create a new service request/lead
- `request_quote.json` - Request a quote for installation/equipment
- `check_lead_status.json` - Check status of a quote/lead
- `request_membership_enrollment.json` - Enroll in maintenance plan

**Python Handlers**: `src/vapi/tools/ops/` and `src/vapi/tools/revenue/`

### Billing (3 tools)

- `billing_inquiry.json` - Inquire about billing/balance
- `invoice_request.json` - Request invoice copy
- `payment_terms_inquiry.json` - Inquire about payment terms

**Python Handlers**: `src/vapi/tools/core/`

### Information (4 tools)

- `get_pricing.json` - Get service pricing information
- `get_maintenance_plans.json` - Get maintenance plan information
- `get_service_area_info.json` - Get service area coverage information
- `check_business_hours.json` - Check business hours

**Python Handlers**: `src/vapi/tools/core/` and `src/vapi/tools/utils/`

### Complaints (1 tool)

- `create_complaint.json` - Create a complaint/escalation ticket

**Python Handlers**: `src/vapi/tools/core/`

## Internal OPS Tools (6+ tools)

These tools are available to employees calling the Internal OPS Line (+1-855-768-3265) via the "Riley Tech" assistant. Access is controlled by role-based permissions.

### Technician Tools (1 tool)

- `ivr_close_sale.json` - Close a sale via IVR (ConversionFlow™)
  - **Access**: Technicians, Managers, Executives, Admin
  - **Purpose**: Allows technicians to close sales in the field, update Odoo pipeline, and trigger install crew dispatch

**Python Handlers**: `src/vapi/tools/revenue/`

### HR Tools (3 tools)

- `payroll_inquiry.json` - Inquire about payroll and commissions
- `onboarding_inquiry.json` - Get onboarding checklist and training info
- `hiring_inquiry.json` - Get hiring requirements and process info

**Access**: HR, Managers, Executives, Admin

**Python Handlers**: `src/vapi/tools/people/`

### Operations Tools (2+ tools)

- `inventory_inquiry.json` - Check parts and equipment inventory
- `purchase_request.json` - Create purchase requests for parts/equipment

**Access**: Managers, Dispatch, Executives, Admin

**Python Handlers**: `src/vapi/tools/core/`

## Role-Based Access Control

The system automatically identifies callers by phone number and assigns roles:

- **Customer**: Default role for unknown callers (customer-facing tools only)
- **Technician**: Identified from Odoo `hr.employee` or static roster
- **HR**: Identified from Odoo job title
- **Billing**: Identified from Odoo job title
- **Manager**: Identified from Odoo job title
- **Dispatch**: Identified from Odoo job title
- **Executive**: Identified from Odoo job title
- **Admin**: Full access to all tools

**Identification Flow:**
1. Try Odoo `hr.employee` lookup (phone, mobile, work_phone fields)
2. Fallback to static technician roster
3. Default to CUSTOMER if not found

**Access Enforcement:**
- Backend checks permissions before processing tool calls
- Unauthorized access returns clear error message
- All access attempts are logged for audit

## Integration Status

### Odoo Integration

Most tools integrate with Odoo 18 Enterprise:
- **Appointments**: Create/update `calendar.event` records
- **Leads**: Create/update `crm.lead` records
- **Quotes**: Create/update `sale.order` records
- **Employees**: Query `hr.employee` for identification

### Brain Handlers

Some tools use brain handlers (OPS/CORE/REVENUE/PEOPLE) which may:
- Query Odoo for data
- Apply business logic
- Calculate pricing
- Route to appropriate workflows

### Static Tools

Some tools provide static or calculated information without Odoo integration:
- Business hours
- Service area coverage
- Maintenance plan information
- Pricing calculations

## Phone Numbers & Assistants

### Customer Line
- **Number**: +1-972-597-1644
- **Source**: 8x8 call forwarding
- **Assistant**: "Riley"
- **Tools**: Customer Facing (17 tools)
- **Purpose**: Public customer service

### Internal OPS Line
- **Number**: +1-855-768-3265
- **Source**: Twilio direct integration
- **Assistant**: "Riley Tech"
- **Tools**: Internal OPS (6+ tools)
- **Purpose**: Internal employee support (technicians, HR, billing, managers)

## Python Handler Locations

All tool handlers are in `src/vapi/tools/`:

- **OPS tools**: `src/vapi/tools/ops/`
- **REVENUE tools**: `src/vapi/tools/revenue/`
- **CORE tools**: `src/vapi/tools/core/`
- **PEOPLE tools**: `src/vapi/tools/people/`
- **UTILS tools**: `src/vapi/tools/utils/`

Tool registration is in `src/vapi/tools/register_tools.py`.

## Adding New Tools

1. **Create Python Handler**: Add handler function in appropriate `src/vapi/tools/` subdirectory
2. **Create JSON Schema**: Add schema file in appropriate `doc/vapi/tools/` subdirectory
3. **Register Tool**: Add registration in `src/vapi/tools/register_tools.py`
4. **Update Permissions**: Add tool to `TOOL_PERMISSIONS` in `src/vapi/tools/base.py` if needed
5. **Update Documentation**: Update this README and `.cursor/context.json`

## Notes

- All tools use the same Server URL endpoint: `https://haes-hvac.fly.dev/vapi/server`
- Tools are automatically registered on import via `register_tools.py`
- Role-based access is enforced at the backend level
- New employees work immediately when added to Odoo (no code changes needed)
- Static roster provides fallback if Odoo is unavailable
