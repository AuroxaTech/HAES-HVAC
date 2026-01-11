# HAES HVAC-R FINEST - AI System Testing Protocol

**Version:** 1.0  

**Date:** January 9, 2026  

**Project:** 4-Brain AI System + Voice Agent + Chat Bot  

**Client:** HVAC-R FINEST LLC

---

## 📋 Purpose

Comprehensive testing protocol to verify all AI voice agent functionality, 4-brain system logic, Odoo integrations, and business workflows before production launch.

---

## 🎯 Test Environment Details

### Test Phone Numbers

**Primary Test Number:** +1 (855) 768-3265 (Existing Twilio)  

**Production Number:** (972) 372-4458 (To be ported)

### Test Contacts (Use REAL Phone Numbers)

**CRITICAL:** All testers MUST use their actual phone numbers to receive calls/SMS.

**Approved Test Team:**

- **Junior Dikousman** - 972-856-8995 (Owner/Top Tech)
- **Linda** - [Get phone number] (Back Office Manager)
- **Bounthon Dikousman** - 945-226-0222 (Senior Tech)
- **Aubry Ritchie** - 910-238-0011 (Senior Tech)
- **Innova Testing Team** - [Your numbers]

### Test Service Areas

**Use these addresses for location-based routing tests:**

- **DeSoto/Home Zone:** 123 Main St, DeSoto, TX 75115
- **West Zone:** 456 Oak Ave, Arlington, TX 76010
- **East Zone:** 789 Elm St, Rockwall, TX 75087
- **Out of Territory:** 321 Pine Dr, Austin, TX 78701

### Test Accounts in Odoo

**Create these test customers in Odoo CRM before testing:**

1. **Residential Test Customer**
    - Name: Test Homeowner 1
    - Type: Retail Pricing
    - Address: 123 Main St, DeSoto, TX 75115
    - Phone: [Tester's real number]
2. **Commercial Test Customer**
    - Name: Test Business 1
    - Type: Com Pricing
    - Address: 456 Oak Ave, Arlington, TX 76010
    - Phone: [Tester's real number]
3. **Property Management Test**
    - Name: Test PM Company
    - Type: Default-PM Pricing
    - Address: 789 Elm St, Rockwall, TX 75087
    - Phone: [Tester's real number]

---

## ⚠️ Before You Start - CRITICAL SETUP

### ✅ Pre-Testing Checklist

- [ ]  Vapi assistant configured and active
- [ ]  Twilio phone number forwarding to Vapi
- [ ]  [Fly.io](http://Fly.io) backend is deployed and healthy
- [ ]  Odoo API connection tested
- [ ]  All 4 AI Brains loaded (CORE, OPS, REVENUE, PEOPLE)
- [ ]  HAEL Command Engine active
- [ ]  Test accounts created in Odoo
- [ ]  Testers have real phone numbers ready
- [ ]  Email notifications configured
- [ ]  SMS notifications configured
- [ ]  Recording consent enabled

### 🔐 Access Requirements

- [ ]  Vapi dashboard access (to review call logs)
- [ ]  Odoo admin access (to verify lead creation)
- [ ]  [Fly.io](http://Fly.io) logs access (to debug issues)
- [ ]  Twilio call logs access
- [ ]  Email access (Junior & Linda accounts)

---

## 📊 Testing Methodology

### Test Result Recording

For each test, document:

**Format:**

```
Test Date: __________
Tester Name: __________
Test Duration: _____ minutes
Test Phone Number Used: __________
Actual Results: [What happened]
PASS / FAIL: [ ]
Client Feedback: [Notes from Junior/Linda]
Critical Issues: [Must fix before launch]
High Priority Issues: [Should fix soon]
Low Priority Issues: [Nice to have]
```

### Issue Priority Levels

**🔴 CRITICAL** (Must fix before launch):

- Security vulnerabilities
- Incorrect pricing applied
- Failed lead creation in Odoo
- Wrong technician assignment
- No notifications sent
- System crashes
- Data loss

**🟡 HIGH PRIORITY** (Should fix soon):

- Poor user experience
- Inconsistent behavior
- Missing expected features
- Integration errors (non-critical)
- Slow response times

**🟢 LOW PRIORITY** (Nice to have):

- Minor UX improvements
- Edge case refinements
- Performance optimizations
- Additional convenience features

---

## 🎙️ SECTION 1: VOICE AGENT - INBOUND CALLS

### Test 1.1: Basic Call Answer & Greeting

**Scenario:** Verify AI answers call and delivers correct greeting

**Test Steps:**

1. Call test number: +1 (855) 768-3265
2. Wait for AI to answer
3. Listen to greeting

**Expected Behavior:**

- ✅ AI answers after 2 rings maximum
- ✅ Greeting: "Thank you for calling HVACR FINEST, this is Jessica, how can I help you today?"
- ✅ Voice tone: Professional, friendly, caring, balanced formality
- ✅ Pacing: Moderate (not too fast or slow)
- ✅ NO background noise or robotic sound

**Test Questions:**

- Does AI answer promptly?
- Is greeting word-for-word correct?
- Does voice sound natural and professional?
- Is there any awkward pause before greeting?

---

**Client Feedback:**

**Status**:

- [ ]  Pass
- [ ]  Fail

**Issues Found**:

```

```

---

### Test 1.2: Emergency - No Heat (Below 55°F)

**Scenario:** Customer calls with heating emergency

**Test Phone Number:** [Use your real number]

**Test Script:**

```
You: "Hi, my heater isn't working and it's freezing in my house!"
AI: [Should recognize emergency]
You: "It's about 50 degrees inside"
AI: [Should qualify emergency]
You: "I'm at 123 Main St, DeSoto, TX 75115"
AI: [Should collect details and create emergency lead]
```

**Expected Behavior:x**

- ✅ AI recognizes "no heat" as potential emergency
- ✅ AI asks about indoor temperature
- ✅ AI confirms emergency when temp below 55°F
- ✅ AI prioritizes as CRITICAL
- ✅ AI collects: Name, Phone, Address, System type
- ✅ AI routes to OPS-BRAIN
- ✅ AI creates lead in Odoo with "Emergency" tag
- ✅ AI assigns to nearest qualified tech (Junior - DeSoto zone)
- ✅ AI mentions: "We can have a technician there within 1.5-3 hours"
- ✅ AI applies emergency pricing: Retail = $187.50 after-hours premium
- ✅ Notifications sent to: Dispatch, Linda, Junior
- ✅ SMS sent to customer confirming appointment

**Status**:

- [ ]  Pass
- [ ]  Fail

**Issues Found**:

```

```

---

### Test 1.3: Emergency - No AC (Above 85°F)

**Scenario:** Customer calls with AC emergency

**Test Phone Number:** [Use your real number]

**Test Script:**

```
You: "My air conditioning stopped working and it's really hot!"
AI: [Should recognize emergency]
You: "It's 92 degrees inside right now"
AI: [Should qualify emergency]
You: "456 Oak Ave, Arlington, TX 76010"
AI: [Should route to West zone tech]
```

**Expected Behavior:**

- ✅ AI recognizes emergency (temp > 85°F)
- ✅ AI routes to OPS-BRAIN
- ✅ AI assigns to Bounthon (West zone - Arlington)
- ✅ Lead created in Odoo with CRITICAL priority
- ✅ Emergency pricing applied
- ✅ All notifications sent

**Status**:

- [ ]  Pass
- [ ]  Fail

**Issues Found**:

```

```

---

---

**Client Feedback:**

---

### Test 1.4: Standard Service Request - Diagnostic

**Scenario:** Customer needs diagnostic visit (non-emergency)

**Test Phone Number:** [Use your real number]

**Test Script:**

```
You: "My AC isn't cooling as well as it should"
AI: [Should identify non-emergency service]
You: "It's working, just not as cold"
AI: [Should schedule diagnostic]
You: "789 Elm St, Rockwall, TX 75087"
You: "How much will this cost?"
AI: [Should provide diagnostic fee based on customer type]
```

**Expected Behavior:**

- ✅ AI identifies as standard service (not emergency)
- ✅ AI routes to OPS-BRAIN
- ✅ AI collects: Name, Phone, Address, Problem description
- ✅ AI assigns to Aubry (East zone - Rockwall)
- ✅ AI mentions diagnostic fee: $125 (Retail pricing)
- ✅ AI offers appointment times
- ✅ Lead created with "Diagnostic Visit" service type
- ✅ Priority: HIGH (but not critical)
- ✅ Duration: 1-1.5 hours scheduled

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.5: Maintenance Request - Tune-Up

**Scenario:** Customer wants routine maintenance

**Test Phone Number:** [Use your real number]

**Test Script:**

```
You: "I'd like to schedule a maintenance tune-up for my AC"
AI: [Should identify maintenance request]
You: "Do you have any membership plans?"
AI: [Should mention Basic $279/year and Commercial $379/year]
You: "What does that include?"
AI: [Should mention VIP contract benefits]
```

**Expected Behavior:**

- ✅ AI routes to OPS-BRAIN
- ✅ AI mentions maintenance plans
- ✅ AI collects address and customer type
- ✅ Service type: "Routine Maintenance / Tune-Up"
- ✅ Priority: MEDIUM
- ✅ Duration: 45-90 minutes
- ✅ Pricing: Based on customer type + membership status
- ✅ Lead created in Odoo
- ✅ Assigned to nearest available tech

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.6: Installation Quote Request

**Scenario:** Customer wants new system installation quote

**Test Phone Number:** [Use your real number]

**Test Script:**

```
You: "I need to replace my whole HVAC system"
AI: [Should route to REVENUE-BRAIN]
You: "It's a 2,000 square foot home"
You: "The current system is about 15 years old"
You: "Do you offer financing?"
AI: [Should mention Greensky, FTL, Microft]
You: "What's the price range?"
AI: [Should provide range based on system type]
```

**Expected Behavior:**

- ✅ AI routes to REVENUE-BRAIN
- ✅ AI collects: Property type, Square footage, System age, Budget range, Timeline
- ✅ AI asks: Utility type (Gas/Electric), Number of systems, Ductwork condition
- ✅ AI mentions financing options
- ✅ AI provides price range: $6,526-$8,441 (based on system type)
- ✅ AI offers to schedule assessment
- ✅ Lead created with "Install Inquiry" type
- ✅ Lead qualified as HOT/WARM/COLD
- ✅ Assigned to Junior (high-value lead >$10K)
- ✅ Follow-up automation triggered

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.7: Pricing Question - Multiple Tiers

**Scenario:** Test correct pricing tier application

**Test Phone Number:** [Use your real number]

**Test Script A - Residential:**

```
You: "How much is a diagnostic visit?"
AI: [Should ask customer type]
You: "I'm a homeowner"
AI: [Should quote Retail pricing: $125]
```

**Test Script B - Property Management:**

```
You: "How much is a diagnostic visit?"
You: "I manage rental properties"
AI: [Should quote Default-PM pricing: $85]
```

**Test Script C - Commercial:**

```
You: "How much is a diagnostic visit?"
You: "I own a restaurant"
AI: [Should quote Com pricing: $250]
```

**Expected Behavior:**

- ✅ AI correctly identifies customer type
- ✅ AI applies correct pricing tier
- ✅ AI mentions trip charges if applicable
- ✅ AI mentions emergency/weekend premiums if relevant

**Pricing Matrix to Verify:**

| Customer Type | Diagnostic | Trip Charge | Emergency | Weekend |
| --- | --- | --- | --- | --- |
| Retail | $125 | $99 | $187.50 | $249 |
| Default-PM | $85 | $85 | $125 | $175 |
| Commercial | $250 | $179 | $350 | $350 |
| Com-Lessen | $125 | $75 | $175 | $250 |
| Hotels/Multi | $155 | $99 | $299 | $349 |

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.8: Appointment Rescheduling

**Scenario:** Existing customer wants to reschedule

**Test Phone Number:** [Use real number of test account]

**Test Script:**

```
You: "I need to reschedule my appointment"
AI: [Should look up existing appointment]
You: "It's under [Test Customer Name]"
AI: [Should find appointment]
You: "Can we move it to next Tuesday?"
AI: [Should check availability and reschedule]
```

**Expected Behavior:**

- ✅ AI routes to OPS-BRAIN
- ✅ AI looks up existing appointment in Odoo
- ✅ AI finds customer record
- ✅ AI shows current appointment details
- ✅ AI offers alternative times
- ✅ AI updates appointment in Odoo
- ✅ AI sends updated SMS confirmation
- ✅ AI notifies assigned technician

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.9: Appointment Cancellation

**Scenario:** Customer wants to cancel appointment

**Test Phone Number:** [Use real number]

**Test Script:**

```
You: "I need to cancel my appointment"
AI: [Should look up appointment]
You: "Yes, I need to cancel completely"
AI: [Should confirm cancellation]
```

**Expected Behavior:**

- ✅ AI routes to OPS-BRAIN
- ✅ AI finds appointment
- ✅ AI confirms cancellation reason (optional)
- ✅ AI cancels in Odoo
- ✅ AI applies cancellation policy if applicable
- ✅ AI sends cancellation confirmation
- ✅ AI notifies dispatch team
- ✅ AI frees up technician schedule slot

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.10: Billing Inquiry

**Scenario:** Customer asks about payment/invoice

**Test Phone Number:** [Use real number]

**Test Script:**

```
You: "When is my payment due?"
AI: [Should route to CORE-BRAIN]
You: "[Provide test customer name]"
AI: [Should look up invoice]
You: "How much do I owe?"
AI: [Should provide balance]
```

**Expected Behavior:**

- ✅ AI routes to CORE-BRAIN
- ✅ AI looks up customer in Odoo
- ✅ AI finds outstanding invoices
- ✅ AI provides: Balance, Due date, Payment methods
- ✅ AI mentions: Cash/Card/Zelle accepted
- ✅ AI mentions payment terms based on customer type
    - Retail: Due on invoice
    - Commercial: Net 15
    - Property Management: Net 30
- ✅ AI mentions 1% late fee if overdue
- ✅ AI offers to email invoice

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.11: Warranty Claim

**Scenario:** Customer has warranty issue

**Test Phone Number:** [Use real number]

**Test Script:**

```
You: "I have a warranty issue - you just fixed my AC last week and it's not working again"
AI: [Should recognize warranty situation]
You: "[Provide details]"
AI: [Should create warranty service request]
```

**Expected Behavior:**

- ✅ AI routes to OPS-BRAIN
- ✅ AI identifies as warranty service
- ✅ AI looks up recent service history
- ✅ AI creates warranty job
- ✅ Priority: 2nd highest (return trip within 24 hours)
- ✅ AI assigns to SAME technician who did original work
- ✅ AI mentions warranty terms:
    - Repairs: 30-day labor warranty
    - Equipment: 1-year labor warranty
- ✅ AI schedules return visit
- ✅ AI does NOT charge diagnostic fee

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

### Test 1.12: Complaint / Escalation

**Scenario:** Unhappy customer with complaint

**Test Phone Number:** [Use real number]

**Test Script:**

```
You: "I'm not happy with the service I received"
AI: [Should handle professionally]
You: "The technician was rude and the work isn't done right"
AI: [Should collect details and escalate]
```

**Expected Behavior:**

- ✅ AI routes to CORE-BRAIN
- ✅ AI remains professional and empathetic
- ✅ AI collects: Customer name, Issue details, Service date
- ✅ AI creates escalation ticket in Odoo
- ✅ AI notifies management (Junior + Linda)
- ✅ AI does NOT make promises like "We'll fix it for free"
- ✅ AI says: "I'm documenting this and management will contact you within 24 hours"
- ✅ AI asks if customer wants immediate callback

**Prohibited Phrases to Check:**

- ❌ "We'll fix it for free"
- ❌ "We caused that"
- ❌ "We will reimburse you"
- ❌ "We are responsible for damages"
- ❌ "I promise"

**Actual Results:**

**Actual Results:**

---

**Test Status:**

- [ ]  ✅ PASS
- [ ]  ❌ FAIL

**Issues Found:**

---

**Client Feedback:**

---

### Test 1.13: After-Hours Call (5pm - 8am)

**Scenario:** Customer calls after business hours

**Test Phone Number:** [Use real number]

**Test Time:** After 5pm CST or before 8am CST

**Test Script:**

```
You: "Hi, my AC just stopped working"
AI: [Should handle after-hours]
You: "Can someone come tonight?"
AI: [Should mention after-hours availability]
```

**Expected Behavior:**

- ✅ AI answers (not voicemail)
- ✅ AI handles call same as business hours
- ✅ AI mentions after-hours premium:
    - Retail: $187.50
    - Commercial: $350
    - etc.
- ✅ AI books appointment for next available slot
- ✅ AI mentions: "We're booked at this time, our next availability is [weekday]. If an opening becomes available over the weekend, we'll reach out. To lock you in, we have [date/time] during the week."
- ✅ Emergency calls get immediate dispatch authorization
- ✅ Non-emergency calls scheduled for next business day

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

### Test 1.14: Weekend Call

**Scenario:** Customer calls on Saturday or Sunday

**Test Phone Number:** [Use real number]

**Test Time:** Saturday or Sunday

**Test Script:**

```
You: "Can I schedule service for today?"
AI: [Should mention weekend availability]
```

**Expected Behavior:**

- ✅ AI mentions: "All weekends are booked out"
- ✅ AI offers: "If an opening becomes available, we'll reach out"
- ✅ AI books for next available weekday
- ✅ AI applies weekend premium if applicable
- ✅ Emergency calls get priority consideration

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

### Test 1.15: Out of Service Area

**Scenario:** Customer calls from outside 35-mile radius

**Test Phone Number:** [Use real number]

**Test Script:**

```
You: "I need AC service"
You: "I'm in Austin, Texas" [Outside service area]
AI: [Should identify out of area]
```

**Expected Behavior:**

- ✅ AI identifies address outside 35-mile radius of downtown Dallas
- ✅ AI politely explains: "We service within 35 miles of downtown Dallas"
- ✅ AI does NOT create lead for out-of-area
- ✅ AI offers to take contact info for future expansion
- ✅ AI remains professional and helpful

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

### Test 1.16: Complex Technical Question

**Scenario:** Customer asks technical question requiring human

**Test Phone Number:** [Use real number]

**Test Script:**

```
You: "Can you tell me if my R-22 refrigerant system can be converted to R-410A?"
AI: [Should recognize complex technical question]
```

**Expected Behavior:**

- ✅ AI recognizes question is complex/technical
- ✅ AI says: "That's a great technical question. Let me connect you with one of our expert technicians who can give you the best guidance."
- ✅ AI attempts to transfer to customer service (if business hours)
- ✅ AI collects contact info if after hours
- ✅ AI creates callback task in Odoo
- ✅ AI does NOT attempt to answer without expertise

**Prohibited Phrases:**

- ❌ "That will definitely fix it"
- ❌ "It's probably nothing"
- ❌ "You don't need a technician"

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

### Test 1.17: Transfer to Human

**Scenario:** Test live transfer capability

**Test Phone Number:** [Use real number]

**Test Time:** During business hours (8am-5pm CST)

**Test Script:**

```
You: "I'd like to speak with someone"
AI: [Should offer transfer]
```

**Expected Behavior:**

- ✅ AI says: "I'd be happy to connect you with our customer service team"
- ✅ AI confirms: "Please hold while I transfer you"
- ✅ Transfer happens smoothly (no dropped call)
- ✅ Transfer to: Customer Service team member
- ✅ After hours: AI explains no one available, offers callback

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

### Test 1.18: Voicemail & SMS Fallback

**Scenario:** Test voicemail and SMS when customer doesn't answer

**Test Steps:**

1. Call test number
2. Hang up before AI finishes collecting all info
3. Wait for SMS fallback

**Expected Behavior:**

- ✅ AI sends SMS within 2 minutes: "Thanks for calling HVACR FINEST. We'd love to help! Please reply with your service needs or call us back at (972) 372-4458."
- ✅ AI creates partial lead in Odoo with "Incomplete" status
- ✅ AI notifies dispatch team
- ✅ Follow-up task created

**Actual Results:**

**PASS / FAIL:** [ ]

**Client Feedback:**

---

## 🔄 SECTION 2: COMMAND ENGINE (HAEL) ROUTING TESTS

### Test 2.1: "My AC broke" → OPS-BRAIN

**Test Script:**

```
Call and say: "My AC broke"
```

**Expected Routing:**

- ✅ HAEL analyzes: Emergency repair
- ✅ Routes to: OPS-BRAIN
- ✅ OPS-BRAIN creates: Odoo lead with Emergency tag
- ✅ Routes to: Emergency queue
- ✅ Schedules: Emergency call

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 2.2: "How much for new system" → REVENUE-BRAIN

**Test Script:**

```
Call and say: "How much does a new HVAC system cost?"
```

**Expected Routing:**

- ✅ HAEL analyzes: Quote request
- ✅ Routes to: REVENUE-BRAIN
- ✅ REVENUE-BRAIN: Gathers details (sq ft, system type)
- ✅ Creates: Quote lead
- ✅ Starts: Follow-up automation

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 2.3: "When is my payment due" → CORE-BRAIN

**Test Script:**

```
Call and say: "When do I need to pay my invoice?"
```

**Expected Routing:**

- ✅ HAEL analyzes: Billing inquiry
- ✅ Routes to: CORE-BRAIN
- ✅ CORE-BRAIN: Looks up invoice in Odoo
- ✅ Provides: Balance and due date

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 2.4: "I want to join maintenance club" → REVENUE-BRAIN

**Test Script:**

```
Call and say: "Tell me about your maintenance membership"
```

**Expected Routing:**

- ✅ HAEL analyzes: Membership inquiry
- ✅ Routes to: REVENUE-BRAIN
- ✅ REVENUE-BRAIN: Explains plans ($279 basic, $379 commercial)
- ✅ Creates: Membership lead
- ✅ Starts: Enrollment flow

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 2.5: "I have a complaint" → CORE-BRAIN

**Test Script:**

```
Call and say: "I'm very upset about the service I received"
```

**Expected Routing:**

- ✅ HAEL analyzes: Escalation
- ✅ Routes to: CORE-BRAIN
- ✅ CORE-BRAIN: Creates escalation ticket
- ✅ Notifies: Junior + Linda immediately

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 💼 SECTION 3: ODOO INTEGRATION TESTS

### Test 3.1: Lead Creation - Residential

**Test Steps:**

1. Call and request service (residential address)
2. Complete full call flow
3. Check Odoo CRM for lead

**Expected in Odoo:**

- ✅ Lead created within 60 seconds
- ✅ Customer type: Retail
- ✅ All fields populated: Name, Phone, Email, Address
- ✅ Service type: [Correct type]
- ✅ Priority: [Correct priority]
- ✅ Assigned to: Bounthon or Aubry (based on zone)
- ✅ Lead source: "AI Voice Agent"
- ✅ Tags: Correct tags applied

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 3.2: Lead Creation - Commercial

**Test Steps:**

1. Call and mention "I own a restaurant" or commercial property
2. Complete call
3. Check Odoo

**Expected in Odoo:**

- ✅ Lead created
- ✅ Customer type: Commercial
- ✅ Pricing tier: Com Pricing
- ✅ Assigned to: Junior or Bounthon
- ✅ All commercial-specific fields captured

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 3.3: Lead Creation - Property Management

**Test Steps:**

1. Call and mention "I manage rental properties"
2. Complete call
3. Check Odoo

**Expected in Odoo:**

- ✅ Lead created
- ✅ Customer type: Property Management
- ✅ Pricing tier: Default-PM
- ✅ Property management company name captured
- ✅ Tax-exempt flag set (if Lessen)
- ✅ Payment terms: Net 30

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 3.4: Lead Routing - Geographic Zones

**Test DeSoto (Home Zone):**

- Address: 123 Main St, DeSoto, TX
- Expected assignment: Junior

**Test Arlington (West Zone):**

- Address: 456 Oak Ave, Arlington, TX
- Expected assignment: Bounthon

**Test Rockwall (East Zone):**

- Address: 789 Elm St, Rockwall, TX
- Expected assignment: Aubry

**Verification:**

- ✅ Correct tech assigned based on service area
- ✅ Tech skills match service type
- ✅ Tech availability considered

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 3.5: Appointment Creation in Odoo Field Service

**Test Steps:**

1. Book appointment via voice
2. Check Odoo Field Service module

**Expected in Odoo:**

- ✅ Appointment created in Field Service
- ✅ Assigned to correct technician
- ✅ Scheduled for correct date/time
- ✅ Duration: Matches service type (e.g., Diagnostic = 1-1.5 hrs)
- ✅ Address populated
- ✅ Customer linked
- ✅ Service type set
- ✅ Status: "Scheduled"

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 3.6: Quote Generation

**Test Steps:**

1. Request installation quote via voice
2. AI collects all details
3. Check Odoo for quote

**Expected in Odoo:**

- ✅ Quote created in Sales/Quotes
- ✅ Customer information linked
- ✅ Line items: Based on system type
- ✅ Pricing: Correct tier applied
- ✅ Quote valid for: [X] days
- ✅ Quote status: "Draft" (pending approval if >$20K)
- ✅ Assigned to: Junior (high-value), Linda (mid-value), or Auto-approved (<$20K)

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 3.7: Invoice Lookup

**Test Steps:**

1. Create test invoice in Odoo manually
2. Call AI and ask about invoice
3. Verify AI retrieves correct information

**Expected Behavior:**

- ✅ AI finds invoice by customer name or account
- ✅ AI provides: Total amount, Amount paid, Balance due, Due date
- ✅ AI mentions payment methods
- ✅ AI mentions late fees if overdue

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 📧 SECTION 4: NOTIFICATION TESTS

### Test 4.1: Email Notifications - New Lead

**Test Steps:**

1. Complete service request call
2. Check email inboxes

**Expected Emails Sent To:**

- ✅ Junior: [junior@hvacrfinest.com](mailto:junior@hvacrfinest.com)
- ✅ Linda: [Linda's email]
- ✅ Dispatch Team
- ✅ [info@hvacrfinest.com](mailto:info@hvacrfinest.com)

**Email Should Contain:**

- ✅ Customer name
- ✅ Phone number
- ✅ Address
- ✅ Service type
- ✅ Priority level
- ✅ Assigned technician
- ✅ Link to Odoo lead

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 4.2: SMS Notifications - Appointment Confirmation

**Test Steps:**

1. Book appointment
2. Check for SMS on customer phone

**Expected SMS:**

- ✅ Sent within 2 minutes
- ✅ Contains: Date, Time, Technician name, Service type
- ✅ Contains: "Reply CONFIRM or CANCEL"
- ✅ Professional format

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 4.3: SMS Reminder - 2 Hours Before Appointment

**Test Steps:**

1. Create appointment scheduled 2+ hours in future
2. Wait for reminder SMS

**Expected SMS:**

- ✅ Sent exactly 2 hours before appointment
- ✅ Contains: "Your HVACR FINEST appointment is in 2 hours"
- ✅ Contains: Technician name, service type
- ✅ Reply option to reschedule

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 4.4: Escalation Notification - Management

**Test Steps:**

1. Create complaint/escalation
2. Check if Junior & Linda receive immediate alert

**Expected Notifications:**

- ✅ Email to Junior (immediate)
- ✅ Email to Linda (immediate)
- ✅ SMS to Junior (immediate)
- ✅ SMS to Linda (immediate)
- ✅ Priority flagged as URGENT
- ✅ Escalation ticket created in Odoo

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 💰 SECTION 5: REVENUE-BRAIN - SALES PROTOCOLS

### Test 5.1: PrimeFlow™ - Same-Day Online Sales

**Test Steps:**

1. Call and say: "I want to buy a new system right now"
2. Provide: Address, square footage, photos (if possible), deposit
3. Track pipeline stages

**Expected Pipeline Flow:**

1. ✅ Quote Approved - Hold (after deposit collected)
2. ✅ Fast verification dispatch (30-45 min tech inspection)
3. ✅ Paused | Return Same Day
4. ✅ If matches quote → Install released immediately
5. ✅ Completed

**Expected in Odoo:**

- ✅ Deposit recorded
- ✅ Verification appointment scheduled
- ✅ Senior tech assigned (Junior)
- ✅ Install crew queued
- ✅ Parts released notification
- ✅ Permit auto-triggered

**Controls Verified:**

- ✅ No same-day without deposit
- ✅ All photos required
- ✅ Auto audit trail created

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 5.2: ConversionFlow™ - IVR Closing System

**Test Steps:**

1. Simulate: Tech identifies install candidate
2. Tech calls IVR "Close Line"
3. AI presents proposal to customer
4. Customer voice-approves

**Expected IVR Flow:**

- ✅ AI reads proposal
- ✅ AI presents Good/Better/Best options
- ✅ AI presents financing options
- ✅ AI records customer acceptance
- ✅ AI collects deposit

**Expected in Odoo:**

- ✅ Pipeline: Quote Approved - Waiting for Parts
- ✅ Recording stored
- ✅ Financing selection recorded
- ✅ Consent captured
- ✅ Signature capture
- ✅ Install crew auto-dispatched

**Controls Verified:**

- ✅ No field discounting
- ✅ Auto financing enforcement
- ✅ All closings logged

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 5.3: Lead Qualification - Hot/Warm/Cold

**Test Hot Lead:**

```
"My AC is broken, I need someone today, money is not an issue"
```

Expected: Qualified as HOT, immediate dispatch

**Test Warm Lead:**

```
"My AC isn't cooling great, I'd like service within the next week"
```

Expected: Qualified as WARM, standard production window

**Test Cold Lead:**

```
"Just calling to get a price quote for sometime in the future"
```

Expected: Qualified as COLD, nurture automation

**Expected Routing:**

- ✅ Hot → Senior tech or sales immediately
- ✅ Warm → Standard production, follow-up automation
- ✅ Cold → Nurture drip, review building

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 5.4: Financing Presentation

**Test Steps:**

1. Request installation quote
2. Ask: "Do you offer financing?"
3. Verify AI response

**Expected Behavior:**

- ✅ AI mentions: "Yes, we partner with Greensky, FTL, and Microft"
- ✅ AI explains: "We can help you get approved quickly"
- ✅ AI offers: "Would you like me to send you financing information?"
- ✅ AI collects: Email/phone for financing info
- ✅ Follow-up automation includes financing links

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 5.5: Follow-Up Automation

**Test Scenario 1 - Quote Sent:**

1. Request quote
2. Quote sent
3. Wait for follow-up

**Expected:**

- ✅ Immediate: Thank-you text + financing options + scheduling link
- ✅ 2 days no response: Auto reminder text + email + call task for CSR

**Test Scenario 2 - "Maybe" Response:**

1. Quote sent
2. Customer says "I'll think about it"
3. Track nurture sequence

**Expected:**

- ✅ Day 1: Education email
- ✅ Day 3: Testimonial
- ✅ Day 7: Financing reminder

**Test Scenario 3 - Lost Deal:**

1. Quote rejected
2. Track reactivation drip

**Expected:**

- ✅ Day 30: Check-in email
- ✅ Day 60: Seasonal promo
- ✅ Day 90: Rebate alert

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 5.6: Membership Enrollment

**Test Steps:**

1. Call and ask about maintenance plans
2. Express interest in enrollment
3. Track enrollment flow

**Expected Behavior:**

- ✅ AI explains Basic ($279/year) vs Commercial ($379/year)
- ✅ AI mentions benefits (VIP contract)
- ✅ AI collects: Name, Address, System details
- ✅ AI creates membership lead in Odoo
- ✅ AI sends contract via SMS/email
- ✅ Payment link included
- ✅ Enrollment confirmation sent

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 👥 SECTION 6: PEOPLE-BRAIN TESTS

### Test 6.1: AI Hiring Phone Screen

**Test Steps:**

1. Call hiring IVR line
2. Complete phone screen
3. Check results in Odoo

**Expected IVR Flow:**

- ✅ Greeting: "Thank you for your interest in HVACR FINEST"
- ✅ Questions asked:
    - Current certifications (EPA 608, TDLR)
    - Years of experience
    - Availability
    - Salary expectations
    - Why interested in role
- ✅ Recording captured
- ✅ Qualification score calculated
- ✅ If qualified → Moved to "Interview" stage
- ✅ If not qualified → Polite rejection + keep on file

**Expected in Odoo:**

- ✅ Candidate record created
- ✅ Phone screen recording attached
- ✅ Qualification notes
- ✅ Next step: Interview or rejection

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 6.2: Commission Calculation - Service Work

**Test Scenario:**

- Technician: 0-24 months tenure (16% commission)
- Service work: $1,000 invoice
- No equipment sold

**Expected Commission:**

- ✅ 16% of $1,000 = $160
- ✅ Calculated automatically in Odoo
- ✅ Appears in payroll queue

**Test Scenario 2:**

- Technician: 4+ years tenure (20% commission)
- Service work: $2,000 invoice
- Equipment sold: $8,000

**Expected Commission:**

- ✅ Service: 20% of $2,000 = $400
- ✅ Equipment bonus: 2.5% of $8,000 = $200
- ✅ Total: $600

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 6.3: Installation Bonus Calculation

**Test Scenario:**

- Install crew: 2 technicians
- Installed: Complete Split System (3 pieces)
- Bonus: $1,050

**Expected:**

- ✅ Total bonus: $1,050
- ✅ Split evenly: $525 per tech
- ✅ Auto-calculated in Odoo
- ✅ Added to payroll

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 6.4: Completion Ownership Rule

**Test Scenario:**

- Tech A diagnoses and sells repair
- Parts unavailable, dispatch reroutes to Tech B
- Tech B completes repair

**Expected Commission Split:**

- ✅ Tech A (sold): 40% of service commission
- ✅ Tech B (completed): 60% of service commission
- ✅ Auto-calculated based on "approved transfer" flag
- ✅ If no approved transfer: Tech A gets 100% (or forfeits if doesn't return)

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 6.5: Time Tracking - Field Technician

**Test Steps:**

1. Simulate technician clocking in
2. Simulate job start
3. Simulate job end
4. Verify in Odoo

**Expected in Odoo:**

- ✅ Attendance record: Clock-in time
- ✅ Field Service log: Job start/end
- ✅ Travel time calculated
- ✅ GPS-linked job logs (if GPS available)
- ✅ Hours logged for payroll
- ✅ Approval workflow: Dispatch → Ops Manager → HR → Owner

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 💬 SECTION 7: WEBSITE CHAT BOT TESTS

### Test 7.1: Chat Widget Appearance

**Test Steps:**

1. Visit [https://www.hvacrfinest.com](https://www.hvacrfinest.com)
2. Observe chat widget

**Expected:**

- ✅ Widget appears in bottom-right corner
- ✅ Widget visible on ALL pages
- ✅ Auto-expands after 3 seconds (or stays collapsed)
- ✅ Brand colors applied
- ✅ Professional appearance
- ✅ Mobile responsive

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 7.2: Chat Greeting & Pre-Qualification

**Test Steps:**

1. Click chat widget
2. Read greeting
3. Fill out pre-chat form

**Expected:**

- ✅ Greeting: "Hi! 👋 Welcome to HVAC-R Finest. I can help you schedule service, request a quote, or check availability. To get started, I just need a few quick details."
- ✅ Required fields:
    - Name (required)
    - Email (required)
    - Phone (required)
    - Service needed (required)
- ✅ Tone: Enthusiastic, caring, helpful
- ✅ Cannot proceed without all fields

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 7.3: Chat Lead Creation

**Test Steps:**

1. Complete chat pre-qualification
2. Submit form
3. Check Odoo CRM

**Expected in Odoo:**

- ✅ Lead created immediately (within 60 seconds)
- ✅ Lead source: "Website Chat"
- ✅ All fields populated from chat
- ✅ Auto-assigned based on:
    - Service area
    - Service type (Residential → Bounthon/Aubry, Commercial → Junior/Bounthon)
- ✅ Notifications sent to:
    - Dispatch Team
    - Linda
    - [info@hvacrfinest.com](mailto:info@hvacrfinest.com)

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 7.4: Live Handoff (Business Hours)

**Test Steps:**

1. Start chat during business hours (8am-5pm CST)
2. Request to speak with someone
3. Verify handoff

**Expected:**

- ✅ Chat says: "I'm connecting you with customer service"
- ✅ Transfer happens smoothly
- ✅ Customer service receives notification
- ✅ Chat context passed to human
- ✅ No information lost in transfer

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 7.5: After-Hours Chat Behavior

**Test Steps:**

1. Start chat after 5pm CST
2. Complete chat flow

**Expected:**

- ✅ Chat bot handles entire conversation
- ✅ No live handoff option shown
- ✅ Message: "Our team is currently offline (8am-5pm CST)"
- ✅ Lead created for follow-up
- ✅ Callback scheduled for next business day
- ✅ Confirmation message with timeline

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 🔍 SECTION 8: EDGE CASES & ERROR HANDLING

### Test 8.1: Call Interruption / Dropped Call

**Test Steps:**

1. Start call
2. Provide partial information
3. Hang up mid-conversation
4. Check system response

**Expected:**

- ✅ Partial lead created with "Incomplete" status
- ✅ SMS sent to customer: "We lost connection, please call back"
- ✅ Callback task created in Odoo
- ✅ All captured data saved

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.2: Unclear/Garbled Speech

**Test Steps:**

1. Call and speak unclearly
2. Or speak with heavy background noise

**Expected:**

- ✅ AI asks for clarification: "I'm sorry, I didn't catch that. Could you repeat?"
- ✅ AI remains patient
- ✅ AI offers alternatives: "Would you prefer to receive a callback?"
- ✅ AI doesn't give up after 1-2 failed attempts

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.3: Very Long Call (>15 minutes)

**Test Steps:**

1. Call and have extensive conversation
2. Ask many questions
3. Verify system handles lengthy call

**Expected:**

- ✅ AI maintains context throughout
- ✅ AI doesn't lose track of conversation
- ✅ AI doesn't repeat already-answered questions
- ✅ Recording captures full call
- ✅ All data saved correctly

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.4: Profanity / Abusive Language

**Test Steps:**

1. Call and use inappropriate language
2. Observe AI response

**Expected:**

- ✅ AI remains professional
- ✅ AI doesn't respond with profanity
- ✅ AI says: "I understand you're frustrated. Let me help resolve this."
- ✅ AI doesn't terminate call immediately
- ✅ If abuse continues, AI offers to escalate

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.5: Multiple Issues in One Call

**Test Steps:**

1. Call with multiple requests:
    - "I need service AND I want to pay my bill AND I want a quote for new system"

**Expected:**

- ✅ AI handles each request sequentially
- ✅ AI asks: "Let's handle these one at a time. Which is most urgent?"
- ✅ AI creates multiple leads/tasks if needed
- ✅ AI summarizes at end: "I've scheduled your service, sent your invoice, and you'll receive a quote within 24 hours"

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.6: Odoo API Down / Integration Failure

**Test Steps:**

1. Simulate Odoo API unavailable
2. Make test call
3. Verify graceful degradation

**Expected:**

- ✅ AI continues conversation
- ✅ AI captures all data locally
- ✅ AI says: "I'm experiencing a technical issue but I've captured your information"
- ✅ AI sends emergency notification to tech team
- ✅ AI provides alternative: "You'll receive a confirmation within 30 minutes"
- ✅ Data queued for retry/manual entry

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.7: Duplicate Call Prevention

**Test Steps:**

1. Call and book appointment
2. Call again immediately with same phone number
3. Observe behavior

**Expected:**

- ✅ AI recognizes returning customer
- ✅ AI says: "Welcome back! I see you just called. Would you like to modify your appointment?"
- ✅ AI doesn't create duplicate lead
- ✅ AI references existing appointment

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 8.8: Wrong Number / Misdial

**Test Steps:**

1. Call and say: "Sorry, wrong number"

**Expected:**

- ✅ AI says: "No problem! Have a great day."
- ✅ AI ends call gracefully
- ✅ No lead created
- ✅ Call logged but not actionable

**Actual Results:**

**PASS / FAIL:** [ ]

---

## 📈 SECTION 9: PERFORMANCE & QUALITY METRICS

### Test 9.1: Response Time

**Measurement:**

- Time from call start to AI greeting: _ seconds
- Time between user input and AI response: _ seconds

**Targets:**

- ✅ Greeting within 2 seconds
- ✅ Response within 1-2 seconds
- ✅ No pauses >3 seconds

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 9.2: Call Completion Rate

**Measurement:**

- Total calls made: _
- Calls completed successfully: _
- Completion rate: _%

**Target:**

- ✅ 90%+ completion rate

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 9.3: Data Accuracy

**Measurement:**

- Total fields collected: _
- Fields with correct data: _
- Accuracy rate: _%

**Target:**

- ✅ 95%+ accuracy

**Common Errors to Check:**

- Wrong phone number format
- Incorrect address
- Misspelled names
- Wrong customer type

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 9.4: User Satisfaction (1-5 Scale)

**Rate the following:**

1. Agent responds quickly: ___/5
2. Agent understands questions accurately: ___/5
3. Agent provides clear answers: ___/5
4. Information is accurate: ___/5
5. Protects sensitive data: ___/5
6. Overall satisfaction: ___/5

**Target:**

- ✅ 4.0+ average rating

**Actual Results:**

**PASS / FAIL:** [ ]

---

### Test 9.5: Common Issues Checklist

**Technical Issues:**

- [ ]  Wrong information provided
- [ ]  Call quality problems (static, echo)
- [ ]  Long pauses (>3 seconds)
- [ ]  Repetition / loops
- [ ]  System crashes

**Understanding Issues:**

- [ ]  Didn't understand question
- [ ]  Couldn't handle follow-up questions
- [ ]  Provided irrelevant answers
- [ ]  Interrupted customer

**Security Issues:**

- [ ]  No identity verification when needed
- [ ]  Shared sensitive data inappropriately
- [ ]  Read full credit card numbers
- [ ]  Couldn't find account securely

**Prohibited Phrase Usage:**

- [ ]  Used "That will definitely fix it"
- [ ]  Used "I promise"
- [ ]  Used "It's free"
- [ ]  Used "We guarantee"
- [ ]  Other prohibited phrase: _

---

## 🎯 SECTION 10: FINAL ACCEPTANCE CRITERIA

### Critical Requirements (All Must Pass)

- [ ]  AI answers 100% of calls (no missed calls)
- [ ]  All emergency calls correctly prioritized
- [ ]  All leads created in Odoo within 60 seconds
- [ ]  Geographic routing 100% accurate
- [ ]  Pricing tiers applied correctly (0 errors)
- [ ]  All notifications sent (email + SMS)
- [ ]  No security vulnerabilities found
- [ ]  No prohibited phrases used
- [ ]  Voice quality professional
- [ ]  Response time <2 seconds

### High Priority Requirements (90%+ Pass Rate)

- [ ]  Call completion rate >90%
- [ ]  Data accuracy >95%
- [ ]  User satisfaction >4.0/5
- [ ]  Integration success rate >95%
- [ ]  Follow-up automation works
- [ ]  Lead assignment accurate
- [ ]  Quote generation accurate
- [ ]  Live transfers work smoothly

### Nice to Have (70%+ Pass Rate)

- [ ]  Edge cases handled gracefully
- [ ]  Performance optimized
- [ ]  Advanced features working
- [ ]  Complex scenarios resolved

---

## 📝 FINAL SUMMARY REPORT

### Test Execution Summary

**Total Tests:** _  

**Tests Passed:** _  

**Tests Failed:** _  

**Pass Rate:** _%

### Critical Issues Found

1. 
    
    ---
    
2. 
    
    ---
    
3. 
    
    ---
    

### High Priority Issues Found

1. 
    
    ---
    
2. 
    
    ---
    
3. 
    
    ---
    

### Low Priority Issues Found

1. 
    
    ---
    
2. 
    
    ---
    

### Client Sign-Off

**Junior (Owner) Approval:**

- [ ]  Approved for production launch
- [ ]  Requires additional fixes

**Signature:** ___  

**Date:** ___

**Linda (Back Office) Approval:**

- [ ]  Approved for production launch
- [ ]  Requires additional fixes

**Signature:** ___  

**Date:** ___

---

## 🚀 GO-LIVE CHECKLIST

**Before Production Launch:**

- [ ]  All critical issues resolved
- [ ]  90%+ pass rate achieved
- [ ]  Client approval received
- [ ]  Port main number (972-372-4458) to Vapi
- [ ]  Update all business listings
- [ ]  Train customer service team
- [ ]  Set up 24/7 monitoring
- [ ]  Prepare escalation contacts
- [ ]  Document all passwords/access
- [ ]  Schedule Week 1 review meeting

**Post-Launch Monitoring (First 48 Hours):**

- [ ]  Monitor all calls in real-time
- [ ]  Check Odoo integration hourly
- [ ]  Verify notifications working
- [ ]  Track customer feedback
- [ ]  Log any issues immediately
- [ ]  Daily check-in with Junior/Linda

---

**Testing Protocol Complete!** 🎉