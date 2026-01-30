---
name: Implement Full Appointment Scheduling
overview: Implement complete appointment scheduling with Odoo integration, including calendar event creation, technician assignment, rescheduling, cancellation, and integration with existing scheduling rules and CRM leads.
todos:
  - id: create_odoo_appointments_module
    content: Create src/integrations/odoo_appointments.py with AppointmentService class following odoo_leads.py pattern. Include field caching, safe field mapping, and core structure.
    status: completed
  - id: implement_create_appointment
    content: Implement create_appointment() method in AppointmentService to create calendar.event in Odoo with proper field mapping (name, start, stop, partner_ids, user_id, description, location).
    status: completed
    dependencies:
      - create_odoo_appointments_module
  - id: implement_appointment_lookup
    content: Implement find_appointment_by_contact() method to lookup existing appointments by phone/email using Odoo search. Support filtering by date range.
    status: completed
    dependencies:
      - create_odoo_appointments_module
  - id: implement_update_cancel
    content: Implement update_appointment() and cancel_appointment() methods in AppointmentService. Update should modify calendar event fields; cancel should set active=False or delete.
    status: completed
    dependencies:
      - create_odoo_appointments_module
      - implement_appointment_lookup
  - id: integrate_scheduling_rules
    content: Add get_technician_availability() and find_next_available_slot() methods to AppointmentService. Integrate with scheduling_rules.py to query Odoo events and calculate available slots.
    status: completed
    dependencies:
      - implement_create_appointment
      - implement_appointment_lookup
  - id: implement_lead_linking
    content: Add link_appointment_to_lead() method to AppointmentService. Link calendar events to CRM leads using res_id/res_model fields. Update appointment creation to auto-link when lead exists.
    status: completed
    dependencies:
      - implement_create_appointment
  - id: update_schedule_handler
    content: Update _handle_schedule_appointment() in src/brains/ops/handlers.py to use AppointmentService. Integrate scheduling rules, technician assignment, and Odoo calendar event creation. Return appointment details in OpsResult.
    status: completed
    dependencies:
      - implement_create_appointment
      - integrate_scheduling_rules
      - implement_lead_linking
  - id: update_reschedule_handler
    content: Update _handle_reschedule_appointment() in src/brains/ops/handlers.py to lookup existing appointment, validate new slot, and update calendar event in Odoo via AppointmentService.
    status: completed
    dependencies:
      - implement_update_cancel
      - integrate_scheduling_rules
  - id: update_cancel_handler
    content: Update _handle_cancel_appointment() in src/brains/ops/handlers.py to lookup appointment, cancel calendar event in Odoo, and update linked CRM lead status if needed.
    status: completed
    dependencies:
      - implement_update_cancel
      - implement_lead_linking
  - id: integrate_vapi_server
    content: Update execute_hael_route() in src/api/vapi_server.py to handle appointment scheduling results. Extract appointment details from OpsResult.data and include in response (appointment_id, scheduled_time, technician_name).
    status: completed
    dependencies:
      - update_schedule_handler
      - update_reschedule_handler
      - update_cancel_handler
  - id: export_module
    content: Update src/integrations/__init__.py to export odoo_appointments module and AppointmentService class.
    status: completed
    dependencies:
      - create_odoo_appointments_module
  - id: add_unit_tests
    content: Add unit tests for AppointmentService in tests/test_ops_handlers_comprehensive.py. Test create, lookup, update, cancel, and scheduling rule integration with mocked Odoo client.
    status: completed
    dependencies:
      - update_schedule_handler
      - update_reschedule_handler
      - update_cancel_handler
  - id: add_integration_tests
    content: Add integration tests in tests/test_vapi_tool_integration.py for end-to-end appointment scheduling via Vapi tool calls, including CRM lead linking and technician assignment.
    status: completed
    dependencies:
      - integrate_vapi_server
  - id: update_context
    content: Update .cursor/context.json to reflect appointment scheduling implementation status. Add appointment scheduling to integrations section and update module status.
    status: completed
    dependencies:
      - add_integration_tests
isProject: false
---

# Implement Full Appointment Scheduling with Odoo Integration

## Overview

Currently, appointment scheduling handlers exist but only return placeholder messages. This plan implements full Odoo integration to create, update, reschedule, and cancel appointments as calendar events, with proper technician assignment, scheduling rules, and CRM lead linking.

## Current State

**What exists:**

- Handler stubs in `src/brains/ops/handlers.py` (`_handle_schedule_appointment`, `_handle_reschedule_appointment`, `_handle_cancel_appointment`)
- Scheduling rules in `src/brains/ops/scheduling_rules.py` (business hours, time slots, travel time)
- Technician roster in `src/brains/ops/tech_roster.py`
- Odoo CRM lead integration pattern in `src/integrations/odoo_leads.py`
- Odoo client in `src/integrations/odoo.py`
- Odoo models available: `calendar.event`, `project.task`

**What's missing:**

- Odoo calendar event creation/update/cancel
- Appointment lookup by phone/email
- Integration of scheduling rules with Odoo
- Linking appointments to CRM leads
- Actual time slot selection and confirmation

## Architecture

```mermaid
flowchart TD
    A[Vapi Call] --> B[HAEL Router]
    B --> C[OPS Brain Handler]
    C --> D{Appointment Action}
    D -->|Schedule| E[Schedule Handler]
    D -->|Reschedule| F[Reschedule Handler]
    D -->|Cancel| G[Cancel Handler]
    
    E --> H[Validate Entities]
    F --> I[Lookup Appointment]
    G --> I
    
    H --> J[Find Available Slot]
    I --> K[Get Existing Event]
    
    J --> L[Assign Technician]
    K --> M[Validate Changes]
    
    L --> N[Create Calendar Event]
    M --> O[Update Calendar Event]
    M --> P[Cancel Calendar Event]
    
    N --> Q[Link to CRM Lead]
    O --> Q
    P --> R[Update Lead Status]
    
    Q --> S[Return Result]
    R --> S
    S --> T[Vapi Response]
```



## Implementation Plan

### Phase 1: Odoo Calendar Integration Module

**File: `src/integrations/odoo_appointments.py**` (new file)

Create a new module following the pattern of `odoo_leads.py`:

1. **AppointmentService class**
  - Initialize with `OdooClient`
  - Cache `calendar.event` fields
  - Safe field mapping with capability checking
2. **Core methods:**
  - `create_appointment()` - Create calendar event in Odoo
  - `find_appointment_by_contact()` - Lookup by phone/email
  - `update_appointment()` - Reschedule existing appointment
  - `cancel_appointment()` - Cancel appointment
  - `get_technician_calendar_events()` - Get existing appointments for tech
  - `link_appointment_to_lead()` - Link calendar event to CRM lead
3. **Field mapping:**
  - Map to `calendar.event` fields: `name`, `start`, `stop`, `partner_ids`, `user_id` (technician), `description`, `location`
  - Support `res_id`/`res_model` for linking to `crm.lead`
  - Handle timezone conversion (Odoo uses UTC)

### Phase 2: Update Scheduling Handlers

**File: `src/brains/ops/handlers.py**`

Update the three handler functions:

1. `**_handle_schedule_appointment()**`
  - Validate required fields (phone/email, service type, preferred time)
  - Use `scheduling_rules.py` to find available slot
  - Get existing appointments from Odoo via `AppointmentService`
  - Assign technician using `tech_roster.py`
  - Create calendar event in Odoo
  - Link to CRM lead if one exists
  - Return success with appointment details
2. `**_handle_reschedule_appointment()**`
  - Lookup existing appointment by phone/email
  - Validate new time slot using scheduling rules
  - Update calendar event in Odoo
  - Notify via email/SMS (if configured)
  - Return success with updated details
3. `**_handle_cancel_appointment()**`
  - Lookup existing appointment
  - Cancel calendar event (set active=False or delete)
  - Update linked CRM lead status if needed
  - Send cancellation confirmation
  - Return success

### Phase 3: Integrate Scheduling Rules with Odoo

**File: `src/integrations/odoo_appointments.py**`

Add helper methods:

1. `**get_technician_availability()**`
  - Fetch technician's calendar events from Odoo
  - Convert to `TimeSlot` objects for `scheduling_rules.py`
  - Filter by date range
2. `**find_next_available_slot()**`
  - Use `scheduling_rules.get_next_available_slot()`
  - Query Odoo for existing appointments
  - Return suggested time slots
3. `**validate_slot_availability()**`
  - Use `scheduling_rules.validate_scheduling_request()`
  - Cross-check with Odoo calendar events
  - Return validation result

### Phase 4: Link Appointments to CRM Leads

**File: `src/integrations/odoo_appointments.py**`

1. **Link creation:**
  - When creating appointment, link to existing `crm.lead` via `res_id`/`res_model`
  - Use `partner_id` from lead for customer link
  - Update lead stage if appropriate
2. **Lead lookup:**
  - Search for existing lead by phone/email
  - Create link in calendar event: `res_model='crm.lead'`, `res_id=<lead_id>`
  - This enables two-way navigation in Odoo

### Phase 5: Integrate with Vapi Server URL

**File: `src/api/vapi_server.py**`

Update `execute_hael_route()`:

1. **For schedule/reschedule/cancel intents:**
  - After OPS brain returns result, check if appointment was created
  - Extract appointment details from `OpsResult.data`
  - Include appointment info in response (time, technician, confirmation)
2. **Response format:**
  - Include `appointment_id` (Odoo calendar.event ID)
  - Include `scheduled_time` (ISO format)
  - Include `technician_name` if assigned
  - Update `speak` message with appointment confirmation

### Phase 6: Update Context and Tests

**Files:**

- `.cursor/context.json` - Update to reflect appointment scheduling implementation
- `tests/test_ops_handlers_comprehensive.py` - Add appointment scheduling tests
- `tests/test_vapi_tool_integration.py` - Add appointment scheduling integration tests

## Data Flow

```mermaid
sequenceDiagram
    participant V as Vapi
    participant VS as Vapi Server
    participant HAEL as HAEL Router
    participant OPS as OPS Brain
    participant AS as AppointmentService
    participant OC as Odoo Client
    participant Odoo as Odoo
    
    V->>VS: Tool call (schedule_appointment)
    VS->>HAEL: Extract intent/entities
    HAEL->>OPS: Route to OPS brain
    OPS->>AS: create_appointment()
    AS->>AS: Find available slot
    AS->>OC: get_technician_events()
    OC->>Odoo: Search calendar.event
    Odoo-->>OC: Existing events
    OC-->>AS: Event list
    AS->>AS: Calculate next slot
    AS->>OC: create calendar.event
    OC->>Odoo: Create event
    Odoo-->>OC: Event ID
    OC-->>AS: Event created
    AS->>OC: link_to_lead()
    OC->>Odoo: Update event (res_id/res_model)
    Odoo-->>OC: Updated
    OC-->>AS: Success
    AS-->>OPS: Appointment created
    OPS-->>HAEL: OpsResult
    HAEL-->>VS: Response
    VS-->>V: Speak + appointment details
```



## Key Design Decisions

1. **Use `calendar.event` not `project.task**`
  - Calendar events are simpler and better suited for appointments
  - Can link to leads via `res_id`/`res_model`
  - Standard Odoo calendar integration
2. **Idempotency via phone/email lookup**
  - Check for existing appointments before creating
  - Prevent duplicate appointments for same customer/time
3. **Scheduling rules integration**
  - Use existing `scheduling_rules.py` logic
  - Query Odoo for actual availability
  - Combine business rules with real data
4. **Technician assignment**
  - Reuse `tech_roster.py` assignment logic
  - Filter by service area and skill
  - Assign `user_id` in calendar event for Odoo user
5. **CRM Lead linking**
  - Always link appointments to leads when possible
  - Enables full workflow visibility in Odoo
  - Update lead stages appropriately

## Error Handling

- **No available slots**: Return `NEEDS_HUMAN` with suggested times
- **Odoo connection failure**: Fail-closed, return `NEEDS_HUMAN` with captured info
- **Missing required fields**: Return `NEEDS_HUMAN` with missing fields list
- **Appointment not found (reschedule/cancel)**: Return error, suggest creating new appointment

## Testing Strategy

1. **Unit tests:**
  - `AppointmentService` methods with mocked Odoo client
  - Scheduling rule integration
  - Field mapping validation
2. **Integration tests:**
  - End-to-end appointment creation via Vapi
  - Reschedule/cancel flows
  - CRM lead linking
  - Technician assignment logic
3. **Edge cases:**
  - No available technicians
  - All slots booked
  - Timezone handling
  - Weekend/holiday scheduling

## Configuration

No new environment variables needed. Uses existing:

- `ODOO_BASE_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_PASSWORD`
- `ODOO_DISPATCH_USER_ID` (for appointment assignments)

## Dependencies

- Existing: `odoo.py`, `scheduling_rules.py`, `tech_roster.py`, `odoo_leads.py`
- New: `odoo_appointments.py`

## Success Criteria

1. Appointments created in Odoo as calendar events
2. Appointments linked to CRM leads
3. Technician assignment working
4. Reschedule/cancel operations functional
5. Scheduling rules respected (business hours, buffers, etc.)
6. Integration with Vapi Server URL working
7. Tests passing

## Files to Create/Modify

**New files:**

- `src/integrations/odoo_appointments.py` (~400-500 lines)

**Modified files:**

- `src/brains/ops/handlers.py` (~150 lines changed)
- `src/integrations/__init__.py` (export `odoo_appointments`)
- `src/api/vapi_server.py` (~50 lines for appointment handling)
- `tests/test_ops_handlers_comprehensive.py` (~100 lines new tests)
- `tests/test_vapi_tool_integration.py` (~50 lines appointment tests)
- `.cursor/context.json` (update status)

## Implementation Order

1. Create `odoo_appointments.py` module with basic structure
2. Implement `create_appointment()` method
3. Implement appointment lookup methods
4. Update `_handle_schedule_appointment()` to use Odoo
5. Implement `update_appointment()` and update reschedule handler
6. Implement `cancel_appointment()` and update cancel handler
7. Add scheduling rules integration
8. Add CRM lead linking
9. Integrate with Vapi Server URL
10. Add tests
11. Update context.json

