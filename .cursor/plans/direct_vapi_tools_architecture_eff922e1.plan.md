---
name: Direct Vapi Tools Architecture
overview: Create a comprehensive direct Vapi tools system that replaces HAEL routing with granular, operation-specific tools. Each tool directly calls brain handlers with parsed parameters, eliminating the HAEL command layer for Vapi integration.
todos:
  - id: create_tool_infrastructure
    content: Create src/vapi/tools/ directory structure with base.py, tool registry, and subdirectories (ops/, revenue/, core/, people/, utils/)
    status: completed
  - id: implement_base_handler
    content: Implement base tool handler in src/vapi/tools/base.py with common utilities (validation, parsing, error handling, response formatting, idempotency, audit logging)
    status: completed
    dependencies:
      - create_tool_infrastructure
  - id: implement_ops_service_request
    content: Implement create_service_request tool - calls _handle_service_request, creates Odoo lead, handles emergency qualification. Add warranty parameters (is_warranty, previous_service_id, previous_technician_id) and service area validation (35-mile radius check before creating lead)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_ops_schedule
    content: Implement schedule_appointment tool - calls _handle_schedule_appointment, creates Odoo calendar event. Add service area validation (35-mile radius check before creating appointment)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_ops_availability
    content: Implement check_availability tool - finds next available slots without creating appointment
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_ops_reschedule
    content: Implement reschedule_appointment tool - calls _handle_reschedule_appointment, updates Odoo calendar event
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_ops_cancel
    content: Implement cancel_appointment tool - calls _handle_cancel_appointment, cancels Odoo calendar event
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_ops_status
    content: Implement check_appointment_status tool - calls _handle_status_update, returns appointment details
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_revenue_quote
    content: Implement request_quote tool - calls _handle_quote_request, creates Odoo CRM lead with qualification
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_revenue_lead_status
    content: Implement check_lead_status tool - looks up CRM lead in Odoo, returns status and pipeline stage
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_revenue_membership
    content: Implement request_membership_enrollment tool - creates membership lead in Odoo, explains plans ($279 basic, $379 commercial), starts enrollment flow (sends contract, payment link)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_billing
    content: Implement billing_inquiry tool - calls _handle_billing_inquiry, returns balance and payment info
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_payment_terms
    content: Implement payment_terms_inquiry tool - calls _handle_payment_terms_inquiry, returns payment terms
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_invoice
    content: Implement invoice_request tool - calls _handle_invoice_request, returns/sends invoice
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_inventory
    content: Implement inventory_inquiry tool - calls _handle_inventory_inquiry, returns parts availability
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_purchase
    content: Implement purchase_request tool - calls _handle_purchase_request, creates purchase order request
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_pricing
    content: Implement get_pricing tool - uses calculate_service_pricing, returns pricing tier and fees
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_core_complaint
    content: Implement create_complaint tool - creates escalation ticket in Odoo, notifies management (Junior + Linda), returns professional response with callback offer. Must avoid prohibited phrases.
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_people_hiring
    content: Implement hiring_inquiry tool - calls _handle_hiring_inquiry, returns hiring requirements
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_people_onboarding
    content: Implement onboarding_inquiry tool - calls _handle_onboarding_inquiry, returns checklist and training
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_people_payroll
    content: Implement payroll_inquiry tool - calls _handle_payroll_inquiry, returns payroll summary
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_utils_business_hours
    content: Implement check_business_hours utility tool - returns current business hours status
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_utils_service_area
    content: Implement get_service_area_info utility tool - returns service area coverage and zone info
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_utils_maintenance_plans
    content: Implement get_maintenance_plans utility tool - returns maintenance plan options and pricing
    status: completed
    dependencies:
      - implement_base_handler
  - id: update_vapi_server_routing
    content: Update src/api/vapi_server.py to route tool calls to appropriate tool handlers based on tool name
    status: completed
    dependencies:
      - implement_ops_service_request
      - implement_ops_schedule
      - implement_revenue_quote
      - implement_core_billing
  - id: create_tool_schemas
    content: Create JSON schema files in doc/vapi/tools/ for all 22 tools with parameter definitions
    status: completed
    dependencies:
      - update_vapi_server_routing
  - id: update_kb_warranty_terms
    content: "Update doc/vapi/kb/customer_faq.md or policies.md with specific warranty terms: Repairs - 30-day labor warranty, Equipment - 1-year labor warranty"
    status: completed
  - id: enhance_brain_warranty_handling
    content: "Enhance _handle_service_request in src/brains/ops/handlers.py to handle warranty claims: lookup service history, assign to same technician, set priority to 2nd highest, waive diagnostic fee"
    status: completed
    dependencies:
      - implement_ops_service_request
  - id: update_system_prompt
    content: Update doc/vapi/system_prompt.md to reference specific tools instead of hael_route
    status: completed
    dependencies:
      - create_tool_schemas
  - id: add_tool_tests
    content: Create comprehensive tests in tests/test_vapi_tools/ for all tool handlers
    status: completed
    dependencies:
      - update_vapi_server_routing
  - id: update_context_json
    content: Update .cursor/context.json to reflect new tool-based architecture
    status: completed
    dependencies:
      - add_tool_tests
  - id: enhance_quote_financing_response
    content: Enhance request_quote tool to include financing options (Greensky, FTL, Microft) and price ranges in response
    status: completed
    dependencies:
      - implement_revenue_quote
  - id: enhance_pricing_customer_type
    content: Add customer_type parameter to get_pricing tool and enhance response to include trip charges and premiums
    status: completed
    dependencies:
      - implement_core_pricing
  - id: enhance_billing_payment_terms
    content: Enhance billing_inquiry tool to include payment terms by customer type and late fee information
    status: completed
    dependencies:
      - implement_core_billing
  - id: enhance_service_request_messaging
    content: Enhance create_service_request tool to check business hours/weekends, apply premiums, include warranty terms, and handle out-of-service area with polite rejection
    status: completed
    dependencies:
      - implement_ops_service_request
      - implement_utils_business_hours
  - id: enhance_schedule_messaging
    content: Enhance schedule_appointment tool to check business hours/weekends and handle out-of-service area
    status: completed
    dependencies:
      - implement_ops_schedule
      - implement_utils_business_hours
  - id: enhance_cancel_policy
    content: Enhance cancel_appointment tool to apply cancellation policy and include policy details in response
    status: completed
    dependencies:
      - implement_ops_cancel
  - id: add_sms_fallback
    content: Add SMS fallback mechanism in vapi_server.py for incomplete calls - create partial lead, send SMS, create follow-up task
    status: completed
    dependencies:
      - update_vapi_server_routing
  - id: update_system_prompt_prohibited
    content: Update system prompt with explicit prohibited phrases list and technical question detection guidance
    status: completed
    dependencies:
      - update_system_prompt
  - id: update_kb_financing
    content: Update KB with detailed financing information (Greensky, FTL, Microft) and cancellation policy
    status: completed
    dependencies:
      - update_kb_warranty_terms
  - id: implement_membership_enrollment
    content: Implement request_membership_enrollment tool to create membership lead and start enrollment flow (Test 2.4)
    status: completed
    dependencies:
      - implement_revenue_membership
  - id: enhance_odoo_lead_creation
    content: Enhance upsert_service_lead in odoo_leads.py to set lead source to "AI Voice Agent", map customer types (Residential→Retail, Commercial→Commercial, PM→Property Management), set pricing tiers, and apply appropriate tags (Tests 3.1-3.3)
    status: completed
    dependencies:
      - implement_ops_service_request
  - id: enhance_odoo_pm_fields
    content: Enhance lead creation to capture property management company name, set tax-exempt flag for Lessen, and set payment terms to Net 30 for PM customers (Test 3.3)
    status: completed
    dependencies:
      - enhance_odoo_lead_creation
  - id: verify_appointment_status
    content: Verify appointment creation sets status to "Scheduled" in Odoo Field Service module (Test 3.5)
    status: completed
    dependencies:
      - implement_ops_schedule
  - id: enhance_quote_creation
    content: Enhance _handle_quote_request to create sale.order quote (not just CRM lead), populate line items, set validity period, and implement approval workflow based on quote value (Test 3.6)
    status: completed
    dependencies:
      - implement_revenue_quote
  - id: implement_lead_email_notification
    content: Create send_new_lead_notification function in email_notifications.py to send emails to Junior, Linda, Dispatch, info@ with all lead details and Odoo link (Test 4.1)
    status: completed
    dependencies:
      - implement_ops_service_request
      - implement_ops_schedule
  - id: enhance_appointment_sms_confirmation
    content: Enhance send_service_confirmation_sms to include "Reply CONFIRM or CANCEL" instruction and ensure it's called immediately after appointment creation (Test 4.2)
    status: completed
    dependencies:
      - implement_ops_schedule
  - id: implement_appointment_reminder_sms
    content: Create send_appointment_reminder_sms function and background job system to send reminder SMS 2 hours before appointment (Test 4.3)
    status: completed
    dependencies:
      - implement_ops_schedule
  - id: enhance_escalation_notifications
    content: Enhance create_complaint tool to send immediate email and SMS notifications to Junior and Linda, and set priority to URGENT (Test 4.4)
    status: completed
    dependencies:
      - implement_core_complaint
  - id: implement_primeflow_same_day_sale
    content: Create request_same_day_sale tool for PrimeFlow™ - handles deposit collection, verification appointment, pipeline stages, install crew queuing, parts release, permit trigger (Test 5.1)
    status: pending
    dependencies:
      - implement_revenue_quote
  - id: implement_conversionflow_ivr_close
    content: Create ivr_close_sale tool or IVR endpoint for ConversionFlow™ - handles technician close line calls, proposal presentation, voice approval, deposit collection, pipeline updates (Test 5.2)
    status: pending
    dependencies:
      - implement_revenue_quote
  - id: verify_lead_qualification_routing
    content: Verify and enhance route_lead function to match exact routing requirements (Hot→Senior tech/sales immediately, Warm→Standard production, Cold→Nurture drip) (Test 5.3)
    status: completed
    dependencies:
      - implement_revenue_quote
  - id: enhance_financing_presentation
    content: Enhance request_quote tool to mention all financing partners, explain approval, offer to send info, collect contact info, include links in follow-ups (Test 5.4)
    status: completed
    dependencies:
      - implement_revenue_quote
  - id: enhance_followup_automation
    content: Enhance follow-up generation to match exact test sequences (immediate with financing/scheduling link, 2-day reminder with CSR task, maybe response sequence, lost deal reactivation) (Test 5.5)
    status: completed
    dependencies:
      - implement_revenue_quote
  - id: enhance_membership_enrollment_flow
    content: Enhance request_membership_enrollment tool to mention VIP benefits, send contract via SMS/email, include payment link, send confirmation (Test 5.6)
    status: completed
    dependencies:
      - implement_revenue_membership
  - id: implement_hiring_phone_screen
    content: Create conduct_hiring_phone_screen tool or IVR endpoint for hiring phone screen - asks questions, captures recording, calculates qualification score, creates candidate in Odoo (Test 6.1)
    status: pending
    dependencies:
      - implement_people_hiring
  - id: enhance_commission_calculation_tenure
    content: Enhance calculate_commission to support tenure-based rates (0-24 months = 16%, 4+ years = 20%) and equipment bonus (2.5%), integrate with Odoo payroll (Test 6.2)
    status: completed
    dependencies:
      - implement_people_payroll
  - id: implement_installation_bonus_calculation
    content: Create installation bonus calculation function that calculates total bonus, splits evenly among crew, integrates with Odoo payroll (Test 6.3)
    status: completed
    dependencies:
      - implement_people_payroll
  - id: implement_completion_ownership_rule
    content: Create completion ownership rule logic for commission splits on transferred work (40/60 split for approved transfers, 100% or forfeit for unapproved) (Test 6.4)
    status: completed
    dependencies:
      - implement_people_payroll
  - id: implement_time_tracking_system
    content: Create time tracking system for field technicians - clock in/out, job start/end, travel time, GPS logs, hours logging, approval workflow (Test 6.5)
    status: pending
    dependencies:
      - implement_people_payroll
  - id: verify_chat_lead_source
    content: Verify chat messages set lead source to "Website Chat" and ensure lead creation happens within 60 seconds (Test 7.3)
    status: completed
    dependencies:
      - implement_ops_service_request
      - implement_revenue_quote
  - id: enhance_chat_lead_notifications
    content: Ensure chat lead creation sends notifications to Dispatch Team, Linda, and info@hvacrfinest.com (Test 7.3)
    status: completed
    dependencies:
      - implement_ops_service_request
      - implement_revenue_quote
  - id: implement_chat_live_handoff
    content: Create live handoff system for chat during business hours - detect business hours, transfer to customer service, pass context, send notification (Test 7.4)
    status: completed
    dependencies:
      - implement_utils_business_hours
  - id: implement_chat_after_hours
    content: Add after-hours chat handling - detect after hours, show offline message, hide handoff option, create lead, schedule callback, send confirmation (Test 7.5)
    status: completed
    dependencies:
      - implement_utils_business_hours
  - id: add_chat_pre_qualification_endpoint
    content: Add backend endpoint to handle pre-qualification form submission with validation for required fields (Name, Email, Phone, Service needed) (Test 7.2 - backend part)
    status: completed
    dependencies:
      - create_tool_infrastructure
  - id: implement_dropped_call_handling
    content: Add dropped call handling - detect interruption, create partial lead with "Incomplete" status, send SMS, create callback task, save partial data (Test 8.1)
    status: completed
    dependencies:
      - implement_ops_service_request
      - add_sms_fallback
  - id: enhance_unclear_speech_handling
    content: Add unclear speech handling - detect low confidence, ask for clarification, remain patient, offer callback alternative (Test 8.2)
    status: completed
    dependencies:
      - implement_base_handler
  - id: enhance_long_call_context
    content: Enhance context tracking for long calls - track collected information, prevent repeating questions, maintain full context (Test 8.3)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_profanity_abuse_handling
    content: Add profanity/abuse detection and handling - detect inappropriate language, respond professionally, offer escalation (Test 8.4)
    status: completed
    dependencies:
      - implement_base_handler
  - id: enhance_multi_request_handling
    content: Enhance multi-request handling - detect multiple intents, ask for prioritization, process sequentially, create multiple leads, provide summary (Test 8.5)
    status: completed
    dependencies:
      - implement_base_handler
  - id: enhance_odoo_error_handling
    content: Enhance Odoo error handling - graceful degradation, local data capture, emergency notification, retry queue, user messaging (Test 8.6)
    status: completed
    dependencies:
      - implement_ops_service_request
      - implement_revenue_quote
  - id: enhance_duplicate_call_ux
    content: Enhance duplicate call UX - recognize returning customer, friendly message, reference existing appointment, prevent duplicate leads (Test 8.7)
    status: completed
    dependencies:
      - implement_ops_schedule
  - id: implement_wrong_number_detection
    content: Add wrong number detection - detect misdial phrases, respond gracefully, end call, do NOT create lead, log as non-actionable (Test 8.8)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_response_time_tracking
    content: Add response time tracking - measure call start to greeting, user input to response, track pauses >3 seconds, provide metrics endpoint (Test 9.1)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_call_completion_tracking
    content: Add call completion rate tracking - track total calls, completed calls, calculate rate, provide metrics endpoint, alert if below 90% (Test 9.2)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_data_accuracy_tracking
    content: Add data accuracy tracking - validate phone/address format, customer type, track accuracy rate, provide metrics endpoint (target 95%+) (Test 9.3)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_user_satisfaction_tracking
    content: Add user satisfaction tracking - collect ratings (1-5 scale), track all metrics, calculate average, provide metrics endpoint (target 4.0+) (Test 9.4)
    status: completed
    dependencies:
      - implement_base_handler
  - id: implement_issue_tracking_system
    content: Add issue tracking system - track common issues by category, log prohibited phrases, provide reporting dashboard, track frequency (Test 9.5)
    status: completed
    dependencies:
      - implement_base_handler
  - id: todo-1768346159367-vmjmdtssw
    content: Update context.json as per the all the above changes
    status: completed
---

# Direct Vapi Tools Architecture Plan

## Overview

Replace the single `hael_route` tool with a granular set of direct Vapi tools. Each tool maps to a specific business operation and directly invokes the appropriate brain handler, bypassing HAEL routing while maintaining all existing business logic.

## Architecture Change

**Current Flow:**

```
Vapi → hael_route tool → HAEL extraction/routing → Brain handler → Odoo
```

**New Flow:**

```
Vapi → Specific tool (e.g., create_service_request) → Brain handler → Odoo
```

## Directory Structure

Create new tool directory:

```
src/vapi/tools/
├── __init__.py
├── base.py                    # Base tool handler with common utilities
├── ops/
│   ├── __init__.py
│   ├── create_service_request.py
│   ├── schedule_appointment.py
│   ├── check_availability.py
│   ├── reschedule_appointment.py
│   ├── cancel_appointment.py
│   └── check_appointment_status.py
├── revenue/
│   ├── __init__.py
│   ├── request_quote.py
│   ├── check_lead_status.py
│   └── request_membership_enrollment.py
├── core/
│   ├── __init__.py
│   ├── billing_inquiry.py
│   ├── payment_terms_inquiry.py
│   ├── invoice_request.py
│   ├── inventory_inquiry.py
│   ├── purchase_request.py
│   ├── get_pricing.py
│   └── create_complaint.py
├── people/
│   ├── __init__.py
│   ├── hiring_inquiry.py
│   ├── onboarding_inquiry.py
│   └── payroll_inquiry.py
└── utils/
    ├── __init__.py
    ├── check_business_hours.py
    ├── get_service_area_info.py
    └── get_maintenance_plans.py
```

## Complete Tool List (23 Tools)

### OPS-BRAIN Tools (6 tools)

1. **create_service_request**

   - Purpose: Create emergency or standard service request (including warranty claims)
   - Parameters: customer_name, phone, email, address, issue_description, urgency, system_type, indoor_temperature_f, property_type, is_warranty (optional), previous_service_id (optional), previous_technician_id (optional)
   - Handler: `_handle_service_request` from `src/brains/ops/handlers.py` (enhanced for warranty handling)
   - Creates: Odoo CRM lead with emergency tagging, technician assignment
   - Warranty handling: When `is_warranty=true`, looks up service history, assigns to same technician, sets priority to 2nd highest, waives diagnostic fee
   - Service area validation: Validates address is within 35-mile radius before creating lead

2. **schedule_appointment**

   - Purpose: Schedule a new appointment
   - Parameters: customer_name, phone, email, address, service_type, preferred_time_windows, problem_description, property_type
   - Handler: `_handle_schedule_appointment` from `src/brains/ops/handlers.py`
   - Creates: Odoo calendar event, links to CRM lead
   - Service area validation: Validates address is within 35-mile radius before creating appointment

3. **check_availability**

   - Purpose: Check next available appointment slots
   - Parameters: service_type, preferred_date (optional), property_type
   - Handler: New handler or extend `_handle_schedule_appointment` with availability-only mode
   - Returns: List of available time slots

4. **reschedule_appointment**

   - Purpose: Reschedule existing appointment
   - Parameters: customer_name, phone, address, preferred_time_windows, appointment_id (optional)
   - Handler: `_handle_reschedule_appointment` from `src/brains/ops/handlers.py`
   - Updates: Odoo calendar event, sends confirmation

5. **cancel_appointment**

   - Purpose: Cancel existing appointment
   - Parameters: customer_name, phone, address, appointment_id (optional), cancellation_reason (optional)
   - Handler: `_handle_cancel_appointment` from `src/brains/ops/handlers.py`
   - Updates: Odoo calendar event (set active=False), updates CRM lead

6. **check_appointment_status**

   - Purpose: Check status of existing appointment
   - Parameters: customer_name, phone, address, appointment_id (optional)
   - Handler: `_handle_status_update` from `src/brains/ops/handlers.py`
   - Returns: Appointment details, technician info, ETA

### REVENUE-BRAIN Tools (3 tools)

7. **request_quote**

   - Purpose: Request installation/equipment quote
   - Parameters: customer_name, phone, email, address, property_type, square_footage, system_age_years, budget_range, timeline, system_type (optional)
   - Handler: `_handle_quote_request` from `src/brains/revenue/handlers.py`
   - Creates: Odoo CRM lead with qualification (hot/warm/cold), assigns to sales team

8. **check_lead_status**

   - Purpose: Check status of existing quote/lead
   - Parameters: customer_name, phone, email, lead_id (optional)
   - Handler: New handler to lookup CRM lead in Odoo
   - Returns: Lead status, pipeline stage, quote details

9. **request_membership_enrollment**

   - Purpose: Request maintenance membership enrollment
   - Parameters: customer_name, phone, email, address, property_type, membership_type (basic/commercial), system_details (optional)
   - Handler: New handler in REVENUE-BRAIN (or extend `_handle_quote_request` with membership type)
   - Creates: Odoo CRM lead with "Membership Inquiry" type
   - Explains: Plans ($279 basic, $379 commercial) and benefits
   - Starts: Enrollment flow (sends contract via SMS/email, payment link, enrollment confirmation)
   - Note: Can use `get_maintenance_plans` utility tool first to explain plans, then this tool to create lead and start enrollment

### CORE-BRAIN Tools (7 tools)

9. **billing_inquiry**

   - Purpose: Check billing information and outstanding balance
   - Parameters: customer_name, phone, email, invoice_number (optional)
   - Handler: `_handle_billing_inquiry` from `src/brains/core/handlers.py`
   - Returns: Balance, due date, payment methods, late fees

10. **payment_terms_inquiry**

    - Purpose: Get payment terms for customer segment
    - Parameters: customer_name, phone, email, property_type (optional)
    - Handler: `_handle_payment_terms_inquiry` from `src/brains/core/handlers.py`
    - Returns: Payment terms, due days, late fee policy

11. **invoice_request**

    - Purpose: Request invoice copy or send invoice
    - Parameters: customer_name, phone, email, invoice_number (optional)
    - Handler: `_handle_invoice_request` from `src/brains/core/handlers.py`
    - Returns: Invoice details, sends email if configured

12. **inventory_inquiry**

    - Purpose: Check parts/equipment availability
    - Parameters: part_name, part_number (optional), quantity (optional)
    - Handler: `_handle_inventory_inquiry` from `src/brains/core/handlers.py`
    - Returns: Inventory status, availability, reorder info

13. **purchase_request**

    - Purpose: Request parts/equipment purchase
    - Parameters: customer_name, phone, part_name, part_number, quantity, urgency
    - Handler: `_handle_purchase_request` from `src/brains/core/handlers.py`
    - Creates: Purchase order request in Odoo (if approved)

14. **get_pricing**

    - Purpose: Get service pricing for customer type
    - Parameters: property_type, service_type, urgency (optional), is_weekend (optional), is_after_hours (optional)
    - Handler: New handler using `calculate_service_pricing` from `src/brains/core/handlers.py`
    - Returns: Pricing tier, diagnostic fee, trip charge, premiums

15. **create_complaint**

    - Purpose: Create complaint/escalation ticket
    - Parameters: customer_name, phone, email, complaint_details, service_date (optional), service_id (optional)
    - Handler: New handler in CORE-BRAIN (or extend existing handler)
    - Creates: Escalation ticket in Odoo, notifies management (Junior + Linda)
    - Returns: Confirmation message, callback offer, management contact timeline (24 hours)
    - Note: AI must remain professional, avoid prohibited phrases, no promises

### PEOPLE-BRAIN Tools (3 tools)

15. **hiring_inquiry**

    - Purpose: Get hiring information and requirements
    - Parameters: None (general inquiry)
    - Handler: `_handle_hiring_inquiry` from `src/brains/people/handlers.py`
    - Returns: Hiring requirements, interview stages, approval process

16. **onboarding_inquiry**

    - Purpose: Get onboarding checklist and training info
    - Parameters: employee_email (optional), employee_name (optional)
    - Handler: `_handle_onboarding_inquiry` from `src/brains/people/handlers.py`
    - Returns: Onboarding checklist, training program details

17. **payroll_inquiry**

    - Purpose: Get payroll/commission information
    - Parameters: employee_email, employee_name (optional)
    - Handler: `_handle_payroll_inquiry` from `src/brains/people/handlers.py`
    - Returns: Payroll summary, commission rules, pay period info

### Utility Tools (3 tools)

18. **check_business_hours**

    - Purpose: Check if currently business hours
    - Parameters: None
    - Handler: New utility function
    - Returns: Is business hours, current time, next business day

19. **get_service_area_info**

    - Purpose: Get service area coverage information
    - Parameters: zip_code (optional), address (optional)
    - Handler: New utility function
    - Returns: Service area coverage, zone info, technician availability

20. **get_maintenance_plans**

    - Purpose: Get maintenance plan information and pricing
    - Parameters: property_type (optional)
    - Handler: New utility function using CORE pricing catalog
    - Returns: Plan options, pricing, benefits, enrollment info

## Implementation Details

### Base Tool Handler (`src/vapi/tools/base.py`)

Common functionality for all tools:

- Request validation
- Parameter parsing and normalization
- Error handling
- Response formatting
- Idempotency key generation
- Audit logging
- Odoo client initialization

### Tool Handler Pattern

Each tool follows this pattern:

```python
async def handle_tool_call(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str,
    conversation_context: str | None = None
) -> dict[str, Any]:
    """
    Handle tool call from Vapi.
    
    Returns:
        {
            "speak": str,  # Message for assistant
            "action": str,  # "completed" | "needs_human" | "error"
            "data": dict   # Structured result data
        }
    """
    # 1. Validate parameters
    # 2. Parse/normalize inputs
    # 3. Build HaelCommand or direct entity objects
    # 4. Call brain handler directly
    # 5. Format response
    # 6. Log audit trail
    # 7. Return Vapi-compatible response
```

### Vapi Server URL Integration

Update `src/api/vapi_server.py`:

- Add tool routing based on `toolCall.function.name`
- Map tool names to handler functions
- Maintain backward compatibility with `hael_route` (optional)
- Support multiple tools in single request

### Tool Schema Files

Create JSON schema files in `doc/vapi/tools/`:

- One schema file per tool
- Follow Vapi tool definition format
- Include parameter descriptions and examples
- Required vs optional fields clearly marked

## Migration Strategy

1. **Phase 1: Create tool infrastructure**

   - Create `src/vapi/tools/` directory structure
   - Implement base tool handler
   - Create tool registry

2. **Phase 2: Implement OPS tools (highest priority)**

   - Service request tool
   - Appointment tools (schedule, reschedule, cancel, check status, check availability)
   - Test with real Vapi calls

3. **Phase 3: Implement REVENUE tools**

   - Quote request tool
   - Lead status tool
   - Membership enrollment tool

4. **Phase 4: Implement CORE tools**

   - Billing, payment terms, invoice tools
   - Pricing tool
   - Inventory and purchase tools

5. **Phase 5: Implement PEOPLE tools**

   - Hiring, onboarding, payroll tools

6. **Phase 6: Implement utility tools**

   - Business hours, service area, maintenance plans

7. **Phase 7: Update Vapi configuration**

   - Deploy all tool schemas to Vapi
   - Update assistant configuration
   - Update system prompt to reference specific tools

8. **Phase 8: Deprecate hael_route (optional)**

   - Keep for backward compatibility initially
   - Monitor usage
   - Remove after full migration

## Key Design Decisions

1. **Parameter Parsing**: Tools parse parameters directly, no HAEL extraction needed
2. **Entity Building**: Tools build entity objects directly from parameters
3. **Brain Handler Reuse**: All existing brain handlers remain unchanged
4. **Response Format**: Consistent Vapi response format across all tools
5. **Error Handling**: Fail-closed approach - return `needs_human` on errors
6. **Idempotency**: Each tool generates idempotency key from parameters
7. **Audit Logging**: All tool calls logged to audit_log with tool name

## Files to Create

**New directories:**

- `src/vapi/tools/` (with subdirectories)
- `doc/vapi/tools/` (tool schema files)

**New files (estimated 35+ files):**

- Base handler: `src/vapi/tools/base.py`
- 23 tool handler files (22 original + 1 membership enrollment)
- 23 tool schema JSON files
- Tool registry: `src/vapi/tools/__init__.py`
- Tests: `tests/test_vapi_tools/` directory with tests for each tool

**Modified files:**

- `src/api/vapi_server.py` - Add tool routing
- `src/brains/ops/handlers.py` - Enhance `_handle_service_request` for warranty handling
- `doc/vapi/system_prompt.md` - Update to reference specific tools
- `doc/vapi/kb/customer_faq.md` or `policies.md` - Add specific warranty terms (30-day labor, 1-year equipment)
- `.cursor/context.json` - Update architecture description

## Testing Strategy

1. **Unit tests** for each tool handler
2. **Integration tests** with mocked brain handlers
3. **End-to-end tests** with real Vapi tool calls
4. **Backward compatibility tests** (if keeping hael_route)

## Benefits

1. **Direct control**: Vapi can call specific operations without routing overhead
2. **Better tool descriptions**: Each tool has focused, clear purpose
3. **Easier debugging**: Tool-specific logs and error handling
4. **Flexible usage**: Vapi can choose appropriate tool based on conversation context
5. **Maintainability**: Each tool is self-contained and testable

## Considerations

1. **Tool count**: 22 tools may be many for Vapi assistant - consider grouping related tools
2. **Parameter overlap**: Many tools share common parameters (name, phone, email) - use base handler utilities
3. **Response consistency**: Ensure all tools return consistent response format
4. **Error messages**: Provide clear, actionable error messages for missing parameters
5. **Documentation**: Each tool needs clear documentation for Vapi assistant
6. **Service area validation**: Tools that create leads/appointments must validate service area before proceeding
7. **Warranty handling**: Service request tool must handle warranty claims with special logic (same tech, no fee, priority)
8. **Complaint handling**: Complaint tool must remain professional and avoid prohibited phrases

## Test Coverage Analysis (Tests 1.6-1.18)

### Fully Covered Tests

**Test 1.8: Appointment Rescheduling** - ✅ `reschedule_appointment` tool

**Test 1.9: Appointment Cancellation** - ✅ `cancel_appointment` tool (needs cancellation policy logic)

**Test 1.11: Warranty Claim** - ✅ `create_service_request` with warranty parameters (needs warranty terms in response)

### Partially Covered Tests (Gaps Identified)

**Test 1.6: Installation Quote Request**

- ✅ `request_quote` tool covers lead creation and qualification
- ❌ **Gap**: Tool response must mention financing options (Greensky, FTL, Microft)
- ❌ **Gap**: Tool response must provide price range ($6,526-$8,441 based on system type)
- **Fix**: Enhance `request_quote` tool to include financing info and price ranges in response

**Test 1.7: Pricing Question - Multiple Tiers**

- ✅ `get_pricing` tool covers pricing calculation
- ❌ **Gap**: Tool needs `customer_type` parameter or must identify from conversation context
- ❌ **Gap**: Tool response must mention trip charges and emergency/weekend premiums when relevant
- **Fix**: Add `customer_type` parameter to `get_pricing` tool, enhance response formatting

**Test 1.10: Billing Inquiry**

- ✅ `billing_inquiry` tool covers balance lookup
- ❌ **Gap**: Tool response must mention payment terms based on customer type (Retail: Due on invoice, Commercial: Net 15, PM: Net 30)
- ❌ **Gap**: Tool response must mention 1% late fee if overdue
- **Fix**: Enhance `billing_inquiry` tool to include payment terms and late fee info

**Test 1.12: Complaint / Escalation**

- ✅ `create_complaint` tool covers escalation ticket creation
- ❌ **Gap**: System prompt must enforce prohibited phrases (no "We'll fix it for free", "I promise", etc.)
- **Fix**: Update system prompt with explicit prohibited phrases list

**Test 1.13: After-Hours Call (5pm-8am)**

- ✅ `check_business_hours` utility tool can detect after-hours
- ❌ **Gap**: Tools must mention after-hours premium in response (Retail: $187.50, Commercial: $350)
- ❌ **Gap**: Tools must use specific messaging: "We're booked at this time, our next availability is [weekday]. If an opening becomes available over the weekend, we'll reach out. To lock you in, we have [date/time] during the week."
- ❌ **Gap**: Emergency calls must get immediate dispatch authorization
- **Fix**: Enhance `create_service_request` and `schedule_appointment` tools to check business hours and adjust messaging/premiums

**Test 1.14: Weekend Call**

- ❌ **Gap**: Tools must mention "All weekends are booked out"
- ❌ **Gap**: Tools must offer "If an opening becomes available, we'll reach out"
- ❌ **Gap**: Tools must apply weekend premium if applicable
- ❌ **Gap**: Emergency calls must get priority consideration
- **Fix**: Enhance `create_service_request` and `schedule_appointment` tools to detect weekends and adjust messaging

**Test 1.15: Out of Service Area**

- ✅ Service area validation in `create_service_request` and `schedule_appointment`
- ✅ `get_service_area_info` utility tool for validation
- ❌ **Gap**: Tools must return polite rejection message: "We service within 35 miles of downtown Dallas"
- ❌ **Gap**: Tools must offer to take contact info for future expansion
- **Fix**: Enhance service area validation to return user-friendly rejection message with expansion offer

### Not Covered Tests (New Tools/Features Needed)

**Test 1.16: Complex Technical Question**

- ❌ **Gap**: No tool/mechanism to detect complex technical questions
- ❌ **Gap**: No transfer to human capability
- ❌ **Gap**: No callback task creation for after-hours technical questions
- **Fix**: Add `transfer_to_human` utility tool or enhance system prompt to detect technical questions and use existing transfer mechanism

**Test 1.17: Transfer to Human**

- ❌ **Gap**: No explicit transfer tool or mechanism
- ❌ **Gap**: No after-hours callback offer when transfer unavailable
- **Fix**: Add `transfer_to_human` utility tool or document existing Vapi transfer capability in system prompt

**Test 1.18: Voicemail & SMS Fallback**

- ❌ **Gap**: No SMS fallback mechanism for incomplete calls
- ❌ **Gap**: No partial lead creation with "Incomplete" status
- ❌ **Gap**: No follow-up task creation for incomplete calls
- **Fix**: Enhance `src/api/vapi_server.py` to detect incomplete calls and trigger SMS fallback via Twilio integration

## Additional Implementation Requirements

### Tool Response Enhancements

1. **request_quote tool**:

   - Include financing options (Greensky, FTL, Microft) in response
   - Include price range based on system type in response
   - Reference KB for detailed financing information

2. **get_pricing tool**:

   - Accept `customer_type` parameter (Retail, Default-PM, Commercial, Com-Lessen, Hotels/Multi)
   - Return complete pricing matrix including trip charges and premiums
   - Format response for AI to read naturally

3. **billing_inquiry tool**:

   - Include payment terms based on customer type
   - Include late fee information (1% if overdue)
   - Format response with all payment methods

4. **create_service_request tool**:

   - Check business hours and apply after-hours premium messaging
   - Check if weekend and apply weekend messaging
   - Include warranty terms in response when `is_warranty=true` (30-day labor, 1-year equipment)
   - Return polite rejection for out-of-service area with expansion offer

5. **schedule_appointment tool**:

   - Check business hours and adjust messaging
   - Check if weekend and apply weekend messaging
   - Return polite rejection for out-of-service area

6. **cancel_appointment tool**:

   - Apply cancellation policy if applicable
   - Include cancellation policy details in response

### System Prompt Updates

1. **Prohibited Phrases Enforcement**:

   - Add explicit list of prohibited phrases to system prompt
   - Include examples of what NOT to say for complaints
   - Reference `doc/vapi/kb/ops_intake_and_call_policy.md` for detailed guidance

2. **After-Hours/Weekend Messaging**:

   - Add specific messaging templates for after-hours calls
   - Add specific messaging templates for weekend calls
   - Include emergency vs non-emergency handling guidance

3. **Technical Question Detection**:

   - Add guidance for detecting complex technical questions
   - Add instructions for transferring to human or creating callback task
   - Include prohibited phrases for technical questions

### New Utility Tools/Features

1. **transfer_to_human** (optional utility tool):

   - Purpose: Initiate transfer to human customer service
   - Parameters: reason (optional), urgency (optional)
   - Handler: Uses Vapi transfer capability or creates callback task
   - Returns: Transfer status or callback confirmation

2. **SMS Fallback Mechanism** (in `src/api/vapi_server.py`):

   - Detect incomplete calls (call ended before completion)
   - Create partial lead with "Incomplete" status
   - Send SMS: "Thanks for calling HVACR FINEST. We'd love to help! Please reply with your service needs or call us back at (972) 372-4458."
   - Create follow-up task in Odoo
   - Notify dispatch team

### Knowledge Base Updates

1. **Financing Information** (`doc/vapi/kb/customer_faq.md`):

   - Add detailed information about Greensky, FTL, Microft
   - Include approval process and terms
   - Reference in `request_quote` tool response

2. **Warranty Terms** (`doc/vapi/kb/policies.md` or `customer_faq.md`):

   - Add specific warranty terms: Repairs - 30-day labor warranty, Equipment - 1-year labor warranty
   - Reference in `create_service_request` tool response when warranty claim

3. **Cancellation Policy** (`doc/vapi/kb/policies.md`):

   - Add cancellation policy details
   - Reference in `cancel_appointment` tool response

## Test Coverage Analysis (Tests 2.1-2.5: HAEL Routing Tests)

**Note**: These tests verify routing to the correct brain. With direct Vapi tools, routing happens at the Vapi level (Vapi chooses which tool to call), but the end result should be the same - the correct brain handler gets called.

### Test 2.1: "My AC broke" → OPS-BRAIN

- ✅ **Covered**: `create_service_request` tool routes to OPS-BRAIN via `_handle_service_request`
- ✅ Creates Odoo lead with Emergency tag
- ✅ Routes to Emergency queue
- ✅ Schedules Emergency call
- **Status**: Fully covered

### Test 2.2: "How much for new system" → REVENUE-BRAIN

- ✅ **Covered**: `request_quote` tool routes to REVENUE-BRAIN via `_handle_quote_request`
- ✅ Gathers details (sq ft, system type)
- ✅ Creates Quote lead
- ✅ Starts Follow-up automation
- **Status**: Fully covered

### Test 2.3: "When is my payment due" → CORE-BRAIN

- ✅ **Covered**: `billing_inquiry` tool routes to CORE-BRAIN via `_handle_billing_inquiry`
- ✅ Looks up invoice in Odoo
- ✅ Provides Balance and due date
- **Status**: Fully covered

### Test 2.4: "I want to join maintenance club" → REVENUE-BRAIN

- ⚠️ **Partially Covered**: `get_maintenance_plans` utility tool can explain plans ($279 basic, $379 commercial)
- ❌ **Gap**: No tool to create Membership lead in Odoo
- ❌ **Gap**: No tool to start Enrollment flow
- **Fix**: Add `request_membership_enrollment` tool in REVENUE-BRAIN that:
  - Explains plans ($279 basic, $379 commercial)
  - Creates Membership lead in Odoo with "Membership Inquiry" type
  - Starts enrollment flow (sends contract, payment link, etc.)
  - Or enhance `get_maintenance_plans` to optionally create lead when customer expresses interest
- **Status**: Needs new tool or enhancement

### Test 2.5: "I have a complaint" → CORE-BRAIN

- ✅ **Covered**: `create_complaint` tool routes to CORE-BRAIN
- ✅ Creates escalation ticket
- ✅ Notifies Junior + Linda immediately
- **Status**: Fully covered

## Test Coverage Analysis (Tests 3.1-3.7: Odoo Integration Tests)

**Note**: These tests verify that Odoo integration correctly creates leads, appointments, quotes, and invoices with all required fields and proper routing.

### Test 3.1: Lead Creation - Residential

- ✅ **Covered**: `create_service_request` and `schedule_appointment` tools create leads via `upsert_service_lead`
- ⚠️ **Gap**: Lead source field not set to "AI Voice Agent"
- ⚠️ **Gap**: Customer type not explicitly set to "Retail" (property_type="residential" should map to Retail)
- ⚠️ **Gap**: Tags may not be correctly applied (beyond Emergency tag)
- **Fix**: Enhance `upsert_service_lead` in `src/integrations/odoo_leads.py` to:
  - Set `source_id` or `source` field to "AI Voice Agent" (or find/create source record)
  - Map `property_type="residential"` to customer type "Retail" in Odoo
  - Apply appropriate tags based on service type and customer type
- **Status**: Partially covered, needs enhancement

### Test 3.2: Lead Creation - Commercial

- ✅ **Covered**: `create_service_request` tool creates leads
- ⚠️ **Gap**: Customer type not explicitly set to "Commercial"
- ⚠️ **Gap**: Pricing tier not set to "Com Pricing"
- ⚠️ **Gap**: Commercial-specific fields may not be captured
- **Fix**: Enhance `upsert_service_lead` to:
  - Map `property_type="commercial"` to customer type "Commercial"
  - Set pricing tier to "Com Pricing" (may require custom field or tag)
  - Capture commercial-specific fields if available
- **Status**: Partially covered, needs enhancement

### Test 3.3: Lead Creation - Property Management

- ✅ **Covered**: `create_service_request` tool creates leads
- ⚠️ **Gap**: Customer type not explicitly set to "Property Management"
- ⚠️ **Gap**: Pricing tier not set to "Default-PM"
- ⚠️ **Gap**: Property management company name not captured
- ⚠️ **Gap**: Tax-exempt flag not set (if Lessen)
- ⚠️ **Gap**: Payment terms not set to "Net 30"
- **Fix**: Enhance `upsert_service_lead` to:
  - Map `property_type="property_management"` to customer type "Property Management"
  - Set pricing tier to "Default-PM"
  - Capture property management company name (may need new entity field)
  - Set tax-exempt flag if applicable (Lessen)
  - Set payment terms to "Net 30" (may require custom field or tag)
- **Status**: Partially covered, needs enhancement

### Test 3.4: Lead Routing - Geographic Zones

- ✅ **Covered**: `assign_technician` function in `src/brains/ops/tech_roster.py` handles geographic routing
- ✅ DeSoto (Home Zone) → Junior
- ✅ Arlington (West Zone) → Bounthon
- ✅ Rockwall (East Zone) → Aubry
- ✅ Tech skills and availability considered
- **Status**: Fully covered (assuming tech_roster implementation is correct)

### Test 3.5: Appointment Creation in Odoo Field Service

- ✅ **Covered**: `schedule_appointment` tool creates appointments via `create_appointment` in `src/integrations/odoo_appointments.py`
- ✅ Assigned to correct technician
- ✅ Scheduled for correct date/time
- ✅ Duration matches service type
- ✅ Address populated
- ✅ Customer linked
- ✅ Service type set
- ⚠️ **Gap**: Status may not be explicitly set to "Scheduled" (depends on Odoo Field Service module implementation)
- **Fix**: Verify appointment status is set correctly in `create_appointment` method
- **Status**: Mostly covered, verify status field

### Test 3.6: Quote Generation

- ✅ **Covered**: `request_quote` tool creates quote leads via `_handle_quote_request` in REVENUE-BRAIN
- ⚠️ **Gap**: Quote may not be created in Sales/Quotes module (may only create CRM lead)
- ⚠️ **Gap**: Line items may not be populated based on system type
- ⚠️ **Gap**: Quote validity period may not be set
- ⚠️ **Gap**: Quote status and approval workflow (>$20K to Junior, mid-value to Linda, <$20K auto-approved) may not be implemented
- **Fix**: Enhance `_handle_quote_request` in `src/brains/revenue/handlers.py` to:
  - Create quote in `sale.order` model (not just CRM lead)
  - Populate line items based on system type and square footage
  - Set quote validity period
  - Implement approval workflow based on quote value
  - Assign to appropriate user (Junior/Linda) based on value
- **Status**: Partially covered, needs enhancement

### Test 3.7: Invoice Lookup

- ✅ **Covered**: `billing_inquiry` tool looks up invoices via `_handle_billing_inquiry` in CORE-BRAIN
- ✅ Finds invoice by customer name or account
- ✅ Provides: Total amount, Amount paid, Balance due, Due date
- ✅ Mentions payment methods
- ✅ Mentions late fees if overdue
- **Status**: Fully covered (assuming handler implementation is correct)

## Updated Todos for Test Coverage

- id: enhance_quote_financing_response

content: Enhance request_quote tool to include financing options (Greensky, FTL, Microft) and price ranges in response

dependencies: [implement_revenue_quote]

- id: enhance_pricing_customer_type

content: Add customer_type parameter to get_pricing tool and enhance response to include trip charges and premiums

dependencies: [implement_core_pricing]

- id: enhance_billing_payment_terms

content: Enhance billing_inquiry tool to include payment terms by customer type and late fee information

dependencies: [implement_core_billing]

- id: enhance_service_request_messaging

content: Enhance create_service_request tool to check business hours/weekends, apply premiums, include warranty terms, and handle out-of-service area with polite rejection

dependencies: [implement_ops_service_request, implement_utils_business_hours]

- id: enhance_schedule_messaging

content: Enhance schedule_appointment tool to check business hours/weekends and handle out-of-service area

dependencies: [implement_ops_schedule, implement_utils_business_hours]

- id: enhance_cancel_policy

content: Enhance cancel_appointment tool to apply cancellation policy and include policy details in response

dependencies: [implement_ops_cancel]

- id: add_sms_fallback

content: Add SMS fallback mechanism in vapi_server.py for incomplete calls - create partial lead, send SMS, create follow-up task

dependencies: [update_vapi_server_routing]

- id: update_system_prompt_prohibited

content: Update system prompt with explicit prohibited phrases list and technical question detection guidance

dependencies: [update_system_prompt]

- id: update_kb_financing

content: Update KB with detailed financing information (Greensky, FTL, Microft) and cancellation policy

dependencies: [update_kb_warranty_terms]

- id: implement_membership_enrollment

content: Implement request_membership_enrollment tool to create membership lead and start enrollment flow (Test 2.4)

dependencies: [implement_revenue_membership]

- id: enhance_odoo_lead_creation

content: Enhance upsert_service_lead in odoo_leads.py to set lead source to "AI Voice Agent", map customer types (Residential→Retail, Commercial→Commercial, PM→Property Management), set pricing tiers, and apply appropriate tags (Tests 3.1-3.3)

dependencies: [implement_ops_service_request]

- id: enhance_odoo_pm_fields

content: Enhance lead creation to capture property management company name, set tax-exempt flag for Lessen, and set payment terms to Net 30 for PM customers (Test 3.3)

dependencies: [enhance_odoo_lead_creation]

- id: verify_appointment_status

content: Verify appointment creation sets status to "Scheduled" in Odoo Field Service module (Test 3.5)

dependencies: [implement_ops_schedule]

- id: enhance_quote_creation

content: Enhance _handle_quote_request to create sale.order quote (not just CRM lead), populate line items, set validity period, and implement approval workflow based on quote value (Test 3.6)

dependencies: [implement_revenue_quote]

## Test Coverage Analysis (Tests 4.1-4.4: Notification Tests)

**Note**: These tests verify that email and SMS notifications are sent correctly for leads, appointments, and escalations.

### Test 4.1: Email Notifications - New Lead

- ⚠️ **Partially Covered**: `send_emergency_staff_notification` exists for emergency leads
- ❌ **Gap**: No general lead notification function for non-emergency leads
- ❌ **Gap**: Recipients may not include all required: Junior, Linda, Dispatch Team, info@hvacrfinest.com
- ❌ **Gap**: Email content may not include all required fields: Customer name, Phone, Address, Service type, Priority level, Assigned technician, Link to Odoo lead
- **Fix**: Create `send_new_lead_notification` function in `src/integrations/email_notifications.py` that:
  - Sends to: Junior, Linda, Dispatch Team, info@hvacrfinest.com
  - Includes all required fields in email body
  - Includes link to Odoo lead
  - Called from `create_service_request` and `schedule_appointment` tools after lead creation
- **Status**: Partially covered, needs new function

### Test 4.2: SMS Notifications - Appointment Confirmation

- ✅ **Covered**: `send_service_confirmation_sms` exists in `src/integrations/twilio_sms.py`
- ✅ Contains: Date, Time, Technician name, Service type
- ⚠️ **Gap**: May not contain "Reply CONFIRM or CANCEL" text
- ⚠️ **Gap**: May not be sent within 2 minutes (depends on when tool is called)
- **Fix**: Enhance `send_service_confirmation_sms` to:
  - Include "Reply CONFIRM or CANCEL" instruction
  - Ensure it's called immediately after appointment creation (within tool handler)
- **Status**: Mostly covered, needs enhancement

### Test 4.3: SMS Reminder - 2 Hours Before Appointment

- ❌ **Gap**: No SMS reminder function exists
- ❌ **Gap**: No scheduled job/background task to send reminders
- ❌ **Gap**: No mechanism to track appointments and send reminders at correct time
- **Fix**: Create `send_appointment_reminder_sms` function in `src/integrations/twilio_sms.py` and:
  - Create background job system (using existing `jobs` table) to schedule reminder SMS
  - Job should be created when appointment is scheduled
  - Job should execute 2 hours before appointment time
  - SMS should contain: "Your HVACR FINEST appointment is in 2 hours", Technician name, Service type, Reply option to reschedule
  - Or use Odoo's scheduled actions/automation if available
- **Status**: Not covered, needs new feature

### Test 4.4: Escalation Notification - Management

- ✅ **Covered**: `create_complaint` tool creates escalation ticket
- ⚠️ **Gap**: May not send email to Junior and Linda immediately
- ⚠️ **Gap**: May not send SMS to Junior and Linda immediately
- ⚠️ **Gap**: Priority may not be flagged as URGENT in Odoo
- **Fix**: Enhance `create_complaint` tool handler to:
  - Send immediate email notifications to Junior and Linda using `send_email` function
  - Send immediate SMS notifications to Junior and Linda using Twilio SMS
  - Set priority to URGENT in escalation ticket
  - Use existing `send_emergency_staff_notification` pattern or create new escalation notification function
- **Status**: Partially covered, needs enhancement

## Updated Todos for Notification Tests

- id: implement_lead_email_notification

content: Create send_new_lead_notification function in email_notifications.py to send emails to Junior, Linda, Dispatch, info@ with all lead details and Odoo link (Test 4.1)

dependencies: [implement_ops_service_request, implement_ops_schedule]

- id: enhance_appointment_sms_confirmation

content: Enhance send_service_confirmation_sms to include "Reply CONFIRM or CANCEL" instruction and ensure it's called immediately after appointment creation (Test 4.2)

dependencies: [implement_ops_schedule]

- id: implement_appointment_reminder_sms

content: Create send_appointment_reminder_sms function and background job system to send reminder SMS 2 hours before appointment (Test 4.3)

dependencies: [implement_ops_schedule]

- id: enhance_escalation_notifications

content: Enhance create_complaint tool to send immediate email and SMS notifications to Junior and Linda, and set priority to URGENT (Test 4.4)

dependencies: [implement_core_complaint]

## Test Coverage Analysis (Tests 5.1-5.6: REVENUE-BRAIN - SALES PROTOCOLS)

**Note**: These tests verify advanced sales protocols including PrimeFlow™, ConversionFlow™, lead qualification, financing, follow-up automation, and membership enrollment.

### Test 5.1: PrimeFlow™ - Same-Day Online Sales

- ❌ **Not Covered**: No PrimeFlow™ implementation exists
- ❌ **Gap**: No tool/mechanism to handle same-day sales requests
- ❌ **Gap**: No deposit collection mechanism
- ❌ **Gap**: No pipeline stage management (Quote Approved - Hold, Fast verification dispatch, Paused | Return Same Day, Install released, Completed)
- ❌ **Gap**: No verification appointment scheduling (30-45 min tech inspection)
- ❌ **Gap**: No install crew queuing
- ❌ **Gap**: No parts release notification
- ❌ **Gap**: No permit auto-trigger
- ❌ **Gap**: No controls for deposit requirement and photo requirements
- **Fix**: Create `request_same_day_sale` tool in REVENUE-BRAIN that:
  - Collects deposit (requires payment integration)
  - Creates quote with "Quote Approved - Hold" stage
  - Schedules verification appointment (30-45 min)
  - Assigns senior tech (Junior)
  - Queues install crew
  - Triggers parts release notification
  - Auto-triggers permit
  - Enforces deposit and photo requirements
  - Creates audit trail
- **Status**: Not covered, needs new feature

### Test 5.2: ConversionFlow™ - IVR Closing System

- ❌ **Not Covered**: No ConversionFlow™ implementation exists
- ❌ **Gap**: No IVR "Close Line" mechanism for technicians
- ❌ **Gap**: No proposal presentation system
- ❌ **Gap**: No Good/Better/Best options presentation
- ❌ **Gap**: No voice approval recording
- ❌ **Gap**: No deposit collection via IVR
- ❌ **Gap**: No pipeline stage management (Quote Approved - Waiting for Parts)
- ❌ **Gap**: No recording storage
- ❌ **Gap**: No financing selection recording
- ❌ **Gap**: No consent/signature capture
- ❌ **Gap**: No auto-dispatch of install crew
- ❌ **Gap**: No controls for field discounting prevention and financing enforcement
- **Fix**: Create `ivr_close_sale` tool or special IVR endpoint that:
  - Accepts technician call to "Close Line"
  - Presents proposal to customer via AI
  - Shows Good/Better/Best options
  - Presents financing options
  - Records customer voice approval
  - Collects deposit
  - Updates pipeline to "Quote Approved - Waiting for Parts"
  - Stores recording
  - Records financing selection
  - Captures consent/signature
  - Auto-dispatches install crew
  - Enforces no field discounting
  - Logs all closings
- **Status**: Not covered, needs new feature

### Test 5.3: Lead Qualification - Hot/Warm/Cold

- ✅ **Covered**: `qualify_lead` function exists in `src/brains/revenue/qualification.py`
- ✅ Hot lead qualification logic exists
- ✅ Warm lead qualification logic exists
- ✅ Cold lead qualification logic exists
- ✅ Routing logic exists (`route_lead` function)
- ⚠️ **Gap**: Routing may not exactly match test expectations (Hot → Senior tech or sales immediately, Warm → Standard production, Cold → Nurture drip)
- **Fix**: Verify and enhance `route_lead` function to match exact routing requirements:
  - Hot → Senior tech or sales immediately
  - Warm → Standard production, follow-up automation
  - Cold → Nurture drip, review building
- **Status**: Mostly covered, needs verification

### Test 5.4: Financing Presentation

- ⚠️ **Partially Covered**: Plan mentions financing options in `request_quote` tool response
- ⚠️ **Gap**: May not mention all three partners (Greensky, FTL, Microft)
- ⚠️ **Gap**: May not explain "We can help you get approved quickly"
- ⚠️ **Gap**: May not offer to send financing information
- ⚠️ **Gap**: May not collect email/phone for financing info
- ⚠️ **Gap**: Follow-up automation may not include financing links
- **Fix**: Enhance `request_quote` tool to:
  - Mention all three financing partners (Greensky, FTL, Microft)
  - Explain approval process
  - Offer to send financing information
  - Collect email/phone if customer interested
  - Include financing links in follow-up automation
- **Status**: Partially covered, needs enhancement

### Test 5.5: Follow-Up Automation

- ✅ **Covered**: `generate_lead_followups` and `generate_quote_followups` exist in `src/brains/revenue/followups.py`
- ✅ Immediate thank-you text/email
- ✅ 2-day reminder exists
- ⚠️ **Gap**: Follow-up sequences may not exactly match test requirements:
  - Test requires: Immediate thank-you text + financing options + scheduling link
  - Test requires: 2 days no response: Auto reminder text + email + call task for CSR
  - Test requires: "Maybe" response: Day 1 education email, Day 3 testimonial, Day 7 financing reminder
  - Test requires: Lost deal: Day 30 check-in, Day 60 seasonal promo, Day 90 rebate alert
- **Fix**: Enhance follow-up generation to match exact test sequences:
  - Quote sent: Immediate thank-you with financing options and scheduling link
  - 2 days no response: Reminder text + email + call task for CSR
  - "Maybe" response: Track and send Day 1 education, Day 3 testimonial, Day 7 financing reminder
  - Lost deal: Track and send Day 30 check-in, Day 60 seasonal promo, Day 90 rebate alert
- **Status**: Partially covered, needs enhancement

### Test 5.6: Membership Enrollment

- ✅ **Covered**: `request_membership_enrollment` tool added to plan
- ✅ Explains Basic ($279/year) vs Commercial ($379/year)
- ✅ Creates membership lead in Odoo
- ⚠️ **Gap**: May not mention VIP contract benefits
- ⚠️ **Gap**: May not send contract via SMS/email
- ⚠️ **Gap**: May not include payment link
- ⚠️ **Gap**: May not send enrollment confirmation
- **Fix**: Enhance `request_membership_enrollment` tool to:
  - Mention VIP contract benefits
  - Send contract via SMS/email
  - Include payment link
  - Send enrollment confirmation after payment
- **Status**: Partially covered, needs enhancement

## Updated Todos for REVENUE-BRAIN Sales Protocols

- id: implement_primeflow_same_day_sale

content: Create request_same_day_sale tool for PrimeFlow™ - handles deposit collection, verification appointment, pipeline stages, install crew queuing, parts release, permit trigger (Test 5.1)

dependencies: [implement_revenue_quote]

- id: implement_conversionflow_ivr_close

content: Create ivr_close_sale tool or IVR endpoint for ConversionFlow™ - handles technician close line calls, proposal presentation, voice approval, deposit collection, pipeline updates (Test 5.2)

dependencies: [implement_revenue_quote]

- id: verify_lead_qualification_routing

content: Verify and enhance route_lead function to match exact routing requirements (Hot→Senior tech/sales immediately, Warm→Standard production, Cold→Nurture drip) (Test 5.3)

dependencies: [implement_revenue_quote]

- id: enhance_financing_presentation

content: Enhance request_quote tool to mention all financing partners, explain approval, offer to send info, collect contact info, include links in follow-ups (Test 5.4)

dependencies: [implement_revenue_quote]

- id: enhance_followup_automation

content: Enhance follow-up generation to match exact test sequences (immediate with financing/scheduling link, 2-day reminder with CSR task, maybe response sequence, lost deal reactivation) (Test 5.5)

dependencies: [implement_revenue_quote]

- id: enhance_membership_enrollment_flow

content: Enhance request_membership_enrollment tool to mention VIP benefits, send contract via SMS/email, include payment link, send confirmation (Test 5.6)

dependencies: [implement_revenue_membership]

## Test Coverage Analysis (Tests 6.1-6.5: PEOPLE-BRAIN TESTS)

**Note**: These tests verify hiring phone screens, commission calculations, installation bonuses, completion ownership rules, and time tracking.

### Test 6.1: AI Hiring Phone Screen

- ❌ **Not Covered**: No hiring phone screen IVR flow exists
- ❌ **Gap**: No IVR endpoint for hiring line
- ❌ **Gap**: No phone screen question flow (certifications, experience, availability, salary, interest)
- ❌ **Gap**: No recording capture mechanism
- ❌ **Gap**: No qualification score calculation
- ❌ **Gap**: No candidate record creation in Odoo
- ❌ **Gap**: No phone screen recording attachment to Odoo
- ❌ **Gap**: No interview stage assignment or rejection handling
- **Fix**: Create `conduct_hiring_phone_screen` tool or IVR endpoint that:
  - Handles hiring IVR line calls
  - Asks questions: certifications (EPA 608, TDLR), years of experience, availability, salary expectations, why interested
  - Captures recording
  - Calculates qualification score
  - Creates candidate record in Odoo
  - Attaches phone screen recording
  - Moves to "Interview" stage if qualified, or polite rejection if not
- **Status**: Not covered, needs new feature

### Test 6.2: Commission Calculation - Service Work

- ⚠️ **Partially Covered**: `calculate_commission` function exists in `src/brains/people/payroll_rules.py`
- ❌ **Gap**: Commission rates don't match test requirements:
  - Test requires: 0-24 months tenure = 16%, 4+ years = 20%
  - Current code: Fixed 15% for repairs, 5% for installs
- ❌ **Gap**: No tenure-based commission calculation
- ❌ **Gap**: No equipment bonus calculation (2.5% of equipment sold)
- ❌ **Gap**: No automatic calculation in Odoo (currently just Python function)
- ❌ **Gap**: No payroll queue integration
- **Fix**: Enhance commission calculation to:
  - Accept technician tenure (months/years)
  - Apply tenure-based rates (0-24 months = 16%, 4+ years = 20%)
  - Calculate equipment bonus (2.5% of equipment sold)
  - Integrate with Odoo payroll module for automatic calculation
  - Add to payroll queue automatically
- **Status**: Partially covered, needs enhancement

### Test 6.3: Installation Bonus Calculation

- ❌ **Not Covered**: No installation bonus calculation exists
- ❌ **Gap**: No bonus calculation logic
- ❌ **Gap**: No split calculation for install crews
- ❌ **Gap**: No Odoo integration for automatic calculation
- ❌ **Gap**: No payroll integration
- **Fix**: Create installation bonus calculation function that:
  - Calculates total bonus based on system type (e.g., Complete Split System = $1,050)
  - Splits bonus evenly among install crew members
  - Integrates with Odoo for automatic calculation
  - Adds to payroll automatically
- **Status**: Not covered, needs new feature

### Test 6.4: Completion Ownership Rule

- ❌ **Not Covered**: No completion ownership rule exists
- ❌ **Gap**: No commission split logic for transferred work
- ❌ **Gap**: No "approved transfer" flag tracking
- ❌ **Gap**: No 40/60 split calculation (Tech A sold = 40%, Tech B completed = 60%)
- ❌ **Gap**: No handling for unapproved transfers (Tech A gets 100% or forfeits)
- **Fix**: Create completion ownership rule logic that:
  - Tracks "approved transfer" flag when work is transferred
  - Calculates commission split: Tech A (sold) = 40%, Tech B (completed) = 60%
  - Handles unapproved transfers: Tech A gets 100% or forfeits if doesn't return
  - Integrates with Odoo commission calculation
- **Status**: Not covered, needs new feature

### Test 6.5: Time Tracking - Field Technician

- ❌ **Not Covered**: No time tracking system exists
- ❌ **Gap**: No clock-in/clock-out mechanism
- ❌ **Gap**: No job start/end tracking
- ❌ **Gap**: No travel time calculation
- ❌ **Gap**: No GPS-linked job logs
- ❌ **Gap**: No hours logging for payroll
- ❌ **Gap**: No approval workflow (Dispatch → Ops Manager → HR → Owner)
- **Fix**: Create time tracking system that:
  - Allows technicians to clock in/out
  - Tracks job start/end times
  - Calculates travel time
  - Links GPS data if available
  - Logs hours for payroll
  - Implements approval workflow in Odoo
- **Status**: Not covered, needs new feature

## Updated Todos for PEOPLE-BRAIN Tests

- id: implement_hiring_phone_screen

content: Create conduct_hiring_phone_screen tool or IVR endpoint for hiring phone screen - asks questions, captures recording, calculates qualification score, creates candidate in Odoo (Test 6.1)

dependencies: [implement_people_hiring]

- id: enhance_commission_calculation_tenure

content: Enhance calculate_commission to support tenure-based rates (0-24 months = 16%, 4+ years = 20%) and equipment bonus (2.5%), integrate with Odoo payroll (Test 6.2)

dependencies: [implement_people_payroll]

- id: implement_installation_bonus_calculation

content: Create installation bonus calculation function that calculates total bonus, splits evenly among crew, integrates with Odoo payroll (Test 6.3)

dependencies: [implement_people_payroll]

- id: implement_completion_ownership_rule

content: Create completion ownership rule logic for commission splits on transferred work (40/60 split for approved transfers, 100% or forfeit for unapproved) (Test 6.4)

dependencies: [implement_people_payroll]

- id: implement_time_tracking_system

content: Create time tracking system for field technicians - clock in/out, job start/end, travel time, GPS logs, hours logging, approval workflow (Test 6.5)

dependencies: [implement_people_payroll]

## Test Coverage Analysis (Tests 7.1-7.5: WEBSITE CHAT BOT TESTS)

**Note**: These tests verify website chat widget functionality, pre-qualification forms, lead creation, live handoff, and after-hours behavior.

### Test 7.1: Chat Widget Appearance

- ❌ **Not Covered**: No chat widget frontend implementation exists
- ❌ **Gap**: No chat widget component
- ❌ **Gap**: No widget positioning (bottom-right corner)
- ❌ **Gap**: No widget visibility on all pages
- ❌ **Gap**: No auto-expand after 3 seconds
- ❌ **Gap**: No brand colors applied
- ❌ **Gap**: No mobile responsive design
- **Fix**: Create frontend chat widget that:
  - Appears in bottom-right corner
  - Visible on all website pages
  - Auto-expands after 3 seconds (or stays collapsed)
  - Uses brand colors
  - Professional appearance
  - Mobile responsive
- **Status**: Not covered, needs frontend implementation (outside current plan scope - frontend work)

### Test 7.2: Chat Greeting & Pre-Qualification

- ⚠️ **Partially Covered**: Chat API endpoint exists (`/chat/message` in `src/api/chat.py`)
- ❌ **Gap**: No pre-qualification form in frontend
- ❌ **Gap**: No greeting message ("Hi! 👋 Welcome to HVAC-R Finest...")
- ❌ **Gap**: No required fields validation (Name, Email, Phone, Service needed)
- ❌ **Gap**: No form blocking until all fields filled
- **Fix**: 
  - Frontend: Create pre-qualification form with greeting and required fields
  - Backend: Add endpoint to handle pre-qualification form submission
  - Backend: Validate all required fields before proceeding
- **Status**: Partially covered, needs frontend form and backend validation

### Test 7.3: Chat Lead Creation

- ✅ **Covered**: Chat API endpoint processes messages and routes to brains
- ⚠️ **Gap**: Lead source may not be set to "Website Chat" (currently uses `LeadSource.PHONE` or `LeadSource.WEBSITE` based on channel)
- ⚠️ **Gap**: Lead creation may not happen immediately (within 60 seconds) - depends on brain handler
- ✅ **Covered**: Auto-assignment logic exists in brain handlers
- ⚠️ **Gap**: Notifications may not be sent to all required recipients (Dispatch Team, Linda, info@hvacrfinest.com)
- **Fix**: 
  - Ensure `LeadSource.WEBSITE` is used for chat messages (already handled via `Channel.CHAT`)
  - Verify lead creation happens immediately in brain handlers
  - Ensure notifications are sent to all required recipients when lead is created
- **Status**: Mostly covered, needs verification and notification enhancement

### Test 7.4: Live Handoff (Business Hours)

- ❌ **Not Covered**: No live handoff mechanism exists
- ❌ **Gap**: No business hours detection
- ❌ **Gap**: No live chat handoff to customer service
- ❌ **Gap**: No chat context passing to human
- ❌ **Gap**: No customer service notification
- **Fix**: Create live handoff system that:
  - Detects business hours (8am-5pm CST)
  - Provides handoff option during business hours
  - Transfers chat to customer service
  - Passes chat context to human
  - Sends notification to customer service
  - Ensures no information lost in transfer
- **Status**: Not covered, needs new feature

### Test 7.5: After-Hours Chat Behavior

- ❌ **Not Covered**: No after-hours detection or messaging
- ❌ **Gap**: No business hours check
- ❌ **Gap**: No after-hours message ("Our team is currently offline (8am-5pm CST)")
- ❌ **Gap**: No hiding of live handoff option after hours
- ⚠️ **Gap**: Lead creation may not schedule callback for next business day
- **Fix**: Add after-hours handling that:
  - Checks if current time is outside business hours (8am-5pm CST)
  - Shows message: "Our team is currently offline (8am-5pm CST)"
  - Hides live handoff option
  - Creates lead for follow-up
  - Schedules callback for next business day
  - Sends confirmation message with timeline
- **Status**: Not covered, needs new feature

## Updated Todos for WEBSITE CHAT BOT Tests

**Note**: Tests 7.1-7.2 require frontend work (chat widget, pre-qualification form) which is outside the scope of the current backend-focused plan. These should be tracked separately.

- id: verify_chat_lead_source

content: Verify chat messages set lead source to "Website Chat" and ensure lead creation happens within 60 seconds (Test 7.3)

dependencies: [implement_ops_service_request, implement_revenue_quote]

- id: enhance_chat_lead_notifications

content: Ensure chat lead creation sends notifications to Dispatch Team, Linda, and info@hvacrfinest.com (Test 7.3)

dependencies: [implement_ops_service_request, implement_revenue_quote]

- id: implement_chat_live_handoff

content: Create live handoff system for chat during business hours - detect business hours, transfer to customer service, pass context, send notification (Test 7.4)

dependencies: [implement_utils_business_hours]

- id: implement_chat_after_hours

content: Add after-hours chat handling - detect after hours, show offline message, hide handoff option, create lead, schedule callback, send confirmation (Test 7.5)

dependencies: [implement_utils_business_hours]

- id: add_chat_pre_qualification_endpoint

content: Add backend endpoint to handle pre-qualification form submission with validation for required fields (Name, Email, Phone, Service needed) (Test 7.2 - backend part)

dependencies: [create_tool_infrastructure]

**Frontend Work Required (Outside Current Plan Scope)**:

- Chat widget component (Test 7.1)
- Pre-qualification form UI (Test 7.2)
- Live handoff UI integration (Test 7.4)
- After-hours messaging UI (Test 7.5)

## Test Coverage Analysis (Tests 8.1-8.8: EDGE CASES & ERROR HANDLING)

**Note**: These tests verify system behavior under edge cases, errors, and unusual conditions.

### Test 8.1: Call Interruption / Dropped Call

- ⚠️ **Partially Covered**: Idempotency system exists to prevent duplicate processing
- ❌ **Gap**: No specific handling for dropped calls/interruptions
- ❌ **Gap**: No partial lead creation with "Incomplete" status
- ❌ **Gap**: No SMS sent to customer on dropped call ("We lost connection, please call back")
- ❌ **Gap**: No callback task creation in Odoo for incomplete calls
- ❌ **Gap**: No mechanism to save partial data from interrupted calls
- **Fix**: Add dropped call handling that:
  - Detects call interruption (via Vapi end-of-call-report or timeout)
  - Creates partial lead with "Incomplete" status
  - Sends SMS: "We lost connection, please call back"
  - Creates callback task in Odoo
  - Saves all captured data before interruption
- **Status**: Partially covered, needs enhancement

### Test 8.2: Unclear/Garbled Speech

- ⚠️ **Partially Covered**: Vapi handles speech recognition, but backend doesn't handle unclear input
- ❌ **Gap**: No specific handling for unclear/garbled speech
- ❌ **Gap**: No clarification request: "I'm sorry, I didn't catch that. Could you repeat?"
- ❌ **Gap**: No alternative offer: "Would you prefer to receive a callback?"
- ❌ **Gap**: No retry logic (doesn't give up after 1-2 failed attempts)
- **Fix**: Add unclear speech handling in tool handlers that:
  - Detects low confidence or unclear input
  - Asks for clarification: "I'm sorry, I didn't catch that. Could you repeat?"
  - Remains patient (allows multiple retries)
  - Offers callback alternative if multiple failures
- **Status**: Partially covered, needs enhancement (mostly Vapi-side, but backend should handle gracefully)

### Test 8.3: Very Long Call (>15 minutes)

- ✅ **Covered**: System maintains context via session_id and request_id
- ✅ **Covered**: Vapi maintains conversation context
- ⚠️ **Gap**: May not explicitly prevent repeating already-answered questions
- ⚠️ **Gap**: May not track what information has already been collected
- **Fix**: Enhance context tracking to:
  - Track collected information in session
  - Prevent repeating questions for already-collected data
  - Maintain full conversation context
- **Status**: Mostly covered, needs verification

### Test 8.4: Profanity / Abusive Language

- ❌ **Not Covered**: No profanity/abuse detection or handling
- ❌ **Gap**: No professional response: "I understand you're frustrated. Let me help resolve this."
- ❌ **Gap**: No escalation offer if abuse continues
- **Fix**: Add profanity/abuse handling that:
  - Detects inappropriate language (via Vapi or backend filtering)
  - Responds professionally: "I understand you're frustrated. Let me help resolve this."
  - Doesn't terminate call immediately
  - Offers escalation if abuse continues
- **Status**: Not covered, needs new feature

### Test 8.5: Multiple Issues in One Call

- ⚠️ **Partially Covered**: System can handle multiple tool calls, but may not handle sequential processing
- ❌ **Gap**: May not ask: "Let's handle these one at a time. Which is most urgent?"
- ❌ **Gap**: May not create multiple leads/tasks sequentially
- ❌ **Gap**: May not provide summary at end
- **Fix**: Enhance multi-request handling to:
  - Detect multiple intents in single call
  - Ask: "Let's handle these one at a time. Which is most urgent?"
  - Process requests sequentially
  - Create multiple leads/tasks as needed
  - Provide summary: "I've scheduled your service, sent your invoice, and you'll receive a quote within 24 hours"
- **Status**: Partially covered, needs enhancement

### Test 8.6: Odoo API Down / Integration Failure

- ⚠️ **Partially Covered**: Error handling exists, but may not have graceful degradation
- ✅ **Covered**: Fail-closed approach mentioned in vapi_server.py comments
- ❌ **Gap**: May not continue conversation when Odoo is down
- ❌ **Gap**: May not capture data locally when Odoo is down
- ❌ **Gap**: May not say: "I'm experiencing a technical issue but I've captured your information"
- ❌ **Gap**: May not send emergency notification to tech team
- ❌ **Gap**: May not provide alternative: "You'll receive a confirmation within 30 minutes"
- ❌ **Gap**: May not queue data for retry/manual entry
- **Fix**: Enhance Odoo error handling to:
  - Catch Odoo API failures
  - Continue conversation
  - Capture data locally (database or queue)
  - Say: "I'm experiencing a technical issue but I've captured your information"
  - Send emergency notification to tech team
  - Provide alternative: "You'll receive a confirmation within 30 minutes"
  - Queue data for retry/manual entry
- **Status**: Partially covered, needs enhancement

### Test 8.7: Duplicate Call Prevention

- ✅ **Covered**: Idempotency system exists (`IdempotencyChecker` in `src/utils/idempotency.py`)
- ✅ **Covered**: Uses call_id for idempotency in Odoo lead creation
- ⚠️ **Gap**: May not recognize returning customer with friendly message
- ⚠️ **Gap**: May not say: "Welcome back! I see you just called. Would you like to modify your appointment?"
- ⚠️ **Gap**: May not reference existing appointment
- **Fix**: Enhance duplicate call handling to:
  - Check for recent calls from same phone number
  - Recognize returning customer
  - Say: "Welcome back! I see you just called. Would you like to modify your appointment?"
  - Reference existing appointment/lead
  - Prevent duplicate lead creation
- **Status**: Mostly covered, needs enhancement for user experience

### Test 8.8: Wrong Number / Misdial

- ❌ **Not Covered**: No wrong number/misdial detection
- ❌ **Gap**: No detection of "Sorry, wrong number" or similar phrases
- ❌ **Gap**: May not respond: "No problem! Have a great day."
- ❌ **Gap**: May not end call gracefully
- ❌ **Gap**: May create lead even for wrong number
- **Fix**: Add wrong number detection that:
  - Detects phrases like "Sorry, wrong number", "Wrong number", "Misdial"
  - Responds: "No problem! Have a great day."
  - Ends call gracefully
  - Does NOT create lead
  - Logs call but marks as non-actionable
- **Status**: Not covered, needs new feature

## Updated Todos for EDGE CASES & ERROR HANDLING

- id: implement_dropped_call_handling

content: Add dropped call handling - detect interruption, create partial lead with "Incomplete" status, send SMS, create callback task, save partial data (Test 8.1)

dependencies: [implement_ops_service_request, add_sms_fallback]

- id: enhance_unclear_speech_handling

content: Add unclear speech handling - detect low confidence, ask for clarification, remain patient, offer callback alternative (Test 8.2)

dependencies: [implement_base_handler]

- id: enhance_long_call_context

content: Enhance context tracking for long calls - track collected information, prevent repeating questions, maintain full context (Test 8.3)

dependencies: [implement_base_handler]

- id: implement_profanity_abuse_handling

content: Add profanity/abuse detection and handling - detect inappropriate language, respond professionally, offer escalation (Test 8.4)

dependencies: [implement_base_handler]

- id: enhance_multi_request_handling

content: Enhance multi-request handling - detect multiple intents, ask for prioritization, process sequentially, create multiple leads, provide summary (Test 8.5)

dependencies: [implement_base_handler]

- id: enhance_odoo_error_handling

content: Enhance Odoo error handling - graceful degradation, local data capture, emergency notification, retry queue, user messaging (Test 8.6)

dependencies: [implement_ops_service_request, implement_revenue_quote]

- id: enhance_duplicate_call_ux

content: Enhance duplicate call UX - recognize returning customer, friendly message, reference existing appointment, prevent duplicate leads (Test 8.7)

dependencies: [implement_ops_schedule]

- id: implement_wrong_number_detection

content: Add wrong number detection - detect misdial phrases, respond gracefully, end call, do NOT create lead, log as non-actionable (Test 8.8)

dependencies: [implement_base_handler]

## Test Coverage Analysis (Tests 9.1-9.5: PERFORMANCE & QUALITY METRICS)

**Note**: These tests verify system performance, quality metrics, and monitoring capabilities. These are measurement and monitoring tests rather than feature tests.

### Test 9.1: Response Time

- ⚠️ **Partially Covered**: Basic metrics system exists (`src/monitoring/metrics.py`)
- ❌ **Gap**: No response time tracking
- ❌ **Gap**: No measurement of time from call start to AI greeting
- ❌ **Gap**: No measurement of time between user input and AI response
- ❌ **Gap**: No alerting for pauses >3 seconds
- **Fix**: Add response time tracking that:
  - Measures time from call start to AI greeting (target: <2 seconds)
  - Measures time between user input and AI response (target: 1-2 seconds)
  - Tracks pauses >3 seconds
  - Logs response times to audit_log or metrics system
  - Provides metrics endpoint for monitoring
- **Status**: Partially covered, needs enhancement

### Test 9.2: Call Completion Rate

- ⚠️ **Partially Covered**: Audit logging tracks call events (`log_vapi_webhook` with `ended_reason`)
- ❌ **Gap**: No call completion rate calculation
- ❌ **Gap**: No tracking of total calls vs completed calls
- ❌ **Gap**: No metrics endpoint for completion rate
- ❌ **Gap**: No alerting if completion rate drops below 90%
- **Fix**: Add call completion tracking that:
  - Tracks total calls made
  - Tracks calls completed successfully (vs dropped/interrupted)
  - Calculates completion rate percentage
  - Provides metrics endpoint (target: 90%+ completion rate)
  - Alerts if completion rate drops below threshold
- **Status**: Partially covered, needs enhancement

### Test 9.3: Data Accuracy

- ⚠️ **Partially Covered**: Audit logging tracks data, but no accuracy measurement
- ❌ **Gap**: No data accuracy tracking
- ❌ **Gap**: No validation of phone number format
- ❌ **Gap**: No validation of address format
- ❌ **Gap**: No spell-checking for names
- ❌ **Gap**: No validation of customer type
- ❌ **Gap**: No accuracy rate calculation
- **Fix**: Add data accuracy tracking that:
  - Validates phone number format
  - Validates address format
  - Validates customer type
  - Tracks accuracy rate (target: 95%+)
  - Provides metrics endpoint
  - Logs data quality issues
- **Status**: Partially covered, needs enhancement

### Test 9.4: User Satisfaction (1-5 Scale)

- ❌ **Not Covered**: No user satisfaction tracking
- ❌ **Gap**: No satisfaction survey mechanism
- ❌ **Gap**: No rating collection (1-5 scale)
- ❌ **Gap**: No tracking of satisfaction metrics:
  - Agent responds quickly
  - Agent understands questions accurately
  - Agent provides clear answers
  - Information is accurate
  - Protects sensitive data
  - Overall satisfaction
- ❌ **Gap**: No target tracking (4.0+ average rating)
- **Fix**: Add user satisfaction tracking that:
  - Collects satisfaction ratings (1-5 scale) via post-call survey or SMS
  - Tracks all satisfaction metrics
  - Calculates average rating
  - Provides metrics endpoint (target: 4.0+ average)
  - Stores ratings in database
- **Status**: Not covered, needs new feature

### Test 9.5: Common Issues Checklist

- ⚠️ **Partially Covered**: Error tracking exists (`increment_errors()` in metrics)
- ❌ **Gap**: No specific tracking for common issues:
  - Wrong information provided
  - Call quality problems (static, echo) - Vapi-side
  - Long pauses (>3 seconds)
  - Repetition / loops
  - System crashes
  - Didn't understand question
  - Couldn't handle follow-up questions
  - Provided irrelevant answers
  - Interrupted customer
  - No identity verification when needed
  - Shared sensitive data inappropriately
  - Read full credit card numbers
  - Couldn't find account securely
  - Prohibited phrase usage
- ❌ **Gap**: No issue tracking/categorization system
- ❌ **Gap**: No reporting for common issues
- **Fix**: Add issue tracking system that:
  - Tracks common issues by category
  - Logs prohibited phrase usage
  - Provides issue reporting dashboard
  - Tracks issue frequency
  - Alerts on critical issues
- **Status**: Partially covered, needs enhancement

## Updated Todos for PERFORMANCE & QUALITY METRICS

- id: implement_response_time_tracking

content: Add response time tracking - measure call start to greeting, user input to response, track pauses >3 seconds, provide metrics endpoint (Test 9.1)

dependencies: [implement_base_handler]

- id: implement_call_completion_tracking

content: Add call completion rate tracking - track total calls, completed calls, calculate rate, provide metrics endpoint, alert if below 90% (Test 9.2)

dependencies: [implement_base_handler]

- id: implement_data_accuracy_tracking

content: Add data accuracy tracking - validate phone/address format, customer type, track accuracy rate, provide metrics endpoint (target 95%+) (Test 9.3)

dependencies: [implement_base_handler]

- id: implement_user_satisfaction_tracking

content: Add user satisfaction tracking - collect ratings (1-5 scale), track all metrics, calculate average, provide metrics endpoint (target 4.0+) (Test 9.4)

dependencies: [implement_base_handler]

- id: implement_issue_tracking_system

content: Add issue tracking system - track common issues by category, log prohibited phrases, provide reporting dashboard, track frequency (Test 9.5)

dependencies: [implement_base_handler]

**Note**: These metrics tests require monitoring and measurement infrastructure. The current plan focuses on feature implementation, but these metrics are critical for production monitoring and quality assurance. Consider implementing these alongside or after core features are complete.