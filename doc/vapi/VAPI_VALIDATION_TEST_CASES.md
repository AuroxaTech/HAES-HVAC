# Vapi Validation Test Cases — Client Requested Changes

Use this checklist to validate the deployed Jessica assistant in Vapi (phone or web). Run through each scenario and tick off as you verify.

**How to test:** Call your Vapi number or use Vapi dashboard → Test (web). Answer as the “customer” and note what Jessica says and does.

---

## Pre-requisites

- [ ] Backend deployed (e.g. Fly) and Server URL correct in Vapi
- [ ] `VAPI_ASSISTANT_ID` matches the assistant you updated
- [ ] Test phone number (or web) can reach the assistant

---

## 1. Call purpose at start (#17)

**Goal:** Jessica asks why they’re calling and routes correctly. The 4-option question is the **CRITICAL first step** (top of prompt). If Vapi uses an open-ended firstMessage, the LLM asks the 4-option question immediately after the customer's first response. Optional: In Vapi, set firstMessage to include the 4-option question; keep assistant name consistent (e.g. Jessica).

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Call in, wait for greeting | First message includes the 4-option question, OR after you respond to an open-ended greeting Jessica asks: “Are you calling for: (1) Service or repair, (2) Equipment replacement, (3) Scheduled maintenance, or (4) A question I can answer?” |
| 2 | “Service or repair.” | Jessica acknowledges and moves into service/repair flow (property type, urgency, etc.). |
| 3 | (New call) “Scheduled maintenance.” | Jessica moves toward scheduling / check_availability. |
| 4 | (New call) “A question.” | Jessica offers to answer or use knowledge base. |

**Pass:** [ ] Jessica asks the 4-option call purpose question (first turn or right after customer's first response) and routes by your answer.

---

## 2. Tenant vs property management (#11, #12)

**Goal:** Jessica asks “tenant or property management?” Right after "Service or repair" (after Step 1 empathy), Jessica asks the question and follows the correct flow: tenant = caller's name/phone/address; PM = tenant + PM details and optional "Do you need to schedule another property?"

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Call, say “Service or repair.” | Right after acknowledging, Jessica asks: “Are you calling as a tenant or as part of the property management team?” |
| 2 | “Tenant.” | Jessica collects your name, phone, address (you are the tenant); standard flow; two slots. |
| 3 | (New call) “Property management.” | Jessica uses streamlined flow; collects tenant's name/phone, address, your (PM) contact; can ask "Do you need to schedule another property?" after first; two slots. |

**Pass:** [ ] Tenant vs PM asked right after Step 1; tenant path = caller's details; PM path = tenant + PM details, optional multiple properties.

---

## 3. Warranty / service history question (#19)

**Goal:** Jessica uses the new wording and, on “yes,” can look up profile.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | In a **residential** service flow, when asked | Jessica asks: “Have we provided service or warranty work at your house before?” (not “Have you called us before?”). |
| 2 | “Yes.” | Jessica uses or offers to use lookup (phone + address) and says something like: “I found your profile, [Name] at [Address]. Is that correct?” |
| 3 | “Yes, that’s correct.” | Rest of call uses that profile (no duplicate partner). |
| 4 | (New call) “No.” | Jessica continues as new customer. |

**Pass:** [ ] Correct warranty wording; on “yes,” profile lookup and confirmation; on confirm, profile used for rest of call.

---

## 4. Two time slots (#6)

**Goal:** Jessica offers exactly two time slot options and books the one the customer chooses. Flow: first schedule_appointment call (no slot) returns two options; after customer picks, second call with either chosen_slot_start (ISO datetime) or preferred_date + preferred_time. Backend accepts both.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Go through flow to **schedule** (maintenance or after service request): give name, phone, address, problem. | When scheduling, Jessica says **two** options (from first schedule_appointment call), e.g. “I have [Day A at Time A] or [Day B at Time B]. Which works better for you?” |
| 2 | “The first one.” or “Tuesday at 10.” | Jessica calls schedule_appointment again with chosen_slot_start or preferred_date + preferred_time; confirms and completes booking. |
| 3 | Check backend / Odoo | One appointment created at the chosen time. |

**Pass:** [ ] Two slots offered; second call books chosen slot (chosen_slot_start or preferred_date + preferred_time); appointment in Odoo at chosen time.

---

## 5. Information confirmation before finalizing (#8)

**Goal:** Jessica repeats key details and only finalizes after “Is all of this correct?”

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Complete a **service request** or **appointment** flow up to the point of creation. | Before calling the create/schedule tool, Jessica **repeats back**: name, address, phone, service type / problem, and (if scheduling) date/time. |
| 2 | Jessica asks | “Is all of this correct?” (or similar). |
| 3 | “Yes.” | Jessica then says she’s creating/scheduling and calls the tool. |
| 4 | “No, the address is wrong.” | Jessica corrects and repeats again before finalizing. |

**Pass:** [ ] Repeat-back and “Is all of this correct?” before any create/schedule tool call.

---

## 6. Lead source — “How did you hear about us?” (#7)

**Goal:** Jessica asks before finalizing and lead in Odoo has correct source. create_service_request must have **lead_source** parameter (repo: enum Google, Referral, Social media, Previous customer, Other). If missing on Vapi, re-run `scripts/update_vapi_assistant_from_repo.py`.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Before finalizing a **service request** (or scheduling), when Jessica is confirming. | Jessica asks: “How did you hear about us?” |
| 2 | “Google.” or “A friend referred me.” or “Social media.” | Jessica acknowledges and continues to repeat-back / final confirmation. |
| 3 | Complete the call and create the lead. | In Odoo, lead’s source (utm.source) is set to the normalized value (e.g. Google, Referral, Social media, Previous customer, Other). |

**Pass:** [ ] Question asked before finalizing; create_service_request called with lead_source; Odoo lead source matches answer.

---

## 7. Post-appointment SMS + email (#9)

**Goal:** After a **new** appointment is booked, customer gets immediate SMS and email.

**Implementation (verified):** In `src/vapi/tools/ops/schedule_appointment.py`, after an appointment is successfully created, the handler (1) sends immediate SMS via `send_service_confirmation_sms` (Twilio) with appointment date, time, service type, and confirmation wording; (2) sends immediate email via `send_service_confirmation_email` (if customer email was provided) with same appointment details. SMS content: `build_service_confirmation_sms` in `src/integrations/twilio_sms.py`. Email content: `build_service_confirmation_email` in `src/integrations/email_notifications.py`. Requires Twilio (SMS) and SMTP configured; customer inbound voice is 8x8. `FEATURE_EMERGENCY_SMS` enables sending.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Schedule a **new** appointment (full flow: name, phone, email, address, two slots, choose one, confirm). | Appointment is created. |
| 2 | Check customer phone | **SMS** received with appointment date, time, service type, confirmation wording. |
| 3 | Check customer email (if you gave one) | **Email** received with same appointment details. |

**Pass:** [ ] New appointment → immediate SMS + email to customer.

---

## 8. Returning customer — greet by name (#4)

**Goal:** If caller’s phone matches one partner in Odoo, Jessica can greet by name and use existing profile.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Call from a **phone number** that exists on exactly one `res.partner` in Odoo (with name set). | Jessica calls lookup_customer_profile at call start (phone only); then **greets by name** early in the call (e.g. “Hi [Name]”) and does not re-ask for name/address unless confirming. |
| 2 | Complete a service request or appointment. | In Odoo, lead/appointment is linked to **that** partner (no new partner created). |

**Pass:** [ ] Call-start phone lookup; recognized phone → greeting by name; same partner used for lead/appointment.

---

## 9. Lookup customer profile tool (#20)

**Goal:** After “yes” to warranty question, Jessica can call lookup and confirm profile.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Residential flow; when asked “Have we provided service or warranty work at your house before?” say “Yes.” | Jessica has (or collects) phone + address, then says she’s looking up your profile. |
| 2 | (Backend has one match for that phone+address) | Jessica says: “I found your profile, [Name] at [Address]. Is that correct?” |
| 3 | “Yes.” | Jessica uses that profile (confirmed_partner_id) for create_service_request or schedule_appointment. |
| 4 | (Backend has no match) | Jessica says she couldn’t find a profile and continues as new customer. |

**Pass:** [ ] On “yes” to warranty, lookup used; confirmation phrase; profile used when found.

---

## 10. Diagnostic questions (#2)

**Goal:** For service/repair, Jessica asks diagnostic questions by issue type (from KB).

**KB/Prompt (verified):** Step 4 says use KB for diagnostic questions by issue type. KB `customer_faq.txt`: "Diagnostic questions (service/repair calls)" — Water leaks, Unit not working, Cooling/heating noise, Appliance (each with specific questions).

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Say “Service or repair,” then describe **water leak**. | Jessica asks diagnostic questions relevant to water leaks (e.g. where they see water, inside/outside unit). |
| 2 | (New call) Describe **unit not working**. | Questions about indoor/outdoor unit, when noticed, how long in house. |
| 3 | (New call) Describe **cooling/heating or noise**. | Questions about noise, when noticed, happened before. |
| 4 | (New call) Mention **appliance** (e.g. fridge). | Questions about electric/gas, appliance type. |

**Pass:** [ ] Issue type mentioned → relevant diagnostic questions from KB asked.

---

## 11. Maintenance assessment (#10)

**Goal:** For maintenance/tune-up, Jessica runs the six-question assessment (+ optional filter size).

**KB/Prompt (verified):** Step 4 says use KB for six-question maintenance assessment. KB `customer_faq.txt`: "Maintenance assessment" — 6 questions (operating, hot/cold spots, bills, sticky/dry air, allergies, dust) + optional filter size ("I'm not sure" OK).

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Say “Scheduled maintenance” or “tune-up.” | Jessica asks maintenance assessment questions (e.g. system operating, hot/cold spots, high bills, sticky/dry air, allergies/sickness, dust). |
| 2 | Answer a few. | Jessica may ask air filter size or “I’m not sure” accepted. |

**Pass:** [ ] Maintenance path includes the six-question assessment (and optional filter size).

---

## 12. Commercial — urgency (#13)

**Goal:** For commercial, Jessica asks urgency first.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Say “Service or repair” then “Business” (or commercial). | Jessica asks: “Is this an urgent issue requiring immediate attention, or can it be scheduled at your convenience?” |
| 2 | “Urgent” or “At my convenience.” | Jessica sets priority/timeline and continues (property type, etc.). |

**Pass:** [ ] Commercial flow includes urgency question at start.

---

## 13. Commercial — property-type questions (#14)

**Goal:** For commercial, Jessica asks property-type-specific questions from KB.

**KB/Prompt (verified):** Step 2: for Commercial, "determine property type (hotel, warehouse, school, etc.) and use the knowledge base for property-type questions." KB `customer_faq.txt` "Commercial — urgency and property type": **Property-type questions (#14)** — Hotels (rooms, ladder access/location, check-in/guests); Warehouses (ladder/height, equipment type/count, operations/safety); Schools (ladder, system type, areas, best time, security).

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Commercial flow; when asked property type, say **hotel**. | Jessica asks questions about rooms, ladder access, check-in/guests (from KB). |
| 2 | (New call) Say **warehouse**. | Questions about ladder, height, equipment type/count, operations/safety. |
| 3 | (New call) Say **school**. | Questions about ladder, system type, areas, time, security. |

**Pass:** [ ] Commercial property type → relevant KB questions asked.

---

## 14. Commercial checklist (#16)

**Goal:** For every commercial call, checklist items are collected (urgency, property type, ladder, equipment, contact, access, hours, safety).

**KB/Prompt (verified):** Step 2: "use the knowledge base for ... the full commercial checklist." KB `customer_faq.txt` "Commercial checklist (#16)": urgency; property type; ladder access and location; equipment type and quantity; point of contact; access restrictions; business hours; safety considerations. Lead/request should pass these into Odoo for technicians.

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Complete a **commercial** service request or scheduling flow. | Jessica gathers: urgency, property type, ladder access/location, equipment type/quantity, point of contact, access restrictions, business hours, safety. (Details in KB.) |
| 2 | Create lead. | In Odoo, lead description or fields contain the collected commercial checklist data for technicians. |

**Pass:** [ ] Commercial flow covers full checklist; lead in Odoo has checklist data.

---

## 15. Ring delay (#1) — optional

**Goal:** Phone rings 2–3 seconds before bot answers (config in Vapi dashboard, not repo).

| Step | You say / do | Expect |
|------|----------------|--------|
| 1 | Call the Vapi number from another phone. | Phone rings for 2–3 seconds before Jessica answers. |

**Pass:** [ ] Ring delay configured in Vapi Phone Number → Hooks → call.ringing.

---

## Quick smoke test (one call)

If you want a single end-to-end pass:

1. Call in → say “Service or repair.”
2. Answer: tenant, home, routine.
3. Give a problem (e.g. “AC not cooling”).
4. Answer diagnostic question or two.
5. Answer “Have we provided service or warranty work at your house before?” (e.g. “No”).
6. Give name, phone, address.
7. When asked “How did you hear about us?” say “Google.”
8. Let Jessica repeat back and ask “Is all of this correct?” → “Yes.”
9. Let her create the service request.

**Check:** Lead in Odoo with correct source; no errors in Vapi/backend.

---

## Sign-off

| Area | Pass |
|------|------|
| Call purpose (#17) | [ ] |
| Tenant vs PM (#11, #12) | [ ] |
| Warranty question (#19) + profile lookup (#20) | [ ] |
| Two time slots (#6) | [ ] |
| Info confirmation (#8) | [ ] |
| Lead source (#7) | [ ] |
| Post-appointment SMS + email (#9) | [ ] |
| Returning customer (#4) | [ ] |
| Diagnostic questions (#2) | [ ] |
| Maintenance assessment (#10) | [ ] |
| Commercial urgency (#13) | [ ] |
| Commercial property-type (#14) | [ ] |
| Commercial checklist (#16) | [ ] |
| Ring delay (#1) — if configured | [ ] |

**Tester:** _________________ **Date:** _________________
