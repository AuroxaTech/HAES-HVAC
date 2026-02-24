# Scheduling & Urgency Implementation Plan

Implementation plan for scheduling-related changes: weekend blocking, urgency-based slot targeting, and related flows.

---

## Phase 1: Quick Scheduling Adjustments ✅ (scheduling_rules.py)

**Done:**
- Added top-of-file "QUICK ADJUSTMENTS" comment block documenting:
  - `OPERATING_DAYS` (block weekends: `[0,1,2,3,4]`, include Sat: `[0,1,2,3,4,5]`)
  - `SAME_DAY_DISPATCH_CUTOFF`, `BUSINESS_START`, `BUSINESS_END`
  - `URGENT_DAYS_OUT`, `ROUTINE_DAYS_OUT`

---

## Phase 2: Urgency-Based Slot Targeting ✅

**Done:**
- `URGENT_DAYS_OUT = 2`, `ROUTINE_DAYS_OUT = 7` in scheduling_rules.py
- `get_earliest_slot_by_urgency(after, urgency)` in scheduling_rules.py
- `check_availability` accepts `urgency` and applies it before slot search
- `check_availability.json` schema includes `urgency` enum
- System prompt: Step 5 + HARD RULES require passing urgency to tools

**Logic:**
- emergency: same-day slots (earliest possible)
- urgent: first slot 2 business days out (e.g. Mon → Wed)
- routine: first slot ~7 business days out

---

## Phase 3: schedule_appointment Urgency ✅

**Done:**
- `schedule_appointment.json` includes optional `urgency` parameter
- `schedule_appointment` Python handler passes `urgency` to `command.metadata`
- OPS handlers use `urgency` from metadata to adjust `preferred_start` when fetching slots (no `chosen_slot_start`)

---

## Phase 4: Agent Prompt ✅

**Done:**
- Step 5: "call check_availability (with ... urgency — pass the value the customer gave in Step 2)"
- New HARD RULE: "Pass Urgency to Availability Tools (MANDATORY)"

---

## Phase 5: Tech Schedule Packing & Prioritization (Future / Odoo)

**Not implemented.** When a tech's day is full, prioritize by urgency (emergency > urgent > routine). This is an Odoo FSM / dispatch concern. Document in context.json when ready.

---

## Testing Checklist

- [ ] Block weekends: set `OPERATING_DAYS = [0,1,2,3,4]`, verify no Sat/Sun slots
- [ ] Emergency: customer says "emergency" → slots same day (when before cutoff)
- [ ] Urgent: customer says "urgent" → slots 2–3 days out, not same day
- [ ] Routine: customer says "routine" → slots ~7 days out
- [ ] `preferred_time` still works (later-in-day slots)
- [ ] Duplicate-call flow: existing appointment → offer reschedule → `reschedule_appointment` when yes
- [ ] Different property: `create_service_request` called when customer wants new address

---

## Files Changed

| File | Changes |
|------|---------|
| `src/brains/ops/scheduling_rules.py` | Quick-adjust comments, URGENT_DAYS_OUT, ROUTINE_DAYS_OUT, get_earliest_slot_by_urgency |
| `src/vapi/tools/ops/check_availability.py` | urgency param, import and apply get_earliest_slot_by_urgency |
| `doc/vapi/tools/customer_facing/appointments/check_availability.json` | urgency property |
| `doc/vapi/system_prompt_customer_inbound.md` | Step 5, Pass Urgency HARD RULE |
| `doc/vapi/tools/customer_facing/appointments/schedule_appointment.json` | urgency property |
| `src/vapi/tools/ops/schedule_appointment.py` | urgency in metadata |
| `src/brains/ops/handlers.py` | import get_earliest_slot_by_urgency, apply urgency to preferred_start |
