# AI-Integrated Company Workflow

**Owner → Managers → Field → Office**

---

## OBJECTIVE

Create one Ops phone number that:

- Identifies who is calling
- Switches to the correct role workflow
- Delivers:
  - Coaching
  - KPI alignment
  - Pulse checks
  - Task execution
  - Close-out accountability
- Logs everything into Odoo
- Escalates only on rules, not emotion
- Scales without adding managers

---

## REALITY (CONSTRAINTS)

- Calls must be 60–180 seconds
- Must feel supportive, not surveillance
- Data must be structured
- One human = multiple roles (esp. owner)
- Odoo is the system of record
- Voice bot must handle branching logic
- KPI overload kills adoption

---

## SYSTEM ARCHITECTURE (HIGH LEVEL)

```
PHONE CALL
    ↓
Caller ID / PIN
    ↓
ROLE IDENTIFICATION
    ↓
ROLE-SPECIFIC AI FLOW
    ↓
STRUCTURED DATA → ODOO
    ↓
RULE-BASED ESCALATION (ONLY IF NEEDED)
```

---

## ROLE MAP (WHO USES THE OPS LINE)

| Level | Role |
|-------|------|
| **Owner** | Owner / CEO |
| **Exec** | Ops Director / GM |
| **Management** | Service Manager, Install Manager, Office Manager |
| **Field** | Technicians, Installers |
| **Office** | Dispatch, CSR, Accounting |
| **Support** | Warehouse, IT |

---

## CORE DESIGN RULES (NON-NEGOTIABLE)

1. **1–3 KPIs max per role**
2. **One daily focus**
3. **One micro-commitment**
4. **AI coaches → humans intervene only on thresholds**
5. **Every call produces data**
6. **Every role has AM + Close-Out logic**

---

## GLOBAL AI FLOW (ALL ROLES)

Every call follows this skeleton:

1. Identity & role detection
2. Pulse check (energy + blockers)
3. KPI alignment
4. Coaching (role-appropriate)
5. Task execution or confirmation
6. Commit → log → exit

---

## ROLE-SPECIFIC WORKFLOWS

### 1. OWNER / CEO (STRATEGIC MODE)

#### PURPOSE

- Stay out of ops
- Track leverage
- Prevent blind spots
- Keep vision alive without meetings

#### DAILY OWNER CHECK-IN (OPTIONAL)

**AI Prompts:**
- "What's the single constraint limiting growth today?"
- "Are you in creation or reaction mode?"
- "One decision you're avoiding?"

**KPIs:**
- Revenue trend
- Cash runway
- Manager autonomy score
- % time out of ops

**Escalation:**
- If owner logs ops work > X days → flag "system failure"

---

### 2. OPS DIRECTOR / GENERAL MANAGER

#### PURPOSE

- Run execution without firefighting

#### AM CHECK-IN

**Pulse:**
- Energy (1–5)
- Any department off-track?

**KPIs:**
- Service capacity utilization
- Callback rate
- On-time start %
- Manager escalation count

**AI COACHING:**
- "Where are you solving instead of designing?"

#### WEEKLY AI SUMMARY

- Department drift
- Manager load imbalance
- Process failures (not people)

---

### 3. SERVICE MANAGER / INSTALL MANAGER

#### PURPOSE

- Coach through data
- Remove friction for field

#### DAILY FLOW

**Pulse:**
- Team readiness %
- Any red flags?

**KPIs:**
- Close rate (service / install)
- Avg ticket
- Callbacks
- Rework %

**AI TASKS:**
- Review flagged techs
- Approve AI-recommended training
- Confirm staffing coverage

**Escalation:**
- Only if:
  - Tech burnout flag
  - Repeat KPI decline
  - Safety event

---

### 4. TECHNICIANS (CORE ENGINE)

This is your most advanced flow.

#### A) AM PULSE + COACHING (MANDATORY)

**AI FLOW:**
1. Attendance confirmation
2. Energy (1–5)
3. Blockers
4. Primary KPI focus (1 only)
5. Strength-based coaching
6. Daily micro-commitment

**TECH KPIs (ROLE-APPROPRIATE)**

**Primary KPIs (choose 1–2 per tech):**
- First-time fix rate
- Callback %
- Close rate
- Maintenance conversions
- On-time arrival

**Secondary (tracked, not coached daily):**
- Ticket avg
- Customer notes quality
- Safety compliance

#### B) PER-CALL CHECKOUT (AFTER EACH JOB)

Tech calls Ops line → "Job Close-Out Mode"

**AI CHECKLIST:**
- Was diagnosis completed? (Y/N)
- Photos uploaded? (Y/N)
- Options presented? (Y/N)
- Customer understanding confirmed? (Y/N)
- Any follow-ups needed?
- Is it possible to send docs and photo upload for each job via text or chat
- Go through maintenance sheet with key input information
- Create quote for tech based on work performed to what is being proposed

**AI ACTIONS:**
- Logs job completion
- Flags missing items
- Updates Odoo job status

#### C) END-OF-DAY CLOSE-OUT

**AI PROMPTS:**
- "Did you hit your KPI focus?"
- "One thing you did well?"
- "One thing to improve tomorrow?"

**Escalation:**
- Missed checkout steps
- Safety issues
- Repeat quality misses

---

### 5. DISPATCH / CSR

#### PURPOSE

- Control flow
- Reduce chaos
- Protect field efficiency

#### DAILY CHECK-IN

**KPIs:**
- Calls answered %
- Booking accuracy
- Tech idle time
- Reschedules caused

**AI COACHING:**
- "Where did communication break today?"

**TASK EXECUTION:**
- Confirm schedule lock
- Flag overbooking
- Route blockers to Ops Director

---

### 6. ACCOUNTING / BACK OFFICE

#### PURPOSE

- Cash clarity
- Zero surprises

#### WEEKLY AI FLOW

**KPIs:**
- Invoicing lag
- AR aging
- Vendor backlog

**AI TASKS:**
- Flag unpaid invoices
- Identify margin leaks
- Prep owner summary

---

### 7. WAREHOUSE / INVENTORY

**KPIs:**
- Truck stock accuracy
- Emergency purchases
- Return lag

**AI FLOW:**
- Confirm replenishment
- Flag stockouts
- Log variance

---

## ODOO DATA MODEL (MINIMUM)

Each call logs:

- `user_id`
- `role`
- `call_type`
- `energy_level`
- `blocker_flag`
- `primary_kpi`
- `kpi_action`
- `coach_template_used`
- `commitment`
- `job_id` (if applicable)
- `completion_status`
- `duration`

---

## ESCALATION RULES (ANTI-NOISE)

🚫 **NO human alerts unless:**

- KPI decline ≥ 2 periods
- Energy ≤ 2 for 2+ days
- Safety / compliance issue
- Missed required workflow steps

---

## SCALE LOGIC (COMPOUNDING)

- Calls → Data
- Data → AI coaching
- Coaching → Skill lift
- Skill lift → Margin
- Margin → Less management
- Less management → Scale

**This converts people effort → institutional intelligence.**

---

## TOP 3 PRIORITIES

1. Finalize role-specific KPIs
2. Lock AM Tech + Job Close-Out scripts
3. Build Odoo tables + escalation rules

---

## KPIs FOR THE SYSTEM (META)

- Daily call completion %
- KPI adherence rate
- Escalation frequency
- Manager time reclaimed
- Tech retention

---

**Document Version:** 1.0  
**Last Updated:** January 26, 2024
