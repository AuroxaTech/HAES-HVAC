# Vapi Tools — Architecture Reference

## Architecture Overview

After the March 2026 optimization, tools are organized by **execution context**:

| Context | Count | Assistant | How They Run |
|---------|-------|-----------|--------------|
| **In-Call** | 5 | Riley Customer Inbound | Attached to VAPI. Called during live conversation via `tool-calls` server message. |
| **Post-Call** | 14 | Riley Customer Inbound | NOT attached to VAPI. Triggered by `PostCallProcessor` after call ends via structured outputs from `end-of-call-report`. |
| **Internal OPS** | 6 | Riley OPS | ALL UNLINKED from VAPI. Code retained in codebase. Riley OPS uses post-call structured output ("FSM Subtask Request") only. |

**Total tools in codebase:** 25 (5 active in-call + 14 post-call handlers + 6 unlinked)

## Directory Structure

```
doc/vapi/tools/
├── README.md              # This file
├── in_call/               # 5 tools attached to VAPI (Riley Customer Inbound)
├── post_call/             # 14 backend handlers (PostCallProcessor)
├── internal_ops/          # 6 tools (all UNLINKED from VAPI Dashboard)
└── tool_schema.json       # Legacy hael_route schema
```

---

## In-Call Tools (5) — Attached to VAPI

These are the ONLY tools attached to the Riley Customer Inbound assistant in the VAPI Dashboard. They execute during the live call via the Server URL (`/vapi/server`).

All are **read-only** — no write operations during the call.

| Tool | Purpose | When Jessica Uses It |
|------|---------|---------------------|
| `check_availability` | Get next 2 available appointment slots | After collecting service details, when customer is ready to schedule |
| `lookup_customer_profile` | Look up existing customer by phone | At call start to greet returning customers by name |
| `check_appointment_status` | Check existing appointment details | When customer asks "when is my appointment?" |
| `check_lead_status` | Check quote/lead progress | When customer asks "any update on my estimate?" |
| `billing_inquiry` | Check billing and outstanding balance | When customer asks about payment or balance |

**Server URL:** `https://haes-hvac.fly.dev/vapi/server`
**Server messages required:** `tool-calls` + `end-of-call-report`

---

## Post-Call Handlers (14) — Structured Outputs

These are NOT attached to VAPI. They run server-side after the call ends, triggered by the `PostCallProcessor` which processes structured outputs from the `end-of-call-report` webhook.

### How It Works

1. During the call, Jessica collects all information conversationally
2. Call ends → VAPI sends `end-of-call-report` with 4 structured outputs
3. `PostCallProcessor` extracts data and calls the appropriate handler(s)

### 4 Structured Outputs (from VAPI)

| Output | Fields | Triggers |
|--------|--------|----------|
| **Customer Profile** | name, phone, email, address, propertyType, callerType, companyName | Partner upsert in Odoo |
| **Appointment Action** | action (book/reschedule/cancel), chosenSlotStart, chosenSlotEnd, chosenSlotTechnicianId, urgency, problemDescription, technicianNotes | schedule/reschedule/cancel handlers |
| **Pending Request** | requestType (service/quote/complaint/invoice/membership), details | service request, quote, complaint, invoice, membership handlers |
| **Call Analytics** | primaryIntent, resolution, sentiment, followUpRequired, callSummary | Lead description, call logging |

### Post-Call Handler Reference

| Handler | Triggered By | What It Does |
|---------|-------------|--------------|
| `schedule_appointment` | Appointment Action (action=book) | Creates calendar event + CRM lead + FSM task in Odoo |
| `reschedule_appointment` | Appointment Action (action=reschedule) | Moves existing calendar event to new slot |
| `cancel_appointment` | Appointment Action (action=cancel) | Cancels calendar event, updates lead |
| `create_service_request` | Pending Request (type=service) | Creates CRM lead with service details |
| `request_quote` | Pending Request (type=quote) | Creates quote lead, sends same-day install link |
| `request_membership_enrollment` | Pending Request (type=membership) | Creates enrollment lead, sends payment link via SMS+email |
| `create_complaint` | Pending Request (type=complaint) | Creates complaint lead, escalates to management |
| `invoice_request` | Pending Request (type=invoice) | Sends invoice copy to customer email |
| `payment_terms_inquiry` | Pending Request (type=payment_terms) | Returns payment term info (now in KB) |
| `send_notification` | All successful actions | Sends SMS + email confirmation (automated, no tool call) |
| `get_pricing` | — | Static pricing data (moved to KB) |
| `get_maintenance_plans` | — | Plan info (moved to KB) |
| `get_service_area_info` | — | Service area data (moved to KB) |
| `check_business_hours` | — | Hours data (moved to KB) |

**Note:** The last 4 (pricing, maintenance plans, service area, business hours) have been moved to the Knowledge Base. Jessica answers these from KB without any tool call. The handler code is retained as backend reference.

**PostCallProcessor:** `src/api/post_call_processor.py`
**Structured outputs registration:** `scripts/register_structured_outputs.py`

---

## Internal OPS Tools (6) — All UNLINKED

All 6 tools have been unlinked from the Riley OPS assistant in the VAPI Dashboard. Code is retained in the codebase for potential future use.

Riley OPS now operates with **0 in-call tools**. It uses a single post-call structured output ("FSM Subtask Request") to create FSM subtasks in Odoo.

| Tool | Purpose | Status |
|------|---------|--------|
| `ivr_close_sale` | ConversionFlow — technician closes sale via IVR | Unlinked. Tested, production-ready. |
| `payroll_inquiry` | Employee payroll and commission info | Unlinked. Tested. |
| `onboarding_inquiry` | Onboarding checklist and training | Unlinked. Tested. |
| `hiring_inquiry` | Hiring requirements and process | Unlinked. Tested. |
| `inventory_inquiry` | Parts and equipment inventory | Unlinked. Tested. |
| `purchase_request` | Create purchase requests | Unlinked. Tested. |

**OPS PostCallProcessor:** `src/api/ops_post_call_processor.py`
**FSM subtask service:** `src/integrations/odoo_fsm_subtasks.py`
**OPS structured output registration:** `scripts/register_ops_structured_outputs.py`

---

## Phone Numbers & Assistants

| Line | Number | Assistant | In-Call Tools | Post-Call |
|------|--------|-----------|--------------|-----------|
| Customer | +1-972-597-1644 (8x8) | Riley Customer Inbound | 5 | PostCallProcessor (4 structured outputs) |
| Internal OPS | +1-855-768-3265 (Twilio) | Riley OPS | 0 | OpsPostCallProcessor (FSM Subtask Request) |

---

## Python Handler Locations

All tool handlers remain in `src/vapi/tools/` (unchanged):

- `src/vapi/tools/ops/` — appointment and service request handlers
- `src/vapi/tools/revenue/` — quote, membership, ivr_close_sale handlers
- `src/vapi/tools/core/` — billing, pricing, complaint handlers
- `src/vapi/tools/people/` — HR handlers (payroll, onboarding, hiring)
- `src/vapi/tools/utils/` — business hours, service area, maintenance plans, notifications

**Tool registry:** `src/vapi/tools/register_tools.py`
**Base handler:** `src/vapi/tools/base.py`

---

## Knowledge Base (Replaces Information Tools)

Static data that was previously served by tools is now in the Knowledge Base, queried automatically by the LLM:

| Data | KB File | Old Tool |
|------|---------|----------|
| Business hours | `doc/vapi/kb/customer_faq.txt` | `check_business_hours` |
| Service area | `doc/vapi/kb/customer_faq.txt` | `get_service_area_info` |
| Pricing | `doc/vapi/kb/customer_faq.txt` | `get_pricing` |
| Maintenance plans | `doc/vapi/kb/customer_faq.txt` | `get_maintenance_plans` |
| Payment terms | `doc/vapi/kb/policies.txt` | `payment_terms_inquiry` |

**KB assignment:** See `doc/vapi/KB_ASSIGNMENT.md`
