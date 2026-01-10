## Vapi Voice Agent — End-to-End Verification Checklist (Definition of Done)

This document is your **single source of truth** for verifying the HAES + Vapi voice agent is **fully working end-to-end** per project scope (HAEL + 4 brains + Odoo writes + auditing + reliability).

### How to use this doc

- Run each test in order: **Test 1, Test 2, …**
- Mark each test **PASS/FAIL**.
- If a test fails, capture:
  - **Vapi call link / run output**
  - **Lead ID + Partner ID (if created)**
  - **Fly logs snippet** (search `call_id`, `hael_route`, `Odoo lead`)

### Definition of “Done”

You are done when:

- **All tests in this checklist PASS**
- Vapi calls consistently:
  - collect info naturally (one question at a time)
  - call the tool (no narrated JSON)
  - create/update **Odoo CRM Leads** and **Contacts**
  - write an **audit trail** (server logs + DB audit where applicable)
  - handle emergencies + transfer rules correctly

---

## Preconditions (must be true before testing)

### P0. Production health

- **Action**
  - Open `https://haes-hvac.fly.dev/vapi/server/health` in a browser.
- **Expected**
  - `status=ok`

### P1. Vapi assistant wired to Server URL

- **Action**
  - In Vapi dashboard → Assistant “Riley”:
    - Server URL = `https://haes-hvac.fly.dev/vapi/server`
    - Tool name = `hael_route`
- **Expected**
  - Vapi tool execution appears in dashboard tool trace.

### P2. Tool schema is the structured version

- **Action**
  - Verify the tool expects fields like:
    - `request_type`, `customer_name`, `phone`, `email`, `address`, `issue_description`, `urgency`, `property_type`
- **Expected**
  - Calls send **structured fields**, not only `user_text`.

### P3. Odoo access is working

- **Action**
  - Confirm you can open Odoo → CRM → Leads.
- **Expected**
  - You can see newly created leads.

### P4. Deployment rule (only when you changed tool/prompt)

Any time you change Vapi prompt/tool behavior, you must ensure:

- Backend deployed (Fly) **if backend code changed**
- Vapi configured **if prompt/tool settings changed** (via script or dashboard)

---

## Quick automated smoke tests (optional but recommended)

### Test 0.1 — Run the production smoke script

- **Action**
  - Run:

```bash
python scripts/verify_vapi_server_url.py --prod
```

- **Expected**
  - All tests show ✓
  - The "Service Request with Odoo Lead Creation" test prints:
    - `Odoo Lead ID: <number>`
    - `Odoo Action: created|updated`

### Test 0.2 — Run the emergency flow verification script

- **Action**
  - Run:

```bash
# Local
python scripts/verify_emergency_flow.py

# Against production
BASE_URL=https://haes-hvac.fly.dev python scripts/verify_emergency_flow.py
```

- **Expected**
  - All checks show ✅ PASS:
    - Emergency detected
    - Priority is CRITICAL
    - ETA window 1.5-3 hours
    - Pricing present
    - Junior assigned for DeSoto
    - Speak mentions ETA and pricing

---

## A. Vapi conversation behavior (tone + progressive intake)

### Test 1 — Greeting + tone

- **Action**
  - Call the Vapi number.
- **Expected**
  - Riley greets:
    - “Thank you for calling HVAC‑R Finest, this is Riley. How can I help you today?”
  - Tone is friendly, concise, human.

### Test 2 — Progressive intake (one question at a time)

- **Action**
  - Say: “My heater is not working.”
- **Expected**
  - Riley asks **one question at a time** in this order:
    - name → phone → email → address → issue detail → urgency → property type

### Test 3 — Validation behavior

- **Action**
  - Provide phone + address.
- **Expected**
  - Riley confirms:
    - phone (last 4 digits or clear repeat-back)
    - address (street + city + zip)

### Test 4 — Recap before submission

- **Action**
  - Provide all details.
- **Expected**
  - Riley recaps: name, phone, email, address, issue, urgency, property type
  - Then: “One moment while I submit that.”

### Test 5 — Never narrate tool calls

- **Action**
  - During submission, listen carefully.
- **Expected**
  - Riley does **NOT** read JSON or say “Calling the tool”.
  - Riley does **NOT** show code blocks.

---

## B. Tool execution (Vapi → HAES)

### Test 6 — Tool execution appears in Vapi

- **Action**
  - Complete a call where Riley submits a request.
- **Expected**
  - Vapi dashboard shows:
    - Tool executed: `hael_route`
    - Tool response returned

### Test 7 — Tool response contract

- **Expected tool response**
  - `speak` (string)
  - `action` ∈ `completed | needs_human | error`
  - `data` (object)
  - `request_id` (uuid string)

### Test 8 — needs_human asks only missing fields

- **Action**
  - Refuse to give address, but give name/phone/email.
- **Expected**
  - Tool returns `needs_human` with `missing_fields`
  - Riley asks **only one missing field at a time**

---

## C. Odoo: lead + partner creation (core scope)

### Test 9 — Service request creates an Odoo Lead (crm.lead)

- **Call script**
  - “My heater is not working.”
  - Provide:
    - Name: “Test Service Customer”
    - Phone: “+1 972 555 0101”
    - Email: “test.service.customer+1@example.com”
    - Address: “123 Main St, DeSoto, TX 75115”
    - Urgency: “today”
    - Property type: “residential”
- **Expected**
  - Tool response `data.odoo` exists:
    - `crm_lead_id` is present
    - `action` is `created` or `updated`
    - `partner_id` is present or null (but usually present)
  - In Odoo CRM → Leads:
    - Lead has **contact_name**, **phone**, **email_from**, **street**, **city**, **zip**
    - Lead internal notes include the `[call_id:...]` marker

### Test 10 — Emergency service request sets emergency priority

- **Call script**
  - "I smell gas and my heater isn't working."
- **Expected**
  - Tool returns:
    - `data.is_emergency=true`
  - Odoo lead:
    - priority set to emergency (highest)
    - internal notes show emergency banner/section

### Test 10a — Temperature-based emergency (no heat + cold indoor temp)

- **Call script**
  - "My heater isn't working."
  - When Riley asks for indoor temperature: "52 degrees"
- **Expected**
  - Tool returns:
    - `data.is_emergency=true`
    - `data.priority_label="CRITICAL"`
    - `data.eta_window_hours_min=1.5`
    - `data.eta_window_hours_max=3.0`
  - Riley mentions:
    - Emergency ETA window (1.5-3 hours)
    - Diagnostic fee with premiums

### Test 10b — Emergency pricing shown correctly

- **Expected**
  - Tool response includes `data.pricing` with:
    - `tier="retail"` (default)
    - `diagnostic_fee`, `emergency_premium`, `total_base_fee`
  - `data.pricing.total_base_fee` reflects premiums applied

### Test 10c — DeSoto (75115) assigns Junior

- **Call script**
  - Provide address: "123 Main St, DeSoto, TX 75115"
- **Expected**
  - Tool returns:
    - `data.assigned_technician.id="junior"`
    - `data.assigned_technician.name="Junior"`

### Test 10d — Emergency lead has Emergency tag in Odoo

- **Action**
  - Complete an emergency call, then check Odoo lead.
- **Expected**
  - Lead has "Emergency" tag attached (visible in Tags field)
  - Chatter shows emergency notification post

### Test 10e — Customer receives emergency SMS (if enabled)

- **Precondition**
  - `FEATURE_EMERGENCY_SMS=true` and Twilio configured
- **Expected**
  - Customer receives SMS with:
    - Company name
    - Tech name
    - ETA window
    - Base fee
    - Opt-out instruction

### Test 11 — Internal notes are structured and readable

- **Action**
  - Open the lead’s Internal Notes.
- **Expected**
  - Notes are clearly sectioned (Customer Info / Service Request / Metadata)
  - Not a single long paragraph blob.

### Test 12 — Email capture is stored on both Lead + Partner (when correct)

- **Action**
  - Provide email in the call.
- **Expected**
  - Odoo lead `email_from` = provided email
  - Odoo partner `email` = provided email

---

## D. Prevent wrong contact overwrite (same phone, different person)

This verifies the fix for the “same phone but different name/email overwrites contact” problem.

### Test 13 — Same phone, different person MUST create a new partner (no overwrite)

- **Setup**
  - Pick an existing phone number already in Odoo from a previous call.
- **Call script**
  - Use the **same phone**, but give a **different full name** and **different email**:
    - Name: “Different Person”
    - Phone: (same as existing)
    - Email: `different.person@example.com`
- **Expected**
  - A **new partner** is created in Odoo (new `res.partner`)
  - The new lead links to the new partner
  - The previous partner’s email does **not** change

---

## E. Idempotency / no duplicate lead spam

### Test 14 — Repeat tool call does not create duplicates for same call

- **Action**
  - In Vapi, repeat the same tool submission (or re-run quickly).
- **Expected**
  - HAES returns consistent result (idempotent)
  - Odoo lead is updated (or reused), not duplicated for the same call reference.

---

## F. KB correctness (Files-only KB behavior)

### Test 15 — Hours + service area answered from KB (no guessing)

- **Action**
  - Ask:
    - “What are your hours?”
    - “Do you service DeSoto?”
- **Expected**
  - Riley answers accurately per KB.
  - If KB doesn’t cover a detail: Riley says it will be confirmed by a team member (no guessing).

### Test 16 — Policies answered from KB

- **Action**
  - Ask about warranty/payment terms.
- **Expected**
  - Accurate, policy-aligned response (no promises).

---

## G. Transfer / handoff

### Test 17 — Human request triggers handoff path

- **Action**
  - Say: “I want a human.”
- **Expected**
  - During business hours: transfer destination is provided
  - After hours: Riley collects callback info

### Test 18 — Tool blocks twice triggers handoff

- **Action**
  - Create a flow where tool returns `needs_human` twice (omit required info twice).
- **Expected**
  - Riley offers transfer or callback intake.

---

## H. Brain coverage (voice routes into the 4 brains)

### Test 19 — OPS brain (service request)

- **Action**
  - “My heater is not working.”
- **Expected**
  - OPS path executes; lead created/updated.

### Test 20 — REVENUE brain (quote request)

- **Action**
  - “I need a quote for a new AC system.”
- **Expected**
  - Lead created/updated in Odoo
  - If missing required quote fields: `needs_human` asks only what’s missing

### Test 21 — CORE brain (billing inquiry)

- **Action**
  - “I have a question about my invoice.”
- **Expected**
  - CORE response is correct (policy aligned)
  - No incorrect Odoo lead overwrite (lead creation is optional depending on configured intents)

### Test 22 — PEOPLE brain (hiring inquiry)

- **Action**
  - “Are you hiring HVAC technicians?”
- **Expected**
  - PEOPLE response is correct and safe.

---

## I. Edge / reliability cases (must fail safely)

### Test 23 — No email provided

- **Action**
  - Caller refuses email: “I don’t have one.”
- **Expected**
  - Riley continues (email optional), still creates lead if enough info.
  - Lead has email blank; no crashes.

### Test 24 — Bad email format

- **Action**
  - Provide: “hammas at gmail dot com”
- **Expected**
  - Riley asks to clarify email format or offers to proceed without email.

### Test 25 — Very long issue description

- **Action**
  - Give a long story (2–3 minutes).
- **Expected**
  - Riley stays calm, summarizes, proceeds.
  - Lead notes truncate safely; no errors.

### Test 26 — Unknown intent

- **Action**
  - “I want to talk about something unrelated.”
- **Expected**
  - `needs_human` with safe handoff options.

---

## J. Security / production correctness

### Test 27 — Signature behavior (production)

- **Action**
  - Verify Vapi calls succeed in production without 401/403.
- **Expected**
  - No “Missing webhook signature” errors in Fly logs for real calls.

---

## Final closeout checklist

### Closeout 1 — Confirm your last successful call created:

- Odoo CRM lead with:
  - `contact_name`
  - `phone`
  - `email_from` (if provided)
  - `street`/`city`/`zip`
  - structured internal notes
- Odoo contact (partner) with:
  - correct name/email
  - no overwriting wrong contacts

### Closeout 2 — Confirm Vapi tool trace shows:

- tool executed
- tool response returned
- assistant did not narrate JSON

### Closeout 3 — Confirm no regressions:

- emergency route works
- transfer/handoff works
- KB answers are correct and not guessed

### Closeout 4 — Confirm emergency flow features (new):

- Temperature-based emergency triggers at <55°F for no heat
- Emergency response includes:
  - `priority_label="CRITICAL"`
  - ETA window (1.5-3 hours)
  - Pricing breakdown with premiums
- DeSoto (751xx) assigns to Junior
- Emergency leads get "Emergency" tag in Odoo
- Chatter message posted with emergency details
- Customer SMS sent (if FEATURE_EMERGENCY_SMS=true)

