# HAES HVAC-R FINEST — Client Requested Changes Testing Protocol

**Version:** 1.0  
**Date:** January 2026  
**Project:** Voice Agent — Client-Requested Changes Validation  
**Client:** HVAC-R FINEST LLC  
**References:** [HAES_Requested_Changes_Client_Review.md](client_shared/HAES_Requested_Changes_Client_Review.md), [client_requested_changes_implementation plan](.cursor/plans/client_requested_changes_implementation_e22a2da4.plan.md)

---

## Purpose

This protocol is for **user acceptance testing** of the AI voice agent (Jessica) after implementation of the client-requested changes from the February 2026 review. You will test as a **customer** (or property manager / commercial caller) to verify each change behaves as specified. Use your real phone number so you can receive SMS and email confirmations where applicable.

**In scope (implemented):**  
#1 Ring delay, #2 Diagnostic questions, #4 Returning customer, #6 Two time slots, #7 Lead source, #8 Info confirmation, #9 SMS+email after appointment, #10 Maintenance assessment, #11/#12 Tenant vs PM, #13 Commercial urgency, #14 Property-type questions, #16 Commercial checklist, #17 Call purpose, #19 Warranty question, #20 Profile lookup.

**Out of scope (not in this build):**  
#3 Automatic callback, #5 Photo via SMS, #15 Multiple work orders, #18 Spanish.

---

## Test Environment

### Phone & Access

- **Customer line (Jessica):** Use the same number you use for production/testing (e.g. Vapi-assigned or 8x8-forwarded number). Call as a customer.
- **Your number:** Use a **real** phone number so you receive SMS and email for Tests 7 and related flows.
- **Vapi:** Dashboard access to review call logs and assistant config.
- **Odoo:** Access to verify leads, source, and partner linkage.

### Test Data in Odoo (recommended)

- At least one **res.partner** with a known phone number and name (for Test 8 returning customer and Test 9 profile lookup).
- Optional: test addresses in service area (e.g. DeSoto, Arlington, Rockwall) for zoning if you use it.

### Pre-Testing Checklist

- [ ] Backend (e.g. Fly) deployed and healthy; Server URL correct in Vapi.
- [ ] Vapi assistant updated from repo (prompt + tools): run `scripts/update_vapi_assistant_from_repo.py` if needed.
- [ ] SMS (Twilio) and SMTP configured if testing SMS/email (Test 7). Customer inbound voice is 8x8.
- [ ] Knowledge base in Vapi includes latest `customer_faq.txt` (or equivalent) for diagnostic, maintenance, commercial, and tenant/PM content.

---

## Test Result Recording

For each test, record:

```
Test Date: __________
Tester Name: __________
Phone Used: __________
Result: PASS / FAIL
Notes: [What happened; any deviation from expected]
```

**Issue priority:**  
**CRITICAL** — Wrong flow, no lead created, wrong partner, missing required step.  
**HIGH** — Wrong wording, missing question, poor UX.  
**LOW** — Wording tweak, edge case.

---

## SECTION A — Call Start & Routing

### Test A.1: Ring delay (#1) — optional

**Scenario:** Phone rings briefly before the bot answers so it feels like a normal business line.

**Test steps:**

1. From another phone, call the customer line.
2. Count how long the line rings before Jessica answers.

**Expected behavior:**

- Phone rings for about **2–3 seconds** before the bot answers.
- If not configured, skip; this is set in Vapi Phone Number → Hooks → call.ringing (no repo change).

**Status:** [ ] Pass  [ ] Fail  [ ] Skipped (not configured)

**Notes:**

---

### Test A.2: Call purpose at start (#17)

**Scenario:** Jessica asks why the customer is calling and routes to the right workflow.

**Test steps:**

1. Call in and wait for the greeting.
2. If the first message is open-ended (e.g. “How may I help you?”), say something like “I need help” and observe the next question.
3. Answer: **“Service or repair.”** — Confirm she moves into service/repair (e.g. tenant/PM, then problem).
4. (New call) Answer: **“Scheduled maintenance.”** — Confirm she moves toward scheduling.
5. (New call) Answer: **“A question.”** — Confirm she offers to answer or use the knowledge base.

**Expected behavior:**

- Early in the call (first turn or right after your first response), Jessica asks: **“Are you calling for: (1) Service or repair, (2) Equipment replacement, (3) Scheduled maintenance, or (4) A question I can answer?”**
- She routes correctly for each answer and does not collect other details before call purpose is set.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

## SECTION B — Residential Service Flow

### Test B.1: Tenant vs property management (#11, #12)

**Scenario:** Jessica asks whether the caller is a tenant or property management and follows the right flow.

**Test steps:**

1. Call and say **“Service or repair.”** After she acknowledges, listen for the next question.
2. Say **“Tenant.”** — Give name, phone, address when asked; confirm she collects **your** details and offers two time slots when scheduling.
3. (New call) Say **“Service or repair.”** Then say **“Property management.”** — Confirm she asks for **tenant** name/phone, address, and **your** (PM) contact; confirm she can offer to schedule another property after the first and that two slots are offered.

**Expected behavior:**

- Right after acknowledging “Service or repair,” she asks: **“Are you calling as a tenant or as part of the property management team?”**
- **Tenant:** She collects caller’s name, phone, address; standard flow; two slots when scheduling.
- **PM:** She collects tenant + PM contact; can ask “Do you need to schedule another property?”; two slots.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.2: Warranty / service history question (#19)

**Scenario:** Jessica uses the new warranty wording and, on “yes,” looks up the profile.

**Test steps:**

1. In a **residential** service flow (e.g. tenant, home), proceed until she asks about prior service.
2. Note the exact question — it must be **“Have we provided service or warranty work at your house before?”** (not “Have you called us before?”).
3. Say **“Yes.”** — Give phone and address if asked; confirm she says she’s looking up the profile and then says something like **“I found your profile, [Name] at [Address]. Is that correct?”**
4. Say **“Yes, that’s correct.”** — Complete the flow; in Odoo the lead/appointment should be under the existing partner (no duplicate).
5. (New call) Say **“No.”** to the warranty question — confirm she continues as a new customer.

**Expected behavior:**

- Wording matches #19; on “yes” she uses lookup and confirms name/address; on confirm she uses that profile for the rest of the call.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.3: Lookup customer profile at call start — returning customer (#4)

**Scenario:** When the caller’s phone matches one partner in Odoo, Jessica greets by name early.

**Test steps:**

1. Call from a **phone number** that exists on exactly one **res.partner** in Odoo (with name set).
2. Listen to her first or second turn after the call-purpose question (or after greeting).
3. Complete a short service request or scheduling flow.

**Expected behavior:**

- She calls the lookup tool at call start (phone only). If a profile is found, she **greets by name** early (e.g. “Hi [Name], thanks for calling…”).
- She does not re-ask for name/address except to confirm.
- In Odoo, the lead/appointment is linked to **that** partner (no new partner created).

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.4: Diagnostic questions by issue type (#2)

**Scenario:** For service/repair, Jessica asks diagnostic questions that match the issue type (from KB).

**Test steps:**

1. Say **“Service or repair”** and describe a **water leak** (e.g. “There’s water leaking from my AC”). Note the follow-up questions.
2. (New call) Describe **unit not working** (e.g. “My AC isn’t turning on”). Note questions.
3. (New call) Describe **cooling/heating or noise** (e.g. “It’s making a grinding noise”). Note questions.
4. (New call) Mention an **appliance** (e.g. “My fridge isn’t cooling”). Note questions.

**Expected behavior:**

- **Water leak:** Questions about where they see water, inside/outside unit.
- **Unit not working:** Questions about indoor/outdoor unit, when noticed, how long in the home.
- **Cooling/heating or noise:** Questions about noise, when noticed, happened before.
- **Appliance:** Questions about electric/gas, appliance type.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.5: Maintenance assessment — six questions (#10)

**Scenario:** For maintenance/tune-up, Jessica runs the six-question assessment and optional filter size.

**Test steps:**

1. Say **“Scheduled maintenance”** or **“tune-up.”**
2. Listen for a set of assessment questions (system operating, hot/cold spots, bills, humidity, allergies, dust).
3. Answer a few; when asked about filter size, you may say **“I’m not sure.”**

**Expected behavior:**

- She asks maintenance assessment questions (e.g. system operating, hot/cold spots, high bills, sticky/dry air, allergies/sickness, dust).
- She may ask air filter size; “I’m not sure” is acceptable.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.6: Two time slots (#6)

**Scenario:** When scheduling, Jessica offers exactly two options and books the one the customer chooses.

**Test steps:**

1. Go through a flow that ends in **scheduling** (maintenance or after a service request): give name, phone, address, problem as needed.
2. When she checks availability, note how many options she gives.
3. Choose one (e.g. “The first one” or “Tuesday at 10”).
4. Confirm she completes the booking for that slot.
5. In Odoo (or backend), confirm one appointment exists at the chosen time.

**Expected behavior:**

- She says **two** options (e.g. “I have [Day A at Time A] or [Day B at Time B]. Which works better for you?”).
- After you choose, she confirms and books that slot (no single-slot-only offer).
- One appointment is created at the chosen time.

**Code-level verification:** Backend (`schedule_appointment.py` → OPS `handlers.py`) when called with only customer_name, phone, address (no `chosen_slot_start`) returns `next_available_slots` and a speak message like "I have [slot1] or [slot2]. Which works better for you?" In chat evals the tool may not return real availability; on real calls it returns actual slots. Prompt and tool description now say: do not ask for service type or preferred time before the first call.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.7: Information confirmation before finalizing (#8)

**Scenario:** Before creating the service request or appointment, Jessica repeats key details and asks for confirmation.

**Test steps:**

1. Complete a **service request** or **appointment** flow up to the point where she would create the lead or book the appointment.
2. Listen for a repeat-back of: name, address, phone, service type/problem, and (if scheduling) date/time.
3. Listen for a question like **“Is all of this correct?”**
4. Say **“Yes.”** — She should then say she’s creating/scheduling and complete the tool call.
5. (Optional) In another run, say **“No, the address is wrong”** and give a correction; confirm she corrects and repeats again before finalizing.

**Expected behavior:**

- She repeats back the key details and asks “Is all of this correct?” (or similar) before calling the create/schedule tool.
- She only finalizes after you confirm.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.8: Lead source — “How did you hear about us?” (#7)

**Scenario:** Before finalizing, Jessica asks how the customer heard about the company; the lead in Odoo has the correct source.

**Test steps:**

1. Before finalizing a **service request** (or scheduling), when she is confirming details, listen for a lead-source question.
2. When she asks **“How did you hear about us?”** answer e.g. **“Google”** or **“A friend referred me”** or **“Social media.”**
3. Complete the call so the lead is created.
4. In Odoo, open the lead and check the source (utm.source or equivalent); it should match the normalized value (e.g. Google, Referral, Social media, Previous customer, Other).

**Expected behavior:**

- She asks “How did you hear about us?” before finalizing.
- The lead in Odoo has the correct source set.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test B.9: Post-appointment SMS and email (#9)

**Scenario:** Right after a **new** appointment is booked, the customer receives an SMS and an email with appointment details.

**Test steps:**

1. Schedule a **new** appointment (full flow: name, phone, **email**, address, two slots, choose one, confirm).
2. After she confirms the booking, check your **phone** for an SMS (date, time, service type, confirmation wording).
3. Check your **email** for a confirmation with the same appointment details.

**Expected behavior:**

- **SMS** received shortly after the appointment is created (date, time, service type, confirmation wording).
- **Email** received with the same details (if you provided an email).

**Status:** [ ] Pass  [ ] Fail

**Automated check (optional):** Run `python scripts/test_production_schedule_appointment_sms_email.py`. It signs with `VAPI_WEBHOOK_SECRET`, calls schedule_appointment twice (get slots, then book with email), and expects `action=completed` and `appointment_id`. Requires deployed backend with webhook body re-injection so Step 2 receives the request body.

**Notes:**

---

## SECTION C — Commercial Flow

### Test C.1: Commercial urgency (#13)

**Scenario:** For commercial calls, Jessica asks about urgency first.

**Test steps:**

1. Call and say **“Service or repair.”** When asked about property type (or home/business), say **“Business”** or **“Commercial.”**
2. Listen for the next question.

**Expected behavior:**

- She asks: **“Is this an urgent issue requiring immediate attention, or can it be scheduled at your convenience?”**
- She then continues (e.g. property type, checklist) based on your answer (“Urgent” or “At my convenience”).

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test C.2: Commercial property-type questions (#14)

**Scenario:** For commercial, Jessica asks property-type-specific questions from the KB.

**Test steps:**

1. Enter commercial flow; when asked property type, say **hotel.** Note the follow-up questions (rooms, ladder, check-in/guests).
2. (New call) Say **warehouse.** Note questions (ladder, height, equipment type/count, operations/safety).
3. (New call) Say **school.** Note questions (ladder, system type, areas, time, security).

**Expected behavior:**

- **Hotel:** Questions about rooms, ladder access, check-in/guests.
- **Warehouse:** Questions about ladder, height, equipment type/count, operations/safety.
- **School:** Questions about ladder, system type, areas, time, security.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

### Test C.3: Commercial checklist (#16)

**Scenario:** For every commercial call, Jessica gathers the full checklist and the lead in Odoo contains it for technicians.

**Test steps:**

1. Complete a **commercial** service request or scheduling flow from start to finish.
2. Note whether she collects: urgency, property type, ladder access/location, equipment type/quantity, point of contact, access restrictions, business hours, safety.
3. After the lead is created, open it in Odoo and confirm the description or relevant fields contain the commercial checklist data.

**Expected behavior:**

- She gathers the commercial checklist items (details in KB).
- The lead in Odoo contains the collected checklist data for technicians.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

## SECTION D — Quick Smoke Test (One Call)

**Scenario:** Single end-to-end residential service request to validate the main flow.

**Test steps:**

1. Call in → say **“Service or repair.”**
2. Answer: **tenant**, **home**, **routine** (or similar).
3. Give a problem (e.g. “AC not cooling”).
4. Answer one or two diagnostic questions.
5. Answer **“Have we provided service or warranty work at your house before?”** with **“No.”**
6. Give name, phone, address.
7. When asked **“How did you hear about us?”** say **“Google.”**
8. When she repeats back and asks **“Is all of this correct?”** say **“Yes.”**
9. Let her create the service request.

**Expected behavior:**

- Lead is created in Odoo with correct source (e.g. Google); no errors in Vapi or backend; flow feels coherent.

**Status:** [ ] Pass  [ ] Fail

**Notes:**

---

## Sign-Off Summary

| # | Change | Test | Pass |
|---|--------|------|------|
| 1 | Ring delay | A.1 | [ ] |
| 17 | Call purpose at start | A.2 | [ ] |
| 11/12 | Tenant vs PM | B.1 | [ ] |
| 19 | Warranty question wording | B.2 | [ ] |
| 4 | Returning customer — greet by name | B.3 | [ ] |
| 2 | Diagnostic questions | B.4 | [ ] |
| 10 | Maintenance assessment | B.5 | [ ] |
| 6 | Two time slots | B.6 | [ ] |
| 8 | Info confirmation before finalizing | B.7 | [ ] |
| 7 | Lead source | B.8 | [ ] |
| 9 | Post-appointment SMS + email | B.9 | [ ] |
| 13 | Commercial urgency | C.1 | [ ] |
| 14 | Commercial property-type questions | C.2 | [ ] |
| 16 | Commercial checklist | C.3 | [ ] |
| — | Smoke test (one call) | D | [ ] |

**Tester name:** _________________  
**Date:** _________________  
**Overall:** [ ] All critical tests passed  [ ] Issues require follow-up

**Client feedback (Junior/Linda):**

---

*End of Client Requested Changes Testing Protocol*
