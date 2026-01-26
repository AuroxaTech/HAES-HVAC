---
name: Dual Phone Number Architecture with Tool Reorganization
overview: "Implement dual phone number architecture: Customer Line (+1-972-597-1644) for customers and Internal OPS Line (+1-855-768-3265) for all employees (technicians, HR, billing, managers). Reorganize tools into Customer Facing Tools and Internal OPS Tools folders. Implement role-based access control with hybrid Odoo + static roster identification."
todos:
  - id: reorganize_tool_folders
    content: Create new folder structure (customer_facing/ and internal_ops/) and move all JSON tool files to new locations
    status: completed
  - id: update_tools_readme
    content: Rewrite doc/vapi/tools/README.md to reflect new two-folder structure with tool categorization
    status: completed
    dependencies:
      - reorganize_tool_folders
  - id: create_caller_identification
    content: Create src/utils/caller_identification.py with hybrid employee lookup (Odoo + static roster) and role determination
    status: completed
  - id: enhance_tech_roster
    content: Add normalize_phone() and get_technician_by_phone_static() to src/brains/ops/tech_roster.py
    status: completed
  - id: implement_role_based_access
    content: Add TOOL_PERMISSIONS dictionary and check_access() method to src/vapi/tools/base.py
    status: completed
    dependencies:
      - create_caller_identification
  - id: update_vapi_server_rbac
    content: Add caller identification and role-based access control in src/api/vapi_server.py process_tool_call() function
    status: completed
    dependencies:
      - create_caller_identification
      - implement_role_based_access
  - id: create_ivr_close_sale_handler
    content: Create src/vapi/tools/revenue/ivr_close_sale.py with close sale logic and Odoo integration
    status: completed
    dependencies:
      - create_caller_identification
  - id: create_ivr_close_sale_schema
    content: Create doc/vapi/tools/internal_ops/technician/ivr_close_sale.json tool schema
    status: completed
    dependencies:
      - reorganize_tool_folders
  - id: register_ivr_tool
    content: Register ivr_close_sale tool in src/vapi/tools/register_tools.py
    status: completed
    dependencies:
      - create_ivr_close_sale_handler
  - id: create_internal_ops_prompt
    content: Create doc/vapi/system_prompt_internal_ops.md for Riley Tech assistant with role-based guidance
    status: completed
  - id: create_assistant_config_script
    content: Create scripts/configure_vapi_assistants.py to update Riley assistant and create Riley Tech assistant with phone numbers
    status: completed
    dependencies:
      - create_internal_ops_prompt
      - create_ivr_close_sale_schema
  - id: update_context_json
    content: Update .cursor/context.json with new phone numbers, assistants, tool organization, and role-based access documentation
    status: completed
    dependencies:
      - reorganize_tool_folders
      - create_ivr_close_sale_schema
  - id: update_direct_vapi_plan
    content: Update .cursor/plans/direct_vapi_tools_architecture_eff922e1.plan.md with new phone number strategy and mark conversionflow todo
    status: completed
isProject: false
---

# Dual Phone Number Architecture with Tool Reorganization

## Overview

Implement two-phone-number architecture with clear separation:

- **Customer Line** (+1-972-597-1644): 8x8 forwarded inbound for customers
- **Internal OPS Line** (+1-855-768-3265): Twilio number for all employees (technicians, HR, billing, managers, executives)

## Phone Number Architecture

```
Customer Line (+1-972-597-1644)
    ↓
8x8 Call Forwarding
    ↓
"Riley" Assistant
    ↓
Customer Facing Tools (17 tools)
    ↓
Purpose: Public customer service

---

Internal OPS Line (+1-855-768-3265)
    ↓
Twilio Direct Integration
    ↓
"Riley Tech" Assistant
    ↓
Internal OPS Tools (6+ tools)
    ↓
Backend: Role-based access control
    ↓
Purpose: All internal employees
 - Technicians (ivr_close_sale)
 - HR (payroll_inquiry, onboarding_inquiry, hiring_inquiry)
 - Billing/Accounting (billing_inquiry, invoice_request, payment_terms_inquiry)
 - Managers/Ops (inventory_inquiry, purchase_request)
 - Executives (all tools)
```

## Tool Reorganization

### New Folder Structure

**Current Structure:**

```
doc/vapi/tools/
├── odoo/ (10 tools)
├── brain_handlers/ (8 tools)
├── static/ (4 tools)
└── README.md
```

**New Structure:**

```
doc/vapi/tools/
├── customer_facing/ (17 tools)
│   ├── appointments/ (5 tools)
│   ├── leads_quotes/ (4 tools)
│   ├── billing/ (3 tools)
│   ├── information/ (4 tools)
│   └── complaints/ (1 tool)
├── internal_ops/ (6+ tools)
│   ├── technician/ (1 tool: ivr_close_sale)
│   ├── hr/ (3 tools)
│   └── operations/ (2+ tools)
└── README.md
```

### Tool Categorization

#### Customer Facing Tools (17 tools) → "Riley" Assistant

**Appointments (5 tools):**

- `schedule_appointment.json`
- `reschedule_appointment.json`
- `cancel_appointment.json`
- `check_appointment_status.json`
- `check_availability.json`

**Leads & Quotes (4 tools):**

- `create_service_request.json`
- `request_quote.json`
- `check_lead_status.json`
- `request_membership_enrollment.json`

**Billing (3 tools):**

- `billing_inquiry.json`
- `invoice_request.json`
- `payment_terms_inquiry.json`

**Information (4 tools):**

- `get_pricing.json`
- `get_maintenance_plans.json`
- `get_service_area_info.json`
- `check_business_hours.json`

**Complaints (1 tool):**

- `create_complaint.json`

#### Internal OPS Tools (6+ tools) → "Riley Tech" Assistant

**Technician Tools (1 tool):**

- `ivr_close_sale.json` (NEW)

**HR Tools (3 tools):**

- `payroll_inquiry.json`
- `onboarding_inquiry.json`
- `hiring_inquiry.json`

**Operations Tools (2 tools):**

- `inventory_inquiry.json`
- `purchase_request.json`

**Note:** Some tools may be accessible to both (e.g., managers might need billing tools), but primary access is role-based.

## Implementation Tasks

### Phase 1: Tool Reorganization

#### 1.1 Create New Folder Structure

**Actions:**

- Create `doc/vapi/tools/customer_facing/` directory
- Create `doc/vapi/tools/customer_facing/appointments/` subdirectory
- Create `doc/vapi/tools/customer_facing/leads_quotes/` subdirectory
- Create `doc/vapi/tools/customer_facing/billing/` subdirectory
- Create `doc/vapi/tools/customer_facing/information/` subdirectory
- Create `doc/vapi/tools/customer_facing/complaints/` subdirectory
- Create `doc/vapi/tools/internal_ops/` directory
- Create `doc/vapi/tools/internal_ops/technician/` subdirectory
- Create `doc/vapi/tools/internal_ops/hr/` subdirectory
- Create `doc/vapi/tools/internal_ops/operations/` subdirectory

#### 1.2 Move Existing Tool JSON Files

**Move from `odoo/` to `customer_facing/`:**

- `schedule_appointment.json` → `customer_facing/appointments/`
- `reschedule_appointment.json` → `customer_facing/appointments/`
- `cancel_appointment.json` → `customer_facing/appointments/`
- `check_appointment_status.json` → `customer_facing/appointments/`
- `check_availability.json` → `customer_facing/appointments/`
- `create_service_request.json` → `customer_facing/leads_quotes/`
- `request_quote.json` → `customer_facing/leads_quotes/`
- `check_lead_status.json` → `customer_facing/leads_quotes/`
- `request_membership_enrollment.json` → `customer_facing/leads_quotes/`
- `create_complaint.json` → `customer_facing/complaints/`

**Move from `brain_handlers/` to `customer_facing/`:**

- `billing_inquiry.json` → `customer_facing/billing/`
- `invoice_request.json` → `customer_facing/billing/`
- `payment_terms_inquiry.json` → `customer_facing/billing/`

**Move from `static/` to `customer_facing/information/`:**

- `get_pricing.json` → `customer_facing/information/`
- `get_maintenance_plans.json` → `customer_facing/information/`
- `get_service_area_info.json` → `customer_facing/information/`
- `check_business_hours.json` → `customer_facing/information/`

**Move from `brain_handlers/` to `internal_ops/`:**

- `payroll_inquiry.json` → `internal_ops/hr/`
- `onboarding_inquiry.json` → `internal_ops/hr/`
- `hiring_inquiry.json` → `internal_ops/hr/`
- `inventory_inquiry.json` → `internal_ops/operations/`
- `purchase_request.json` → `internal_ops/operations/`

#### 1.3 Update README.md

**File**: `doc/vapi/tools/README.md`

- Rewrite to reflect new two-folder structure
- Document Customer Facing Tools (17 tools)
- Document Internal OPS Tools (6+ tools)
- Update tool count summary
- Update integration status notes
- Keep Python handler location references

### Phase 2: Employee Identification System

#### 2.1 Create Caller Identification Module

**File**: `src/utils/caller_identification.py` (NEW)

- Implement `normalize_phone()` for consistent phone matching
- Implement `CallerRole` enum: CUSTOMER, TECHNICIAN, HR, BILLING, MANAGER, EXECUTIVE, DISPATCH, ADMIN
- Implement `CallerIdentity` dataclass with role, permissions, employee_id
- Implement `get_employee_by_phone()` with hybrid approach:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Primary: Odoo `hr.employee` lookup (phone, mobile, work_phone)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Fallback: Static roster from `tech_roster.py`
- Implement `get_employee_from_odoo()` to query Odoo employees
- Implement `determine_role_from_job()` to map job titles to roles
- Implement `get_permissions_for_role()` to return tool permissions per role
- Return `CallerIdentity` object with role and permissions

**Key Features:**

- Supports multiple phone numbers per employee
- Works immediately for new employees added to Odoo
- Resilient fallback if Odoo unavailable
- Role-based permission system

#### 2.2 Enhance tech_roster.py

**File**: `src/brains/ops/tech_roster.py`

- Add `normalize_phone()` function (if not present)
- Add `get_technician_by_phone_static()` function
- These support the hybrid identification system

### Phase 3: Role-Based Access Control

#### 3.1 Update BaseToolHandler

**File**: `src/vapi/tools/base.py`

- Add `TOOL_PERMISSIONS` dictionary mapping tools to allowed roles:
  ```python
  TOOL_PERMISSIONS = {
      # Customer tools (public)
      "create_service_request": [CallerRole.CUSTOMER],
      "schedule_appointment": [CallerRole.CUSTOMER],
      # ... all customer tools
      
      # Internal tools (role-based)
      "ivr_close_sale": [CallerRole.TECHNICIAN, CallerRole.MANAGER, CallerRole.EXECUTIVE],
      "payroll_inquiry": [CallerRole.HR, CallerRole.MANAGER, CallerRole.EXECUTIVE],
      "onboarding_inquiry": [CallerRole.HR, CallerRole.MANAGER, CallerRole.EXECUTIVE],
      "hiring_inquiry": [CallerRole.HR, CallerRole.MANAGER, CallerRole.EXECUTIVE],
      "inventory_inquiry": [CallerRole.MANAGER, CallerRole.EXECUTIVE, CallerRole.DISPATCH],
      "purchase_request": [CallerRole.MANAGER, CallerRole.EXECUTIVE, CallerRole.DISPATCH],
      # ... all internal tools
  }
  ```

- Add `check_access()` method to verify caller has permission for tool
- Return (allowed: bool, error_message: str)

#### 3.2 Update vapi_server.py

**File**: `src/api/vapi_server.py`

- In `process_tool_call()` function:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Extract caller phone from Vapi message
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Call `identify_caller()` to get `CallerIdentity`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Check access using `BaseToolHandler.check_access()`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If denied: Return error response
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If allowed: Add caller context to parameters (`_caller_role`, `_caller_id`, `_caller_name`)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Continue with tool processing

**Code Pattern:**

```python
# Extract caller phone
call_obj = message.get("call", {})
caller_phone = (
    call_obj.get("customer", {}).get("number") or
    call_obj.get("from") or
    call_obj.get("customerNumber")
)

# Identify caller
from src.utils.caller_identification import identify_caller
caller_identity = await identify_caller(caller_phone)

# Check access
from src.vapi.tools.base import BaseToolHandler
handler = BaseToolHandler(tool_name)
allowed, error_msg = handler.check_access(tool_name, caller_identity)

if not allowed:
    return error_response(error_msg)

# Add context
parameters["_caller_role"] = caller_identity.role.value
parameters["_caller_id"] = caller_identity.employee_id
parameters["_caller_name"] = caller_identity.name
```

### Phase 4: Create ivr_close_sale Tool

#### 4.1 Create Tool Handler

**File**: `src/vapi/tools/revenue/ivr_close_sale.py` (NEW)

- Implement `handle_ivr_close_sale()` async function
- Verify caller is technician (already done in vapi_server.py, but double-check)
- Load quote/lead from Odoo by `quote_id`
- Present proposal (Good/Better/Best options)
- Record customer voice approval
- Collect deposit information
- Update Odoo pipeline stage to "Quote Approved - Waiting for Parts"
- Store IVR recording reference
- Trigger install crew dispatch via OPS-BRAIN
- Apply same-day premium logic if applicable
- Enforce no field discounting
- Log closing for audit trail

**Parameters:**

- `quote_id` (required): Odoo quote/lead ID
- `proposal_selection` (required): "good", "better", or "best"
- `financing_option` (optional): Financing partner or "cash"
- `deposit_amount` (optional): Deposit amount collected
- `customer_phone` (optional): Customer phone for verification

#### 4.2 Create Tool Schema

**File**: `doc/vapi/tools/internal_ops/technician/ivr_close_sale.json` (NEW)

- Define JSON schema for `ivr_close_sale` tool
- Include all required and optional parameters
- Set `server.url` to production endpoint
- Configure appropriate messages

#### 4.3 Register Tool

**File**: `src/vapi/tools/register_tools.py`

- Import `handle_ivr_close_sale` from `src.vapi.tools.revenue.ivr_close_sale`
- Register: `register_tool("ivr_close_sale", handle_ivr_close_sale)`

### Phase 5: Assistant Configuration

#### 5.1 Create Internal OPS System Prompt

**File**: `doc/vapi/system_prompt_internal_ops.md` (NEW)

- Create system prompt for "Riley Tech" assistant
- Focus on internal employee support:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Technicians: Closing sales, ConversionFlow™ protocol
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - HR: Payroll, onboarding, hiring inquiries
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Billing: Invoice and payment inquiries
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Managers: Inventory, purchase requests
- Reference role-based tool access
- Include prohibited phrases (no field discounting, etc.)
- Professional, helpful tone for internal use

#### 5.2 Update Customer System Prompt

**File**: `doc/vapi/system_prompt.md`

- Ensure it's optimized for customer-facing interactions
- Reference only customer-facing tools
- No mention of internal tools

#### 5.3 Create Vapi Configuration Script

**File**: `scripts/configure_vapi_assistants.py` (NEW)

- Update existing "Riley" assistant:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Attach all Customer Facing Tools (17 tools)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update system prompt from `system_prompt.md`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Verify phone number association (+1-972-597-1644 via 8x8)

- Create "Riley Tech" assistant:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Name: "Riley Tech" or "Riley Internal OPS"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Attach all Internal OPS Tools (6+ tools)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Set system prompt from `system_prompt_internal_ops.md`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create/associate phone number (+1-855-768-3265)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Store assistant ID and phone number ID

**API Calls** (using Context7 docs):

- `PATCH /assistant/{riley_id}` - Update Riley with customer tools
- `POST /assistants` - Create Riley Tech assistant
- `POST /phone-number` - Create/verify Internal OPS phone number
- `PATCH /assistant/{riley_tech_id}` - Update Riley Tech with internal tools

### Phase 6: Update Documentation

#### 6.1 Update Tools README

**File**: `doc/vapi/tools/README.md`

- Complete rewrite with new structure
- Document Customer Facing Tools (17 tools) with subcategories
- Document Internal OPS Tools (6+ tools) with subcategories
- Update tool count: 23 total (17 customer + 6 internal)
- Document role-based access control
- Update integration status notes

#### 6.2 Update Context.json

**File**: `.cursor/context.json`

- Update `vapi_tools.total_tools` to 23
- Update `vapi_tools.organization` to reflect new folder structure:
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `customer_facing`: 17 tools
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - `internal_ops`: 6+ tools
- Add `phone_numbers` section:
  ```json
  "phone_numbers": {
    "customer_line": {
      "number": "+19725971644",
      "source": "8x8_forwarded",
      "assistant": "Riley",
      "tools": "customer_facing (17 tools)",
      "purpose": "Public customer service"
    },
    "internal_ops_line": {
      "number": "+18557683265",
      "source": "twilio",
      "assistant": "Riley Tech",
      "tools": "internal_ops (6+ tools)",
      "purpose": "Internal employees (technicians, HR, billing, managers)"
    }
  }
  ```

- Add `assistants` section:
  ```json
  "assistants": {
    "riley": {
      "name": "Riley",
      "phone_number": "+19725971644",
      "tools_count": 17,
      "tool_category": "customer_facing",
      "purpose": "Customer service"
    },
    "riley_tech": {
      "name": "Riley Tech",
      "phone_number": "+18557683265",
      "tools_count": 6,
      "tool_category": "internal_ops",
      "purpose": "Internal operations support"
    }
  }
  ```

- Add `caller_identification` section documenting hybrid approach
- Add `role_based_access` section documenting permissions

#### 6.3 Update Direct Vapi Tools Plan

**File**: `.cursor/plans/direct_vapi_tools_architecture_eff922e1.plan.md`

- Mark `implement_conversionflow_ivr_close` as in progress
- Add new todos for tool reorganization
- Add new todos for role-based access control
- Update architecture section with phone number strategy

## Tool Migration Map

### Customer Facing Tools (17 tools)

| Current Location | New Location | Tool Name |

|-----------------|--------------|-----------|

| `odoo/schedule_appointment.json` | `customer_facing/appointments/schedule_appointment.json` | schedule_appointment |

| `odoo/reschedule_appointment.json` | `customer_facing/appointments/reschedule_appointment.json` | reschedule_appointment |

| `odoo/cancel_appointment.json` | `customer_facing/appointments/cancel_appointment.json` | cancel_appointment |

| `odoo/check_appointment_status.json` | `customer_facing/appointments/check_appointment_status.json` | check_appointment_status |

| `odoo/check_availability.json` | `customer_facing/appointments/check_availability.json` | check_availability |

| `odoo/create_service_request.json` | `customer_facing/leads_quotes/create_service_request.json` | create_service_request |

| `odoo/request_quote.json` | `customer_facing/leads_quotes/request_quote.json` | request_quote |

| `odoo/check_lead_status.json` | `customer_facing/leads_quotes/check_lead_status.json` | check_lead_status |

| `odoo/request_membership_enrollment.json` | `customer_facing/leads_quotes/request_membership_enrollment.json` | request_membership_enrollment |

| `odoo/create_complaint.json` | `customer_facing/complaints/create_complaint.json` | create_complaint |

| `brain_handlers/billing_inquiry.json` | `customer_facing/billing/billing_inquiry.json` | billing_inquiry |

| `brain_handlers/invoice_request.json` | `customer_facing/billing/invoice_request.json` | invoice_request |

| `brain_handlers/payment_terms_inquiry.json` | `customer_facing/billing/payment_terms_inquiry.json` | payment_terms_inquiry |

| `static/get_pricing.json` | `customer_facing/information/get_pricing.json` | get_pricing |

| `static/get_maintenance_plans.json` | `customer_facing/information/get_maintenance_plans.json` | get_maintenance_plans |

| `static/get_service_area_info.json` | `customer_facing/information/get_service_area_info.json` | get_service_area_info |

| `static/check_business_hours.json` | `customer_facing/information/check_business_hours.json` | check_business_hours |

### Internal OPS Tools (6+ tools)

| Current Location | New Location | Tool Name |

|-----------------|--------------|-----------|

| `brain_handlers/payroll_inquiry.json` | `internal_ops/hr/payroll_inquiry.json` | payroll_inquiry |

| `brain_handlers/onboarding_inquiry.json` | `internal_ops/hr/onboarding_inquiry.json` | onboarding_inquiry |

| `brain_handlers/hiring_inquiry.json` | `internal_ops/hr/hiring_inquiry.json` | hiring_inquiry |

| `brain_handlers/inventory_inquiry.json` | `internal_ops/operations/inventory_inquiry.json` | inventory_inquiry |

| `brain_handlers/purchase_request.json` | `internal_ops/operations/purchase_request.json` | purchase_request |

| NEW | `internal_ops/technician/ivr_close_sale.json` | ivr_close_sale |

## Role-Based Access Matrix

| Tool | Customer | Technician | HR | Billing | Manager | Executive |

|------|----------|------------|----|---------|---------|-----------|

| **Customer Tools** |

| create_service_request | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

| schedule_appointment | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

| request_quote | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

| billing_inquiry | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |

| invoice_request | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |

| **Internal Tools** |

| ivr_close_sale | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

| payroll_inquiry | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |

| onboarding_inquiry | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |

| hiring_inquiry | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |

| inventory_inquiry | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

| purchase_request | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

**Note:** Executives have access to all tools. Managers have access to most tools. Role detection happens automatically from Odoo job titles.

## Security Implementation

### Access Control Layers

1. **Phone Number Level**: 

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Customer Line: Public (published)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Internal OPS Line: Private (employees only)

2. **Assistant Level**: 

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - "Riley": Only customer tools attached
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - "Riley Tech": Only internal tools attached

3. **Backend Verification**: 

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Every tool call identifies caller
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Role determined from Odoo
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Permissions checked before processing

4. **Tool Level**: 

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Tools verify caller role in handler
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Return error if unauthorized

### Employee Identification Flow

```
Employee calls Internal OPS Line
    ↓
Vapi extracts caller phone
    ↓
Backend: identify_caller(caller_phone)
    ↓
Try Odoo hr.employee lookup (phone/mobile/work_phone)
    ↓
If found: Determine role from job title
    ↓
If not found: Try static roster
    ↓
If found: Return CallerIdentity with role
    ↓
If not found: Return CUSTOMER role (limited access)
    ↓
Check tool permissions for role
    ↓
Grant or deny access
```

## Testing Requirements

1. Test tool file migration (all JSON files moved correctly)
2. Test customer tools on Customer Line (Riley assistant)
3. Test internal tools on Internal OPS Line (Riley Tech assistant)
4. Test role identification from Odoo (all employee types)
5. Test fallback to static roster
6. Test access denial for unauthorized roles
7. Test `ivr_close_sale` with technician
8. Test HR tools with HR employee
9. Test billing tools with billing employee
10. Test manager access to all tools
11. Test executive access to all tools

## Deployment Steps

1. **Backend Deployment:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Deploy caller identification system
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Deploy role-based access control
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Deploy `ivr_close_sale` tool
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Deploy tool reorganization (move JSON files)

2. **Vapi Configuration:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update "Riley" assistant with customer tools only
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create "Riley Tech" assistant with internal tools
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Verify Customer Line phone number (+1-972-597-1644)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Create/verify Internal OPS Line phone number (+1-855-768-3265)

3. **Testing:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Test customer calls on Customer Line
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Test employee calls on Internal OPS Line
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Test role-based access for each employee type
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Test unauthorized access denial

4. **Documentation:**

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update README.md
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update context.json
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Share Internal OPS Line number with employees

## Dependencies

- Odoo `hr.employee` model accessible with phone fields
- Vapi API access for updating/creating assistants
- Twilio phone number (+1-855-768-3265) configured
- 8x8 call forwarding to Vapi for Customer Line
- Context7 docs for Vapi API calls
- Existing tool infrastructure (base.py, register_tools.py)

## Notes

- New employees work immediately when added to Odoo (no code changes)
- Multiple phone numbers per employee supported via Odoo fields
- Static roster provides fallback if Odoo is down
- Clear separation: customers vs employees
- Role-based permissions ensure security
- Future tools can be added to appropriate folder and assistant

## Implementation Status

### ✅ Completed (2026-01-26)

**ivr_close_sale Tool (ConversionFlow™):**
- ✅ Fully implemented and tested
- ✅ Handler: `src/vapi/tools/revenue/ivr_close_sale.py`
- ✅ Schema: `doc/vapi/tools/internal_ops/technician/ivr_close_sale.json`
- ✅ Registered in tool registry
- ✅ Role-based access control enforced (technician, manager, executive, admin)
- ✅ Odoo integration working (sale.order and crm.lead support)
- ✅ Error handling comprehensive (100% test pass rate)
- ✅ Tested with real Odoo data (40+ scenarios)
- ✅ Production-ready

**Key Features Implemented:**
- Dual model support (sale.order and crm.lead)
- State/stage updates via `action_confirm()` and stage management
- Chatter note creation with full audit trail
- Graceful degradation for partial failures
- Comprehensive error messages
- Install crew dispatch triggering

**Issues Fixed:**
- ✅ Removed invalid fields (`partner_phone`, `partner_email`) from sale.order query
- ✅ Implemented `action_confirm()` for readonly state field updates
- ✅ Improved error message extraction from Odoo responses
- ✅ Enhanced error categorization and user messaging

**Testing Results:**
- Total Tests: 40 scenarios
- Pass Rate: 100%
- Real Data Tests: 10/10 passed
- Scenario Variations: 5/5 passed
- Edge Cases: 7/7 passed
- Concurrent Load: 15/15 passed
- Average Response Time: 3.27 seconds

**Documentation:**
- Test Report: `doc/vapi/IVR_CLOSE_SALE_STRESS_TEST_REPORT.md`
- Testing Guide: `doc/vapi/TESTING_WITH_REAL_ODOO_DATA.md`
- Test Results: `.cursor/test_results_ivr_close_sale.json`