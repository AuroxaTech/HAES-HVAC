# HAES HVAC - Project Flow & Architecture

## Overview: What HAES Does

**HAES (HVAC Business Automation System)** is an AI-powered voice and chat assistant that integrates with **Odoo 18 Enterprise** to automate HVAC customer service, scheduling, quoting, billing inquiries, and internal workflows.

### Architecture Type
- **Modular Monolith** - Single FastAPI service with internal module separation
- **Deployment**: Fly.io (Dallas region)
- **Database**: PostgreSQL (managed by Fly.io)
- **Integrations**: Odoo 18 Enterprise (JSON-RPC), Vapi.ai (voice), 8x8 (customer inbound), Twilio (SMS)

---

## High-Level Data Flow

```
Voice/Chat Input → Vapi/API → HAEL (Command Engine) → Brain (OPS/CORE/REVENUE/PEOPLE) → Odoo
```

The system processes customer requests, routes them through a deterministic "command engine" (HAEL), sends them to the appropriate business logic module ("brain"), and then creates or retrieves records in Odoo.

---

## End-to-End Flow: Voice Call via Vapi

### Step 1: Call Comes In

- Customer calls your **Vapi-connected phone number**
- Call is routed to the AI assistant **"Riley"**

### Step 2: Riley Converses & Gathers Info

**Riley's Behavior:**
- Follows the **system prompt** for tone and interaction style (professional, friendly, caring, balanced)
- Uses **Knowledge Base** to answer questions about:
  - Business hours, policies, services
  - Emergency definitions
  - Pricing, payment terms
  - Intake checklists for different request types
- Asks for missing required information:
  - Name, phone, email
  - Service address
  - Problem description
  - Urgency level
  - Preferred appointment window

### Step 3: Riley Triggers Backend via Server URL

When Riley needs to perform an **operational action** (create ticket, schedule appointment, get quote, lookup billing, etc.), Vapi sends a webhook to HAES:

**Endpoint:** `POST https://haes-hvac.fly.dev/vapi/server`

**Message Type:** `tool-calls` (Vapi Server URL contract)

**Payload Structure:**
```json
{
  "message": {
    "type": "tool-calls",
    "call": { "id": "call_123" },
    "toolCallList": [
      {
        "id": "tc_001",
        "name": "hael_route",
        "parameters": {
          "user_text": "My AC isn't cooling. I'm John at 123 Main St, Dallas TX. It's urgent.",
          "conversation_context": "Customer called about AC issue, high temperature emergency"
        }
      }
    ]
  }
}
```

### Step 4: HAES Verifies Request (Security Layer)

**Signature Verification:**
- Vapi signs the webhook with HMAC-SHA256
- HAES verifies signature using `VAPI_WEBHOOK_SECRET`
- **Missing/invalid signature** → Returns `401 Unauthorized`
- **Valid signature** → Proceeds to process request

### Step 5: HAES Runs HAEL Pipeline (Command Engine)

**HAEL (HAES Command Engine) Processing:**

1. **Extraction Phase:**
   - Uses **RuleBasedExtractor** (deterministic, no AI hallucinations)
   - Extracts **intent** from user text:
     - `service_request`
     - `schedule_appointment`
     - `reschedule_appointment`
     - `cancel_appointment`
     - `quote_request`
     - `billing_inquiry`
     - `payment_terms_inquiry`
     - `hiring_inquiry`
     - `onboarding_inquiry`
     - `payroll_inquiry`
     - `unknown`
   - Extracts **entities**:
     - Identity (name, phone, email)
     - Location (address, city, zip)
     - Problem description
     - Urgency level
     - Timeline
     - System type
     - Property details

2. **Routing Phase:**
   - Routes command to appropriate **brain** based on intent:
     - **OPS Brain** ← `service_request`, `schedule_appointment`, `reschedule_appointment`, `cancel_appointment`, `status_update_request`
     - **REVENUE Brain** ← `quote_request`
     - **CORE Brain** ← `billing_inquiry`, `payment_terms_inquiry`, `invoice_request`, `inventory_inquiry`, `purchase_request`
     - **PEOPLE Brain** ← `hiring_inquiry`, `onboarding_inquiry`, `payroll_inquiry`

### Step 6: Brain Processes Request & Interacts with Odoo

Each brain applies **deterministic business rules** and interacts with Odoo:

#### OPS Brain (Operations - Service & Scheduling)

**Example Flow for Service Request:**
1. **Emergency Qualification:**
   - Checks if request meets emergency criteria (gas leak, CO smell, temp thresholds, complete failure, etc.)
   - Applies emergency rules from `src/brains/ops/emergency_rules.py`

2. **Service Catalog Matching:**
   - Matches problem description to service catalog
   - Determines service type and required technician skill level

3. **Odoo Interaction:**
   - Creates or updates `res.partner` (customer record)
   - Creates appropriate Odoo artifact:
     - **Project Task** (`project.task`) - For service tickets
     - **Calendar Event** (`calendar.event`) - For appointments
     - **CRM Lead** (`crm.lead`) - If treated as potential job
   - Links records together

4. **Returns Result:**
   - `status`: `success` or `needs_human` or `error`
   - `message`: Confirmation message for Riley to speak
   - `data`: Additional context (ticket ID, missing fields, etc.)

#### REVENUE Brain (Sales & Marketing)

**Example Flow for Quote Request:**
1. **Lead Qualification:**
   - Qualifies lead as "hot", "warm", or "cold"
   - Applies qualification rules from `src/brains/revenue/qualification.py`

2. **Odoo Interaction:**
   - Creates `crm.lead` with property details, timeline, budget range
   - Sets lead stage based on qualification
   - Creates follow-up activities (`mail.activity`) if available

3. **Returns Result:**
   - Confirmation that lead was created
   - Next steps message (site visit scheduling)

#### CORE Brain (Pricing & Accounting)

**Example Flow for Billing Inquiry:**
1. **Odoo Lookup:**
   - Searches for customer by phone/email
   - Retrieves invoice/payment information
   - Applies payment terms rules

2. **Returns Result:**
   - Payment information
   - Payment terms explanation
   - Due dates

#### PEOPLE Brain (HR & Operations)

**Example Flow for Hiring Inquiry:**
1. **Policy Application:**
   - Retrieves hiring requirements from policy
   - Provides information about onboarding process

2. **Odoo Interaction:**
   - May create `hr.job` application or `hr.applicant` if supported
   - Mostly informational responses

### Step 7: HAES Returns Structured Response to Vapi

HAES returns a JSON response that Vapi understands:

```json
{
  "results": [
    {
      "toolCallId": "tc_001",
      "result": "{\"speak\": \"I've created a service request for you. A technician will call you shortly to confirm the appointment.\", \"action\": \"completed\", \"data\": {\"ticket_id\": \"SR-12345\", \"status\": \"pending\"}}"
    }
  ]
}
```

**Action Outcomes:**
- **`completed`**: Action succeeded - Riley confirms to customer
- **`needs_human`**: Missing info or policy requires human - Riley asks for more info once, then transfers if still needed
- **`error`**: Unexpected failure - Riley apologizes and offers human connection

### Step 8: Human Handoff (If Needed)

If Riley needs to transfer to a human, Vapi can request transfer destination:

**Vapi sends:** `transfer-destination-request` message type

**HAES responds based on business hours:**

**During Business Hours (Mon-Fri, 8am-5pm America/Chicago):**
```json
{
  "destination": {
    "type": "number",
    "number": "+19723724458",
    "message": "Please hold while I connect you with one of our team members."
  }
}
```

**After Hours:**
```json
{
  "error": "after_hours",
  "message": {
    "type": "request-complete",
    "content": "Our office is currently closed. Our business hours are 8 AM to 5 PM Central Time, Monday through Friday. I can collect your information and have someone call you back first thing in the morning."
  }
}
```

---

## Alternative Flow: Website Chat

### Step 1: Customer Sends Chat Message

Customer types message in website chat widget.

### Step 2: Website Sends Request to HAES

**Endpoint:** `POST /chat/message`

**Request Body:**
```json
{
  "message": "My AC isn't working. Need urgent service.",
  "customer_info": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+15551234567"
  }
}
```

### Step 3-7: Same HAEL Pipeline

Same HAEL extraction → Brain routing → Odoo interaction → Response generation

### Step 8: HAES Returns Chat Response

```json
{
  "message": "I've created a service request for you. Ticket #SR-12345. A technician will call you within 30 minutes.",
  "status": "completed",
  "data": {
    "ticket_id": "SR-12345"
  }
}
```

---

## Reporting & KPI Flow

### On-Demand Report Generation

**Endpoint:** `POST /reports/run-once`

**Request:**
```json
{
  "report_type": "daily_summary",
  "period_start": "2026-01-08T00:00:00Z",
  "period_end": "2026-01-08T23:59:59Z"
}
```

**What Happens:**
1. HAES queries `audit_log` table for period
2. Computes KPIs (call volume, conversion rates, brain distribution, etc.)
3. Stores report in `report_runs` table
4. Returns report JSON + summary text

### Scheduled Report Delivery (Optional)

If enabled, background job would:
1. Run reports on schedule (daily, weekly, monthly)
2. Store in `report_runs` table
3. Deliver via configured channels (email/SMS - if SMTP/Twilio configured)
4. Track delivery in `report_deliveries` table

---

## Reliability & Safety Features

### 1. Idempotency

**What it does:**
- Prevents duplicate processing of the same request
- Uses database-backed idempotency keys (`idempotency_keys` table)
- Key format: `{call_id}:{tool_call_id}` or `{request_id}`

**How it works:**
- First request: Processes normally, stores response
- Duplicate request: Returns cached response without re-processing

### 2. Audit Logging

**What it does:**
- Records all significant actions in `audit_log` table
- Enables traceability and debugging

**What gets logged:**
- Request ID, channel (voice/chat), actor (customer info)
- Intent, brain, command JSON
- Odoo result JSON, status, error messages

### 3. Rate Limiting

**What it does:**
- Protects against abuse
- Per-IP sliding window rate limiting

**Configuration:**
- Default: 100 requests per 60-second window
- Configurable via `RATE_LIMIT_REQUESTS_PER_WINDOW` and `RATE_LIMIT_WINDOW_SECONDS`

### 4. Webhook Signature Verification

**What it does:**
- Ensures webhooks come from Vapi (not malicious actors)
- HMAC-SHA256 signature verification

**How it works:**
- Vapi signs request with `VAPI_WEBHOOK_SECRET`
- HAES verifies signature matches
- Missing/invalid → `401 Unauthorized`

### 5. Fail-Closed Principle

**What it does:**
- Never guesses - always asks for clarification or connects to human
- Never assumes urgency - only marks as emergency if criteria explicitly met
- Never skips required info collection

**Behavior:**
- If missing required fields → Returns `needs_human` with list of missing fields
- If unsure about intent → Returns `needs_human` with reason
- If Odoo returns unexpected result → Returns `error` and offers human connection

---

## Example Scenarios: What Happens Step-by-Step

### Scenario A: Emergency AC Failure

**Customer:** "My AC stopped working and it's 90 degrees in here!"

**Step-by-Step:**
1. **Riley**: Asks for name, phone, address
2. **Customer**: Provides info
3. **Riley**: Calls `hael_route` tool with emergency context
4. **HAES**: 
   - Extracts intent: `service_request`
   - Extracts urgency: `emergency` (temperature > 85°F)
   - Routes to **OPS Brain**
5. **OPS Brain**:
   - Qualifies as emergency (temp threshold met)
   - Applies emergency rules
   - Creates `res.partner` in Odoo
   - Creates `project.task` with emergency priority
   - Returns: `{"speak": "I understand this is an emergency. I've created an urgent service request. A technician will be dispatched immediately.", "action": "completed"}`
6. **Riley**: Confirms emergency dispatch to customer

### Scenario B: New System Quote Request

**Customer:** "I need a quote for a new AC system for my 2500 sqft home."

**Step-by-Step:**
1. **Riley**: Asks for property type, square footage, current system age, timeline
2. **Customer**: Provides details
3. **Riley**: Calls `hael_route` tool
4. **HAES**:
   - Extracts intent: `quote_request`
   - Routes to **REVENUE Brain**
5. **REVENUE Brain**:
   - Qualifies lead (hot/warm/cold based on timeline + budget)
   - Creates `crm.lead` in Odoo with property details
   - Sets lead stage based on qualification
   - Creates follow-up activity
   - Returns: `{"speak": "I've created a quote request for you. Our sales team will contact you within 24 hours to schedule a site visit.", "action": "completed"}`
6. **Riley**: Confirms quote request and next steps

### Scenario C: Billing Question

**Customer:** "What are your payment terms? Do you accept credit cards?"

**Step-by-Step:**
1. **Riley**: Uses Knowledge Base to answer payment terms question (no tool call needed)
2. **Customer**: "What's the status of my invoice #INV-12345?"
3. **Riley**: Calls `hael_route` tool with billing inquiry
4. **HAES**:
   - Extracts intent: `billing_inquiry`
   - Routes to **CORE Brain**
5. **CORE Brain**:
   - Looks up invoice in Odoo by invoice number
   - Retrieves payment status, due date, amount
   - Returns: `{"speak": "I found invoice INV-12345. The amount is $450, due on January 15th. Payment status is pending. We accept credit cards, checks, or cash.", "action": "completed"}`
6. **Riley**: Provides invoice details to customer

### Scenario D: After-Hours Transfer Request

**Customer (at 6 PM):** "I want to talk to a person about a complaint."

**Step-by-Step:**
1. **Riley**: Acknowledges request, attempts to transfer
2. **Vapi**: Sends `transfer-destination-request` to HAES
3. **HAES**:
   - Checks business hours (6 PM = after hours)
   - Returns: `{"error": "after_hours", "message": {"content": "Our office is currently closed. I can collect your information and have someone call you back first thing in the morning."}}`
4. **Riley**: Collects callback info, creates note in Odoo for morning follow-up

---

## Database Schema: What Gets Stored

### `audit_log`
- Records every significant action
- Fields: `request_id`, `channel`, `actor`, `intent`, `brain`, `command_json`, `odoo_result_json`, `status`, `error_message`

### `idempotency_keys`
- Prevents duplicate processing
- Fields: `scope`, `key`, `status`, `response_hash`, `response_json`, `expires_at`

### `jobs`
- Background job queue (for scheduled reports, async tasks)
- Fields: `type`, `payload_json`, `status`, `attempts`, `run_at`, `completed_at`

### `report_runs`
- Generated report artifacts
- Fields: `report_type`, `period_start`, `period_end`, `status`, `report_json`, `summary_text`

### `report_deliveries`
- Report delivery tracking
- Fields: `report_run_id`, `channel`, `recipient`, `status`, `provider_message_id`

---

## Odoo Integration: What Gets Created

### Customer Records (`res.partner`)
- Created/updated for every customer interaction
- Fields: `name`, `email`, `phone`, `street`, `city`, `zip`, `country_id`

### Service Requests (`project.task` or similar)
- Created for service requests and appointments
- Fields: `name`, `description`, `partner_id`, `priority`, `date_deadline`, `user_id` (assigned tech)

### Leads/Opportunities (`crm.lead`)
- Created for quote requests
- Fields: `name`, `partner_id`, `type`, `stage_id`, `probability`, `expected_revenue`

### Appointments (`calendar.event`)
- Created for scheduled appointments (if calendar module available)
- Fields: `name`, `start`, `stop`, `partner_ids`, `description`

---

## Security & Compliance

### Data Protection
- No sensitive data in logs (passwords, API keys masked)
- Audit trail for all customer interactions
- Idempotency prevents duplicate charges/records

### Access Control
- Webhook signature verification (prevents unauthorized access)
- Rate limiting (prevents abuse)
- Security headers (HSTS, CSP, X-Frame-Options, etc.)

### Compliance
- Licensed contractor disclosures (TDLR)
- EPA 608 certification mentions
- Warranty terms properly communicated (via KB)

---

## Monitoring & Observability

### Health Checks
- `GET /health` - Overall application + database health
- `GET /vapi/server/health` - Vapi Server URL endpoint health
- `GET /monitoring/metrics` - Basic application metrics

### Logging
- Structured logging with request IDs
- All requests logged with timing, status codes
- Errors logged with full stack traces

### Metrics
- Request count, error count
- Per-endpoint timing
- Database connection pool status

---

## Deployment Architecture

### Production Deployment (Fly.io)

**Application:**
- URL: `https://haes-hvac.fly.dev`
- Region: Dallas (dfw)
- Instance: shared-cpu-1x

**Database:**
- Managed PostgreSQL (Fly.io)
- Region: IAD (Washington D.C.)
- Automatic backups

**Secrets Management:**
- All sensitive values stored in Fly.io secrets
- Not committed to repository
- Rotated as needed

---

## Next Steps for Full Production Readiness

### 1. Complete Odoo Model Mapping
- Determine exact Odoo models for service tickets (project.task vs custom module)
- Map scheduling to calendar.event or field.service
- Test all Odoo write operations with real data

### 2. Vapi Dashboard Configuration
- Update assistant "Riley" with new system prompt
- Upload Knowledge Base documents
- Configure `hael_route` tool
- Test end-to-end with real phone call

### 3. End-to-End Testing
- Make test calls for each brain (OPS, REVENUE, CORE, PEOPLE)
- Verify Odoo records created correctly
- Verify audit logs populated
- Verify handoff logic works during/after business hours

### 4. Monitoring Setup
- Set up alerting for health check failures
- Monitor error rates
- Track call volume and conversion metrics

### 5. Documentation
- API documentation (OpenAPI/Swagger)
- Runbook for common issues
- Troubleshooting guide

---

## Summary

HAES transforms **natural language customer requests** (voice or chat) into **structured business commands**, routes them through **deterministic business logic** (the "brains"), and creates/retrieves records in **Odoo** (your system of record). The entire flow is **audited**, **idempotent**, **rate-limited**, and **secure**, ensuring reliable automation of HVAC customer service operations.

The system follows a **"fail closed"** philosophy - when in doubt, it asks for more information or connects to a human rather than guessing. This ensures accuracy and prevents costly mistakes.

---

**Version:** 1.0  
**Last Updated:** 2026-01-09  
**Maintained By:** HAES Development Team
