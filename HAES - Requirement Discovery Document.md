# HAES - Requirement Discovery Document

# HAES - Requirement Discovery Document

**AI-Powered HVAC Business Automation System**

---

## Date: January 2, 2026

This form helps us gather the necessary information to build your four AI brain system, integrated with Odoo ERP. Based on your Simple Vendor Build Guide, we need specific details to implement CORE-BRAIN, OPS-BRAIN, REVENUE-BRAIN, and PEOPLE-BRAIN.

If you need help with any section, contact us at: [auroxatechofficial@gmail.com](mailto:auroxatechofficial@gmail.com)

---

## WHAT WE'RE BUILDING

✅ **Four Sovereign AI Brains:**

- **CORE-BRAIN:** Company leadership logic, money, pricing, accounting, reporting, and legal/compliance rules
- **OPS-BRAIN:** Dispatching, service calls, installations, scheduling, fleet routing, and inventory management
- **REVENUE-BRAIN:** All marketing campaigns, lead handling, quoting, financing, and closing sales
- **PEOPLE-BRAIN:** Hiring, onboarding, training, performance tracking, payroll rules, and KPI accountability

✅ **System Flow:**

Customer talks to voice/chat bot → system converts into structured commands → correct brain processes → Odoo updates → KPIs tracked automatically

✅ **Key Components:**

- Voice IVR Bot
- Website Chat Bot
- AI Brain Microservices
- Command Engine (HAEL)
- Odoo API Integration Layer
- KPI Dashboard

✅ **Success Definition:**

Calls book automatically, invoices auto-send, payroll auto-runs, parts auto-order, KPIs auto-optimize

---

## SECTION 1: ODOO ERP ACCESS & CREDENTIALS

### 1.1 Odoo Instance Access

We need access to your Odoo ERP system to build the API integration layer.

**Odoo Instance URL:**

```
[(https://hvacrfinest.odoo.odoo.com)]
```

**Odoo Version:**

- [ ]  Odoo 14
- [ ]  Odoo 15
- [ ]  Odoo 16
- [ ]  Odoo 17
- [x]  Odoo 18 (Enterprise)
- [ ]  Other: ___

**How to give us API access:**

**Option A: Create API User (Preferred)**

1. Log in to Odoo as an administrator
2. Go to Settings → Users & Companies → Users
3. Click the "Create" button
4. Enter details:
    - Name: Innova API User
    - Login: [auroxatechofficial@gmail.com](mailto:auroxatechofficial@gmail.com)
    - Access Rights: Check "Administration / Settings" and all required modules
5. Click Save
6. Go to the user's "API Keys" tab
7. Generate a new API key
8. Copy and provide below

```
API Username: Admin(I)
API Email: Junior@hvacrfinest.com
API Key: 36416bb976848ce6d96fc0f6b38692afbe2707f1
```

**Option B:  Admin Access**

To build the AI system correctly, I need to understand your Odoo setup
visually during the discovery phase.

- 1. Go to Odoo → Settings → Users & Companies → Users
2. Click "Create."
3. Add your details:
   - Name: Auroxa Developer
   - Login: auroxatechofficial@gmail.com
   - Access Rights: ✅ All modules
4. Send  the login credentials


**After completing, fill in below:**

```
Media@hvacrfinest.com is the user

Pw is 123456789!
```

**Client Comments:**

<aside>
💬

[Add any notes, concerns, or questions about Odoo access]

</aside>

---

### 1.2 Odoo Modules Currently Installed

**Which Odoo modules are you currently using?**

- [x]  CRM
- [x]  Sales
- [x]  Invoicing/Accounting
- [x]  Inventory
- [x]  Field Service
- [x]  Project Management
- [x]  HR/Payroll
- [x]  Marketing Automation
- [x]  Website
- [ ]  Manufacturing
- [x]  Purchase
- [x]  Other: dont know what its called, tech app

**Client Comments:**

<aside>
💬

[Add any notes about your current Odoo setup]

</aside>

---

## SECTION 2: COMPANY & BUSINESS INFORMATION

### 2.1 Company Details

**Legal Company Name:**

```
HVAC-R FINEST LLC
```

**Doing Business As (DBA):**

```
[If different from legal name]
```

**Primary Business Address:**

```

```

**Service Territory:**

```
35mile radius of downtown dallas
```

**Client Comments:**

<aside>
💬

[Add any notes about your company information]

</aside>

---

### 2.2 Business Hours & Availability

**Regular Business Hours:**

```clojure
Monday: _______________
Tuesday: _______________
Wednesday: _______________
Thursday: _______________
Friday: _______________
Saturday: _______________
Sunday: _______________

24/7 service hrs
all weeekends are booked out
```

**After-Hours Emergency Service:**

- [x]  Yes - Details: always offer, mention we are booked at this time our next availability is a weekday. also if an open is available over the weekend we will reach out but to lock you in we have xyz time and date during the week
- [ ]  No

**Holidays/Closures:**

```

New Year’s Day
Memorial Day
4th of July
Labor Day
Veteran’s Day
Thanksgiving Day
Black Friday
Christmas Day
Christmas Eve
Week after Christmas

```

**Client Comments:**

<aside>
💬

[Add any notes about business hours or availability]

</aside>

---

## SECTION 3: CORE-BRAIN CONFIGURATION

*Pricing, accounting, compliance, reporting*

**Why We Need This Information:**

The CORE-BRAIN is your company's financial intelligence center. It handles all pricing decisions, invoice generation, revenue tracking, compliance requirements, and management reporting automatically. To build this brain correctly, we need to understand your pricing structure, accounting rules, legal requirements, and approval workflows. This ensures the system quotes accurately, invoices properly, stays compliant, and requires human approval only when necessary.

---

**Service Call Pricing:**

```

## 1️⃣ **Default-PM**

(Property Management / National Accounts / Portals)

| Fee Type                            | Amount   |
| ----------------------------------- | -------- |
| **Diagnostic Fee**                  | **$85** |
| **Trip Charge**                     | **$85**  |
| **Emergency / After-Hours Premium** | **$125** |
| **Weekend / Holiday Premium**       | **$175** |

## 2️⃣ **Retail Pricing**

(Standard Residential Homeowners)

| Fee Type                            | Amount   |
| ----------------------------------- | -------- |
| **Diagnostic Fee**                  | **125** |
| **Trip Charge**                     | **$99** |
| **Emergency / After-Hours Premium** | **$187.5** |
| **Weekend / Holiday Premium**       | **$249** |

## 3️⃣ **Com Pricing**

(Commercial Offices, Clinics, Plazas, Restaurants)

| Fee Type                            | Amount   |
| ----------------------------------- | -------- |
| **Diagnostic Fee**                  | **$250** |
| **Trip Charge**                     | **$179** |
| **Emergency / After-Hours Premium** | **$350** |
| **Weekend / Holiday Premium**       | **$350** |

## 4️⃣ **Com Pricing – Lessen**

(National Commercial / Warranty / Flat-Rate Portal Accounts)

| Fee Type                            | Amount   |
| ----------------------------------- | -------- |
| **Diagnostic Fee**                  | **$125** |
| **Trip Charge**                     | **$75** |
| **Emergency / After-Hours Premium** | **$175** |
| **Weekend / Holiday Premium**       | **$250** |

## 5️⃣ **Com Pricing – Hotels / Multifamily**

| Fee Type                            | Amount   |
| ----------------------------------- | -------- |
| **Diagnostic Fee**                  | **$155** |
| **Trip Charge**                     | **$99** |
| **Emergency / After-Hours Premium** | **$299** |
| **Weekend / Holiday Premium**       | **$349** |

```

**Labor Rates:**

```
Standard Hourly Rate: $ this is the diagnotic rate for each type of client
Senior Technician Rate: 15 to 20 percent of service incurrent and it they do repair its total invoice 
Helper/Apprentice Rate: $15 to 18
Overtime Multiplier: 1.5
```

**Equipment Installation Pricing:**

- [x]  Fixed pricing tiers
- [ ]  Quote-based (on-site assessment required)
- [x]  Hybrid approach

**Price Ranges (if applicable):**

```
Condenser + Evap Coil Replacement	$6,251
Furnace + Evap Coil Replacement	$5,602
Condenser Only Replacement	$5,213
Heat Pump Unit Only Replacement	$5,888
Evaporator Coil Only Replacement	$3,952
Air Handler Only Replacement	$5,145
Furnace Only Replacement	$4,671
```

| System Type |  |  | **FINAL CUSTOMER PRICE** |
| --- | --- | --- | --- |
| **Complete Furnace + AC (Gas Split)** |  |  | **$8,410** |
| **Complete Heat Pump (Split)** |  |  | **$8,441** |
| **Straight Cool (AC Only)** |  |  | **$8,426** |
| **Packaged Gas System** |  |  | **$7,095** |
| **Packaged Electric Heat Pump** |  |  | **$7,578** |
| **Packaged Cooling Only** |  |  | **$6,526** |
|  |  |  |  |

**Maintenance Plan Pricing:**

```csharp
Basic Plan: $279/year - Includes: vip contract

Commercial Plan: $379/year - Includes: commerical contract
V
```

**Payment Terms:**

```
Standard Payment Terms: due on invoice/ commerical is 15 days/ Property management is 30days
accepted Payment Methods: cash/ card/ zelle
```

**Financing Available:**

- [x]  Yes
- [ ]  No

```
Financing Partner: Optimus= Greensky, FTL, Microft
```

**Client Comments:**

<aside>
💬

[Add any notes about your pricing structure]

</aside>

---

### 3.2 Financial & Accounting Rules

**Revenue Recognition:**

**When is revenue recognized?**

- [ ]  Upon completion
- [ ]  Upon invoice
- [x]  Upon payment

**Invoice Generation:**

```
Automatic invoice trigger: when tech is complete job and workorder is paided
Invoice due terms: _______________
Late payment fees: 1 percent
```

**Tax Configuration:**

```
Sales tax rate(s): texas tax rate
```

**Tax-exempt customers:**

- [x]  Yes
- [ ]  No

```
How to identify: only for Lessen (property management) 
```

**Chart of Accounts:**

```
Revenue accounts by service type: 
400000	Service/Fee Income	
Income

420000	IAQ	
Income

430000	Maintenance Contracts	
Income

432000	Membership Revenue	
Income

441000	Foreign Exchange Gain	
Income

442000	Cash Difference Gain	
Income

443000	Interest Earned	
Other Income

444000	Billable Expense Income	
Income

450000	Other Primary Income	
Other Income

451100	Credit Card Rebates	
Other Income

470000	Unapplied Cash Payment Income	
Income

480000	Uncategorized Income	
Income

705000	Customer Tip	
Other Income

Expense accounts for parts/labor:
446000	Discounts	
Expenses

500000	Cost of Goods Sold	
Cost of Revenue

511000	Commissions	
Cost of Revenue

514000	Job Supplies	
Cost of Revenue

515000	Labor	
Cost of Revenue

517000	Permits	
Cost of Revenue

518000	Sub Contractors	
Cost of Revenue

521000	Warranty	
Cost of Revenue

547000	Equipment Operational Costs	
Expenses

600000	Expenses	
Expenses

605000	Stripe Processing Fee	
Expenses

610000	Cash Discount Loss	
Expenses

6240	Lead Generation	
Expenses

645000	Advertising & Marketing	
Expenses

647000	Automobil Expense	
Expenses

648000	Automobil Expense:Gas	
Expenses

649000	Bank Charges & Fees	
Expenses

650000	Car & Truck	
Expenses

652000	Computer & Internet Expense	
Expenses

653000	Continuing Education	
Expenses

654000	Contractor Employee Benefit	
Expenses

655000	Contractors	
Expenses

656000	Deductions - Cost of Goods Chargeback	
Expenses

657000	Dues & Subscriptions	
Expenses

658000	Employee Benefits	
Expenses

659000	Employer Benefits	
Expenses

660000	Employer Taxes	
Expenses

661000	Equipment (COGS)	
Expenses

662000	General Liability Insurance	
Expenses

663000	Insurance	
Expenses

664000	Interest Paid	
Expenses

665000	Legal & Professional Services	
Expenses

667000	Meals & Entertainment	
Expenses

668000	Medical	
Expenses

669000	Merchant Expense	
Expenses

671000	Office Supplies & Software	
Expenses

672000	Operations Expense	
Expenses

673000	Other Business Expenses	
Expenses

676000	Payroll Expenses	
Expenses

677000	Payroll Expenses:Taxes	
Expenses

678000	Payroll Expenses:Wages	
Expenses

679000	Postage	
Expenses

680000	Purchases	
Expenses

681000	QuickBooks Payments Fees	
Expenses

682000	QuickBooks Payments Fees ( 38 )	
Expenses

683000	Reimbursable Expenses	
Expenses

684000	Reimbursements	
Expenses

685000	Rent & Lease	
Expenses

686000	Shop Repairs & Maintenance	
Expenses

687000	Taxes & Licenses	
Expenses

688000	Telephone Expense	
Expenses

689000	Travel	
Expenses

690000	Uncategorized Expense	
Expenses

691100	Uniforms	
Expenses

692100	Utilities	
Expenses

693100	Reconciliation Discrepancies	
Expenses

AR numbers: 
101000	Account Receivable	
Receivable

101300	Account Receivable (PoS)	
Receivable

102000	unused	
Receivable

AP account numbers: 
211000	Account Payable	
Payable

225000	Sales Tax Payable	
Payable

```

**Client Comments:**

<aside>
💬

[Add any notes about financial and accounting rules]

</aside>

---

### 3.3 Compliance & Legal Requirements

**Required Disclosures:**

**EPA lead paint disclosure required:**

- [ ]  Yes
- [x]  No

```
Warranty terms disclosure: repairs is 30day labor on replaced
1 year labor for equipment replacement
Other regulatory disclosures: “Regulated by the Texas Department of Licensing and Regulation, P.O. Box 12157,
Austin, Texas, 78711, 1-800-803-9202, 512-453-6599; website:
www.tdlr.texas.gove/complaints”
License # TACLA84369E
```

**Contract Requirements:**

```
Written contracts required for jobs over: signed for approval
```

**Digital signature acceptable:**

- [x]  Yes
- [ ]  No

```
Contract template location in Odoo: sign app
```

**Client Comments:**

<aside>
💬

[Add any notes about compliance requirements]

</aside>

---

### 3.4 Reporting & Approval Workflows

**Standard Reports Required:**

**Daily Reports:**

- [x]  Revenue summary
- [x]  Calls/appointments booked
- [x]  Jobs completed
- [x]  Outstanding AR
- [x]  Cash flow
- [ ]  Other: ___

**Weekly Reports:**

- [ ]  Sales pipeline status
- [ ]  Technician performance
- [ ]  Customer satisfaction scores
- [ ]  Inventory levels
- [ ]  Marketing ROI
- [ ]  Other: ___

**Monthly Reports:**

- [ ]  P&L statement
- [ ]  Balance sheet
- [ ]  Department performance
- [ ]  Customer retention
- [ ]  Budget vs actual
- [ ]  Other: ___

# 🟢 DAILY EXECUTION KPIs

*(Operational Pulse – keep the body alive)*

### Revenue & Cash

- Revenue collected today
- Revenue billed today
- Cash collected today
- Outstanding AR balance
- AR aging (0-30 / 31-60 / 61-90 / 90+)
- Average ticket size (service / install / commercial)
- Gross margin today
- Labor cost today
- Material cost today
- Net cash flow today

### Calls, Dispatch & Conversion

- Calls received
- Calls answered
- Abandoned calls
- Appointments booked
- Booking rate %
- Show rate %
- Cancel/no-show rate
- Emergency calls
- After-hours calls
- Membership calls

### Field Production

- Jobs completed
- Jobs rescheduled
- Jobs pending parts
- Callbacks created
- Same-day completion %
- First-time fix rate
- Average job duration
- Travel time per tech
- Tech utilization %

### Customer Experience

- CSAT today
- NPS today
- Complaints opened
- Complaints resolved
- Google reviews received

### Inventory & Fleet

- Parts used today
- Van stock variances
- Emergency purchases
- Fuel cost per van
- Open purchase orders

---

# 🟡 WEEKLY PERFORMANCE KPIs

*(Stability & control)*

### Sales & Growth

- Sales pipeline value
- Close rate %
- Install backlog
- Commercial backlog
- Lead source ROI
- Membership growth
- Revenue per lead

### Technician Performance

- Revenue per technician
- Callbacks per technician
- First-time fix %
- Avg ticket per tech
- Hours billed vs hours worked
- Upsell conversion %

### Marketing

- Ad spend vs revenue
- Cost per lead
- Conversion by channel
- Content reach & engagement
- Review velocity

### Inventory & Supply Chain

- Inventory turnover
- Stockout incidents
- Dead stock $
- Vendor lead times

### Financial Control

- Weekly gross margin
- Weekly net margin
- Payroll % of revenue
- Overhead %

---

# 🔵 MONTHLY CONTROL KPIs

*(Profit engine & scalability)*

### Financial Mastery

- P&L by department
- Balance sheet
- Cash reserves
- Debt ratios
- Net operating margin
- Break-even revenue
- Revenue per employee

### Departmental Scorecards

- Service dept margin
- Install dept margin
- Commercial margin
- Marketing ROI
- Dispatch efficiency %
- Inventory shrinkage %

### Customer Lifetime Value

- Repeat customer %
- Membership churn %
- Lifetime value
- Referral rate

### Labor Health

- Overtime %
- Training completion %
- Technician turnover %
- Revenue per labor hour

---

# 🟣 QUARTERLY STRATEGIC KPIs

*(Scale readiness)*

- Market share growth
- Expansion readiness index
- Automation penetration %
- Process compliance %
- AI handled calls %
- SOP adherence %
- Cost to serve per customer
- Profit per square mile (territory density)
- Hiring pipeline health
- Fleet capacity utilization

---

# 🔴 ANNUAL LEGACY KPIs

*(Enterprise valuation)*

- Company valuation
- EBITDA
- Cash runway (months)
- Franchise readiness score
- Leadership bench strength
- Systems independence %
- Owner dependency %
- Community impact metrics (Loveis360)
- Scholarship deployment

---

# 📤 REPORT RECIPIENTS (By Automation)

| Report | Sent To |
| --- | --- |
| Daily Ops Pulse | COO, Ops Manager, Dispatch Lead |
| Daily Cash | CFO, Accounting |
| Weekly Performance | Executive Team |
| Monthly Board | Junior & Linda |
| Quarterly Strategy | Expansion / AI / CFO |
| Annual Legacy | Ownership & Advisors |

**Report Recipients:**

```
Daily reports send to: _______________
Weekly reports send to: _______________
Monthly reports send to: _______________
Board/investor reports: _______________

Daily Ops Pulse	COO, Ops Manager, Dispatch Lead
Daily Cash	CFO, Accounting
Weekly Performance	Executive Team
Monthly Board	Junior & Linda
Quarterly Strategy	Expansion / AI / CFO
Annual Legacy	Ownership & Advisors

everything currenlty to junior and linda. 
junior is operations and executive role
linda is all back office
```

**Report Delivery Method:**

- [x]  Email
- [x]  Odoo dashboard
- [x]  SMS summary
- [ ]  Slack/Teams notification
- [ ]  Other: ___

**Custom Reports:**

```
all to junior and linda for now

# HVAC-R Finest

## Custom Strategic Report System (Growth, Forecasting & Future Projects)
---

# 1️⃣ THE ENTERPRISE COMMAND DASHBOARD (Live View)

**Purpose:**
Real-time company health + growth readiness.

| Tracks                       | Why                                  |
| ---------------------------- | ------------------------------------ |
| Live revenue vs daily target | Know by noon if you’re winning today |
| Cash runway (days)           | Survival & expansion timing          |
| 13-week cashflow graph       | Predict bottlenecks                  |
| Sales pipeline value         | Future income                        |
| Labor capacity vs backlog    | Can we deliver growth                |
| Inventory readiness          | Prevent bottlenecks                  |
| Marketing ROI by channel     | Scale what works                     |
| Automation penetration %     | System maturity                      |

🕒 **Reviewed:**
• Junior: Daily
• Leadership: Weekly

---

# 2️⃣ 13-WEEK CASHFLOW WAR ROOM

**Purpose:**
Predict your future before it hits you.

Tracks:

* Weekly cash inflow forecast
* Weekly payroll
* Weekly AP obligations
* Tax accrual
* Cash gap warnings
* Minimum operating cash
* Emergency buffer alerts

🕒 Reviewed:
• CFO & Junior: Weekly
• AI bot: Daily monitoring

---

# 3️⃣ GROWTH TARGET COMMAND CENTER

**Purpose:**
Control revenue expansion like a machine.

Tracks:

* Annual revenue goal
* Monthly revenue target
* Weekly production target
* Gap to goal
* Required leads per week
* Required tech capacity
* Required inventory growth
* Marketing scale triggers

🕒 Reviewed:
• Weekly leadership
• Monthly strategic planning

---

# 4️⃣ FUTURE PROJECT PIPELINE

**Purpose:**
Predict future construction & commercial dominance.

Tracks:

* Bid pipeline value
* Probability-weighted revenue
* Project start windows
* Labor loading forecasts
* Equipment pre-purchase timing
* Permitting timelines
* Cash impact forecast

🕒 Reviewed:
• Weekly

---

# 5️⃣ BUDGET vs ACTUAL INTELLIGENCE

Tracks:

* Marketing spend vs ROI
* Payroll vs revenue %
* Inventory investment vs turns
* Fleet vs productivity
* AI/Automation spend ROI

🕒 Reviewed:
• Weekly leadership
• Monthly financial close

---

# 6️⃣ TERRITORY DENSITY & MARKET DOMINANCE MAP

Tracks:

* Jobs per zip code
* Profit per square mile
* Drive time per tech
* Market saturation %

🕒 Reviewed:
• Monthly
• Quarterly expansion planning

---

# 7️⃣ SYSTEM MATURITY & FRANCHISE READINESS

Tracks:

* SOP compliance %
* Automation handled volume %
* KPI stability %
* Owner dependency %
* Process documentation %

🕒 Reviewed:
• Quarterly

---

# 8️⃣ LOVEIS360 & LEGACY IMPACT DASHBOARD (hold off on this for now)

Tracks:

* Scholarships funded
* Homes powered
* Sustainability ROI
* Community reach

🕒 Reviewed:
• Quarterly / Annual (hold off on this for now)

# 9️⃣ AI EARLY WARNING SYSTEM (Autonomous Alerts)

Triggers:

* Cash runway below X days
* Backlog exceeds capacity
* Payroll exceeds % target
* Marketing ROI drops
* Callback rates spike
* Inventory stockouts

🕒 Monitoring:
• 24/7 by AI bots
• Humans intervene only when alerted

```

---

**Approval Workflows:**

**Quote Approvals:**

```
Quotes under $20000: Auto-approved
Quotes over $20k to $ 1million: Requires approval from Linda
Quotes over $1million plus: Requires approval from Junior
```

**Purchase Order Approvals:**

```
Parts/supplies under $99: Auto-approved
Parts/supplies $101  to $500: Requires approval from Linda
Parts/supplies over $501: Requires approval from Junior
Capital equipment over $350: Requires approval from Junior
```

**Refund/Credit Approvals:**

```
Refunds under $0: Technician/CSR can approve
Refunds $1  to $99: Requires approval from Anna
Refunds over $100: Requires approval from Linda
```

**Discount Approvals:**

```
Discounts up to 5: Auto-approved
Discounts 6% to 10%: Requires approval from Linda
Discounts over 10.1%: Requires approval from Junior
```

**Financial Authority Hierarchy:**

```
Position/Title | Spending Authority | Approval Required For

Owner / Founder | Unlimited | N/A
CEO (Non-Owner) | Up to $100,000 | Debt, acquisitions, asset sales, new branches, equity changes
General Manager | Up to $50,000 | Any single expense over $50k, long-term contracts, debt, new vendors
Director of Operations | Up to $25,000 | Capital equipment, payroll changes, vendor contracts
Controller / Accounting Manager | Up to $15,000 | Bill pay batches, payroll execution, tax payments
Service Manager | Up to $5,000 | Emergency repairs, overtime, field material purchases
Install / Project Manager | Up to $7,500 | Project materials, subcontractor labor, equipment rentals
Warehouse / Inventory Manager | Up to $3,000 | Stock replenishment, tools, safety supplies
Dispatcher / Office Lead | Up to $1,000 | Office supplies, minor customer accommodations
Field Technician | Up to $500 | Job-specific materials only
```

**Emergency Expense Approvals:**

```
After-hours emergency purchases

Service Manager / On-Call Ops Manager – Up to $3,000 per incident
New Construction Superintendent – Up to $2,500 per incident
Over limit → Owner / CFO approval required

Emergency subcontractor authorization

Project Manager / Director of Operations – Up to $3,500 per incident
New Construction Project Manager – Up to $3,000 per incident
Over limit → Owner / CFO approval required

Rush order approvals

Controller / Purchasing Manager – Up to $5,000 per order
New Construction Procurement Lead – Up to $4,000 per order
Over limit → Owner / CFO approval required
```

**Write-Off Authority:**

```
Bad debt write-offs under $2,500:
Controller / Accounting Manager

Bad debt write-offs over $2,500:
Owner / CFO approval required

Inventory write-offs:
Inventory Control Manager (under $1,500)
Controller approval (over $1,500)
Owner / CFO approval (over $5,000)
```

**Client Comments:**

<aside>
💬

[Add any notes about reporting and approval workflows]

</aside>

---

*Dispatching, scheduling, fleet routing, and inventory*

## SECTION 4: OPS-BRAIN CONFIGURATION

### 4.1 Service Types & Duration

**List all service types with typical duration:**

```
Service Type	Typical Duration	Priority
Emergency No-Cooling / No-Heat	1.5 – 3 hours	High
Gas Leak / Electrical Hazard	1 – 2 hours	Critical / High
Diagnostic Visit	1 – 1.5 hours	High
Same-Day Repair	1 – 3 hours	High
Routine Maintenance / Tune-Up	45 – 90 minutes	Medium
Membership Maintenance	45 – 90 minutes	Medium
Follow-Up / Warranty	30 – 90 minutes	Medium
Thermostat Installation	45 – 90 minutes	Medium
IAQ / Duct Sanitation	2 – 4 hours	Medium
Mini-Split Service	1.5 – 3 hours	Medium
Heat Load / Engineering Visit	2 – 4 hours	Medium
Full System Installation (Residential)	6 – 10 hours	Medium
Full System Installation (Commercial RTU)	1 – 3 days	Medium
Start-Up & Commissioning	2 – 6 hours	Medium
Preventative Maintenance (Commercial)	1 – 4 hours	Medium
Controls / BAS Service	2 – 6 hours	High
Refrigeration Service	1 – 3 hours	High
New Construction Rough-In	1 – 3 days	Medium
New Construction Trim-Out	1 – 2 days	Medium
Final Inspection / Turnover	2 – 6 hours	Medium
Test & Balance (TAB)	4 – 8 hours	Medium
Duct Fabrication & Install	1 – 3 days	Medium
Equipment Change-Out	1 day	Medium
Crane Lift Coordination	4 – 8 hours	High
After-Hours Emergency	1 – 4 hours	Critical
```

**Emergency Service Definition:**

**What qualifies as an emergency?**

- [x]  No heat when temp below F
- [x]  Gas leak/carbon monoxide
- [x]  No AC when temp above ___°F
- [x]  Complete system failure
- [x]  Other: ___
- **No heat when outdoor temperature is below 55°F**
- **No AC when outdoor temperature is above 85°F**
- **Gas leak or carbon monoxide presence or suspected odor**
- **Complete system failure with no airflow**
- **Electrical burning smell or tripping main breaker**
- **Refrigerant leak visible or audible**
- **Flooding or water damage caused by HVAC**
- **Server room | medical | refrigeration equipment failure**
- **New construction critical-path HVAC delay**
- **Multi-unit outage affecting multiple tenants**
- **Senior | infant | medical-dependent occupant without conditioning**
- **Commercial downtime risk exceeding $1,000 per day**
- **Fire system | make-up air | ventilation failure**

**Client Comments:**

<aside>
💬

[Add any notes about service types and emergency definitions]

</aside>

---

### 4.2 Technician Roster & Scheduling

**Provide your complete technician roster:**

```
Name | Phone | Email | Skill Level | Certifications | Service Areas | Schedule
Junior Dikousman	| 972-856-8995 |junior@hvacrfinest.com |Top Tech	|epa 608	|"Home - Desoto, Red Oak, Lancaster and surrounding areas
"	| 8 to 5pm
Bounthon Dikousman	| 945-226-0222	| b.dikousman@yahoo.com	| Senior Tech	| epa 608	"West - Arlington, Grand Prairie, Mansfield and surrounding areas
"	| 8 to 5pm	
Aubry Ritchie	| 910-238-0011	| ritchie74@gmail.com	| Senior Tech	| epa 608	| East - Rockwall, forney, garland, mesquite, and surrounding areas	| 8 to 5pm
```

**Scheduling Rules:**

**Minimum time between appointments:**

**30 minutes**

---

**Travel time calculation method:**

**Live GPS drive-time + 15% buffer**

---

## Skill-Based Time Blocks

| Tech Level | Slot Length | Max Jobs per Day |
| --- | --- | --- |
| **Junior | New Tech** | **4-hour blocks** |
| **Standard | Mid Tech** | **3-hour blocks** |
| **Senior | Lead Tech** | **2-hour blocks** |

**Dispatch Priority Logic:**

```
1. Emergency calls: Immediate dispatch | Preempt all scheduled work | Nearest qualified tech | After-hours routing enabled | Emergency pricing applied
2. Scheduled maintenance: Fifth priority | Routed by geography + skill match | Cannot be displaced unless emergency | Membership customers take precedence
3. Installation projects: forth priority | Protected blocks | Cannot be displaced once started | Weather + material readiness verified before dispatch
4. Callback/follow-ups: 3rd priority | Routed only into open or low-load windows | Must not displace revenue work unless warranty legal requirement
5. Return trips for repairs (Parts-in | Warranty | Incomplete jobs):
2nd priority | Scheduled within 24 hours | Preempts maintenance & non-critical installs | Protects liability & reviews
```

**Technician Assignment:**

**Assign by:**

- [x]  Proximity
- [x]  Skill match
- [x]  Workload balance
- [x]  Customer request

**Can customers request specific technicians:**

- [x]  Yes
- [ ]  No

**Client Comments:**

<aside>
💬

[Add any notes about technician roster and scheduling]

</aside>

---

### 4.3 Fleet & Route Optimization

**Fleet Information:**

```
Vehicle ID | Assigned Technician | GPS Tracking | Stock Capacity
RDM 3029 | Aubry | No | 20 jobs
SZD 4771 | Bounthon | Yes | 20 Jobs
SZD 4769 | Junior | No | 20 Jobs
```

**Route Optimization Priorities:**

```
Closest qualified technician first
(Reduces drive time, fuel cost, and increases same-day close rate)

Cluster jobs by geographic zone
(Creates tight service loops instead of zig-zag routes)

Balance workload vs van stock capacity
(Do not route high-part-demand jobs to low-stock vans)
```

**Client Comments:**

<aside>
💬

[Add any notes about fleet and routing]

</aside>

---

### 4.4 Inventory Management

**Parts Inventory System:**

```
Central warehouse location:
Main Operations Warehouse | Desoto, TX

Truck stock locations:
All active service vans (Mobile Warehouses)
• Van 1 – Junior
• Van 4 – Bounthon
• Van 2 – Aubry
• Future Vans auto-added by OPS Brain
```

**Inventory tracking in Odoo:**

- [x]  Yes
- [ ]  No

**Top 20 Most-Used Parts:**

```
Part Name/Number | Supplier | Reorder Point | Reorder Qty | Lead Time
_____ | _____ | _____ | _____ | _____
_____ | _____ | _____ | _____ | _____
_____ | _____ | _____ | _____ | _____

do not know currently 
```

**Auto-Reorder Rules:**

**Automatic PO generation at reorder point:**

- [ ]  Yes
- [x]  No

```
Approval required for orders over: $_______________
Preferred suppliers by part category: _______________

we currently do not but would like to
```

**Client Comments:**

<aside>
💬

[Add any notes about inventory management]

</aside>

---

## SECTION 5: REVENUE-BRAIN CONFIGURATION

*Marketing, leads, quoting, sales closing*

### 5.1 Lead Sources & Marketing

**Current Lead Sources:**

- [ ]  Google Ads
- [ ]  Facebook/Meta Ads
- [x]  Website organic
- [ ]  Referral program
- [ ]  Direct mail
- [ ]  Radio/TV
- [ ]  Partnerships
- [ ]  Other: ___

**Lead Source Tracking:**

```
How are lead sources currently tracked:  fields in Odoo unknown
CRM: odoo
would like to do all
```

**Active Marketing Campaigns:**

```
Campaign Name | Target Audience | Offer/Message | Desired Automation
_____ | _____ | _____ | _____
_____ | _____ | _____ | _____

none at this time

would like to
```

**Client Comments:**

<aside>
💬

[Add any notes about lead sources and marketing]

</aside>

---

### 5.2 Lead Qualification & Routing

**Lead Qualification Criteria:**

```
Hot Lead:

• No cooling | No heating | Emergency-qualified
• Ready to schedule today
• Budget approved or decision maker on phone
• Install or repair within 72 hours
• Routed immediately to senior tech or sales

Warm Lead:

• System working but uncomfortable
• Interested in repair | replacement | IAQ
• Scheduling within 3–14 days
• Routed into standard production windows
• Enters follow-up automation

Cold Lead:

• Price shopping only
• No urgency
• 15+ days out
• Sent to nurture | marketing drip | review building
```

**Lead Routing Rules:**

```
Residential leads: Assign to Bounthon and Aubry
Commercial leads: Assign to Junior and Bounthon
High-value leads (over $10k): Assign to Junior
Service area outside primary territory: _______________
```

**Lead Response Time Goals:**

```
Hot leads: 24hr
Warm leads: 72hr
Cold leads: 1 week
```

**Client Comments:**

<aside>
💬

[Add any notes about lead qualification and routing]

</aside>

---

### 5.3 Quoting & Proposal Process

**Quote Generation:**

```
Quote template location in Odoo: _______________
Quote valid for: _____ days

Currently we do not have any templates
```

**Quote approval required:**

- [x]  Yes (over $85)
- [ ]  No

**Quote Components:**

```
Equipment cost markup: _____%
Labor cost calculation: _______________
Permit/disposal fees: _______________
Financing options presentation: _______________
```

**Proposal Delivery:**

- [x]  Email PDF
- [x]  SMS link
- [x]  Customer portal
- [x]  In-person presentation

**Client Comments:**

<aside>
💬

[Add any notes about quoting and proposals]

</aside>

---

### 5.4 Sales Pipeline & Follow-up

**Sales Pipeline Stages in Odoo:**

```
Pending Schedule
(Lead qualified | Waiting to be booked | Entry point for all new calls, web forms, property management tickets)

Job Scheduled
(Appointment booked | Technician assigned | Production slot reserved)

On The Way
(Technician en route | Live ETA | Customer notified)

On-Site
(Technician working | Diagnostic | Repair | Install | Quote generation in progress)

On Hold | Must Reschedule
(Parts needed | Customer unavailable | Weather delays | Return trip pending)

Paused | Return Same Day
(Temporary same-day pause | Waiting on access | Waiting on parts | Same-day continuation)

Pending Quote Approval
(Quote sent | Financing presented | Follow-up automation running)

Quote Approved | Waiting for Parts
(Sale won | Parts procurement | Install | Return trip staged)

Quote Approved | Hold
(Sale approved but delayed | HOA | Permits | Customer scheduling)

Completed
(Job closed | Invoice finalized | Review request sent)

Warranty | Review and Paid
(Warranty service | Payment confirmed | Review captured)

Invoices Not Paid
(AR follow-up | Collections | Payment resolution)

Closed
(Final financial close | Job archived)
```

**Automated Follow-up Sequences:**

```csharp
Quote sent →
Immediate thank-you text + financing options + scheduling link

No response after 2 days →
Auto reminder text + email + call task created for CSR

Customer says “maybe” →
Enter 7-day nurture sequence
(education email + testimonial + financing reminder)

Lost deal →
Enter 90-day reactivation drip
(seasonal promos | rebate alerts | system health reminders)
```

**Conversion Triggers:**

**What actions move a lead to customer status:**

- [ ]  Quote accepted
- [ ]  Deposit received
- [x]  Work order created
- [ ]  Other: ___

**Client Comments:**

<aside>
💬

[Add any notes about sales pipeline]

</aside>

---

## SECTION 6: PEOPLE-BRAIN CONFIGURATION

*Hiring, onboarding, training, performance, payroll*

### 6.1 Recruitment & Hiring

**Current Hiring Process:**

```
Job posting platforms:
Indeed | ZipRecruiter | Facebook Jobs | HVAC-Talk | Trade school partnerships | Referral program

Application review process:
AI pre-screen → License & EPA verification → Experience scoring → Culture-fit questionnaire → Human review

Interview stages:

Phone screen

Technical interview

Ride-along working interview

Final leadership interview

Background check requirements:
Criminal | Driving record (MVR) | License verification | Drug screen | Reference checks
```

**Required Documentation:**

- [x]  I-9 verification
- [x]  Background check
- [x]  Drug screening
- [x]  Driving record (MVR)
- [x]  License verification
- [x]  Other: EPA Cert and TDLR

**Hiring Approval Workflow:**

```
Who approves new hires:
Junior | Linda | Bounthon (Joint approval required)

Offer letter template location:
Odoo Sign App – HR Template Library
```

**Client Comments:**

<aside>
💬

[Add any notes about recruitment and hiring]

</aside>

---

### 6.2 Onboarding & Training

**Onboarding Checklist:**

**What must be completed before day 1?**

- [ ]  
    
    ---
    

## ☐ HR & Identity Verification (Legal Compliance)

- W-4
- I-9
- Driver’s License
- Social Security Card
- TDLR License (if applicable)
- Background check
- Drug screening
- Vehicle Ops Agreement (if driving)

---

## ☐ Employment Agreements (Odoo Sign – MUST be signed)

- Offer Letter
- Employee Handbook Acknowledgment
- NDAs & Conduct Agreements
- Pay Structure & Commission Plans

---

## ☐ Payroll & Banking Activation

- Added to payroll system
- Pay method confirmed
- Tax status verified

---

## ☐ Minimum System Access (Only what’s required to work)

- Company email created
- Odoo login activated
- Property Management login(s) activated
- [ ]  
    
    ---
    
- [ ]  
    
    ---
    

**Training Program:**

```
Initial training duration:
14 days structured onboarding + 30-60-90 ramp program

Training topics | modules:

• Core Values & Core Philosophy
• Customer Promises & Employee Promises
• ServiceTitan operations & mobile workflows
• SMS Assist | Lessen portal & compliance
• Dispatch communication & call routing logic
• Warehouse & van stock organization
• Respect for the Home & Image Standards
• Upfront Pricing & option presentation
• Financing presentation (Greensky)
• Full inspection & evaluation process
• Repair & replacement option building
• Club membership education & enrollment
• Safety & PPE compliance
• Time tracking & event clocking
• Documentation standards
• Shadowing in Service | Install | Sales | Dispatch | Warehouse

Certification requirements:

• EPA 608 (Required)
• TDLR (If applicable)
• OSHA 10 (Recommended within 90 days)
• Valid Driver’s License (Driving positions)

Ongoing education requirements:

• Weekly Friday training meetings
• Quarterly skills refresh & safety reviews
• Annual EPA & TDLR compliance refresh
• New product & code update training
• Ongoing Odoo & Property Management updates
• Leadership track training for Senior Techs
```

**Training Tracking:**

**Training completion tracked in Odoo:**

- [x]  Yes
- [ ]  No

**Certification expiration alerts:**

- [x]  Yes
- [ ]  No

**Client Comments:**

<aside>
💬

[Add any notes about onboarding and training]

</aside>

---

### 6.3 Payroll Configuration

**Pay Periods:**

- [ ]  Weekly
- [x]  Bi-weekly
- [ ]  Semi-monthly
- [ ]  Monthly

**Technician Pay Structure:**

- [ ]  Hourly: $_/hour
- [ ]  Salary: $_/year
- [x]  Commission: 15% of sales for repairs and 5% on sale of installs
- [x]  Flat rate per job
- [x]  Hybrid: on bigger projects, commission techs get day rates

**Commission Rules:**

**Paid on:**

- [x]  Invoice
- [x]  Collection
- [ ]  Job completion

```
Commission tiers: _______________
Spiffs/bonuses: _______________
```

**Overtime Rules:**

```
OT threshold: _____ hours/week
OT rate: _____x regular rate
Double-time threshold: _____ hours
```

**Payroll Automation:**

**Time tracking integrated with Odoo:**

- [ ]  Yes
- [ ]  No

```
Time tracking method: _______________
Approval workflow before payroll run: _______________
Payroll processing system: _______________
```

**Client Comments:**

<aside>
💬

[Add any notes about payroll configuration]

</aside>

---

## SECTION 7: VOICE AGENT CONFIGURATION (Vapi Platform)

**Why We Need This Information:**

Your AI voice agent will be built on **Vapi**, a leading AI voice platform that handles inbound and outbound calls 24/7. Vapi will answer your business phone, qualify leads, book appointments, and transfer calls to your team when needed. You'll need to create your own Vapi account to manage credits and usage - we'll help you set this up. Additionally, you'll need phone number(s) which can be provided through **Twilio** or ported from your existing provider. We need to understand your current phone system, call handling preferences, and brand voice to configure the voice agent properly.

---

**Current Phone System:**

### 7.1 Platform Setup (Vapi & Twilio)

**Vapi Account (Required):**

**Do you already have a Vapi account?**

- [ ]  Yes - Provide account details below
- [ ]  No - We'll help you create one

```
Vapi Account Email (if existing): _______________
Vapi Organization ID (if existing): _______________
```

**Important:** You will need to add credits to your Vapi account. Typical costs are **$0.08-0.15 per minute** of call time. We'll help you estimate monthly usage based on your call volume.

```
Estimated monthly call volume: _____ calls
Average call duration: _____ minutes
```

---

**Phone Number Strategy:**

**Current Business Phone Number:**

```
[The main number customers currently call]
```

**How do you want to handle phone numbers?**

- [ ]  Port existing number to Twilio (recommended - full AI control)
- [ ]  Get new Twilio number and forward existing to it
- [ ]  Keep existing provider and forward calls to Vapi number
- [ ]  Already have Twilio account - use existing

**If you have an existing Twilio account:**

```
Twilio Account SID: _______________
Twilio Auth Token: _______________
Existing phone numbers: _______________
```

**If porting or getting a new number:**

```
Preferred area code: _______________
Port existing number: Yes/No
Current phone provider (if porting): _______________
Account number (for porting): _______________
Authorized person for port: _______________
```

**Additional phone numbers needed:**

- [ ]  Sales line
- [ ]  Service line
- [ ]  After-hours line
- [ ]  Other: ___

<aside>
💬

[Add any notes about platform setup or phone numbers]

</aside>

---

### 7.2 Current Phone System Details

```
Provider: _______________
Account admin contact: _______________
Number of lines: _______________
```

**Primary Business Phone Number:**

```
[The main number customers call]
```

**Department/Extension Numbers:**

```
Service/Dispatch: _______________
Sales: _______________
Billing: _______________
After-hours: _______________
```

**Client Comments:**

<aside>
💬

[Add any notes about phone system]

</aside>

**Business Hours Call Flow:**

**AI answers:**

- [ ]  Immediately
- [ ]  After ___ rings

```
If AI cannot handle: Transfer to _______________
```

**If no answer:**

- [ ]  Voicemail
- [ ]  Callback requested
- [ ]  SMS sent

**After-Hours Call Flow:**

- [ ]  AI handles all calls
- [ ]  Emergency calls transfer to: ___
- [ ]  Non-emergency: Schedule callback for next business day

**Call Types AI Should Handle:**

- [ ]  New service requests
- [ ]  Appointment scheduling
- [ ]  Appointment changes/cancellations
- [ ]  Service status updates
- [ ]  General information (hours, service area, etc.)
- [ ]  Payment questions
- [ ]  Quote requests
- [ ]  Other: ___

**Call Types Requiring Human:**

- [ ]  Complaints/escalations
- [ ]  Complex technical questions
- [ ]  Warranty claims
- [ ]  Large commercial quotes
- [ ]  Other: ___

**Client Comments:**

<aside>
💬

[Add any notes about call handling]

</aside>

**Company Greeting:**

```
How should AI answer the phone?
[Example: "Thank you for calling HAES HVAC, this is Alex, how can I help you today?"]
```

**Brand Voice:**

**Tone:**

- [ ]  Professional
- [ ]  Friendly
- [ ]  Technical
- [ ]  Other: ___

**Formality:**

- [ ]  Formal
- [ ]  Casual
- [ ]  Balanced

**Pacing:**

- [ ]  Fast
- [ ]  Moderate
- [ ]  Slow

**Prohibited Words/Phrases:**

```
What should AI never say?
- _______________
- _______________
```

**Preferred Terminology:**

```
Instead of "cheap" say: _______________
Instead of "free" say: _______________
Equipment terms: _______________
```

**Client Comments:**

<aside>
💬

[Add any notes about voice and brand guidelines]

</aside>

---

### 7.5 Hosting & Infrastructure ([Fly.io](http://Fly.io))

**Why We Need This Information:**

Your AI system needs reliable hosting for backend APIs, webhooks, and optional frontend dashboard. We recommend [**Fly.io**](http://Fly.io) - a modern, cost-effective hosting platform perfect for small businesses. [Fly.io](http://Fly.io) provides custom domain support, automatic SSL certificates, global edge deployment, and easy scaling. You'll create your own [Fly.io](http://Fly.io) account (just like Vapi and Twilio) to maintain full ownership and control.

---

[**Fly.io](http://Fly.io) Account Setup:**

**Do you already have a [Fly.io](http://Fly.io) account?**

- [ ]  Yes - Provide account details below
- [ ]  No - We'll help you create one

```
[Fly.io](http://Fly.io) Account Email (if existing): _______________
[Fly.io](http://Fly.io) Organization Name (if existing): _______________
```

**Important:** [Fly.io](http://Fly.io) offers a generous free tier, but for production use, expect **$10-25/month** in hosting costs depending on traffic and resource needs.

---

**Custom Domain Requirements:**

**Do you want to use a custom domain for your dashboard/API?**

- [ ]  Yes - I have a domain
- [ ]  Yes - I need to purchase a domain
- [ ]  No - Use default [Fly.io](http://Fly.io) subdomain ([yourapp.fly.dev](http://yourapp.fly.dev))

**If using custom domain:**

```
Domain name: _______________ (e.g., [haeshvac.com](http://haeshvac.com))
Domain registrar: _______________ (GoDaddy, Namecheap, etc.)
Domain admin access: Yes/No
```

**Preferred subdomains:**

```
Main website/dashboard: _______________ (e.g., [www.haeshvac.com](http://www.haeshvac.com))
API endpoint: _______________ (e.g., [api.haeshvac.com](http://api.haeshvac.com))
Other subdomains needed: _______________
```

---

**What We'll Host on [Fly.io](http://Fly.io):**

**Backend Services:**

- [ ]  Vapi webhook handlers (FastAPI)
- [ ]  Odoo API integration layer
- [ ]  Command Engine (HAEL)
- [ ]  AI Brain microservices
- [ ]  Database (if needed)

**Frontend Services (Optional):**

- [ ]  KPI Dashboard
- [ ]  Admin panel
- [ ]  Customer portal
- [ ]  Other: ___

**Resource Requirements:**

```
Expected monthly traffic: _______________
Peak concurrent users: _______________
Data storage needs: _______________
```

---

**Deployment & Management Preferences:**

**Who will handle deployments?**

- [ ]  Innova team handles all deployments (recommended initially)
- [ ]  Train our team to deploy independently
- [ ]  Hybrid approach

**Deployment notifications:**

```
Send deployment notifications to: _______________
Preferred notification method: Email/Slack/SMS
```

**Backup requirements:**

- [ ]  Daily automated backups
- [ ]  Weekly automated backups
- [ ]  Manual backups only

```
Backup retention period: _____ days
```

---

**SSL Certificate & Security:**

**SSL Certificate:** [Fly.io](http://Fly.io) provides **free automatic SSL certificates** via Let's Encrypt for all custom domains ✅

**Additional security requirements:**

- [ ]  DDoS protection
- [ ]  WAF (Web Application Firewall)
- [ ]  IP whitelisting
- [ ]  VPN access requirement
- [ ]  Other: ___

---

**Estimated Monthly Infrastructure Costs:**

```
[Fly.io](http://Fly.io) hosting:                  $10-25/month
Database (if needed):            $0-15/month
CDN/static assets:              $0-5/month
Backup storage:                 $0-5/month
────────────────────────────────────────────
Total Infrastructure:           ~$10-50/month

(This is SEPARATE from Vapi and Twilio costs)
```

**Combined Monthly Platform Costs Summary:**

```
Vapi (voice agent usage):        $200-500/month (varies by call volume)
Twilio (phone numbers):          $2-10/month
[Fly.io](http://Fly.io) (hosting):                $10-25/month
Odoo (if cloud hosted):          $25-50/month per user
────────────────────────────────────────────
ESTIMATED TOTAL:                 $237-585/month
```

<aside>
💬

[Add any notes about hosting, domains, or infrastructure requirements]

</aside>

---

**Website Platform:**

**Why We Need This Information:**

Your website chat assistant provides 24/7 customer engagement on your website. The chat widget can qualify leads, answer common questions, book appointments, and seamlessly hand off to human agents when needed. The chat assistant can be built using various platforms, depending on your needs and existing website setup. We need to understand your website platform, chat behavior preferences, and lead conversion goals to configure the chat assistant properly.

### 8.1 Website Integration

- [ ]  WordPress
- [ ]  Odoo Website Builder
- [ ]  Custom
- [ ]  Other: ___

**Website URL:**

```
[Your website address]
```

**Admin Access:**

```
Username/Email: _______________
Where to place chat widget: _______________
```

**Client Comments:**

<aside>
💬

[Add any notes about website integration]

</aside>

---

### 8.2 Chat Bot Behavior

**Greeting Message:**

```
[What should appear when chat opens?]
```

**Pre-Chat Qualification:**

**Name:**

- [ ]  Required
- [ ]  Optional

**Email:**

- [ ]  Required
- [ ]  Optional

**Phone:**

- [ ]  Required
- [ ]  Optional

**Service needed:**

- [ ]  Required
- [ ]  Optional

**Chat to Lead Conversion:**

```
Create lead in Odoo after: _______________
Lead assignment rule: _______________
Email notification to: _______________
```

**Live Handoff:**

**Chat can transfer to human:**

- [ ]  Yes
- [ ]  No

```
Transfer to: _______________
Hours for live transfer: _______________
```

**Client Comments:**

<aside>
💬

[Add any notes about chat bot behavior]

</aside>

---

## SECTION 9: COMMAND ENGINE (HAEL) CONFIGURATION

### 9.2 Command Routing Rules

**Decision Tree - Which Brain Processes What:**

```
Customer Input | Intent | Routed To Brain | Action
"My AC broke" | Emergency repair | OPS-BRAIN | Schedule emergency call
"How much for new system" | Quote request | REVENUE-BRAIN | Gather details, create lead
"When is my payment due" | Billing inquiry | CORE-BRAIN | Lookup invoice, provide info
_____ | _____ | _____ | _____
```

**Client Comments:**

<aside>
💬

[Add any notes about command routing]

</aside>

---

### 9.3 Data Extraction Requirements

**For Service Requests:**

- [ ]  Name
- [ ]  Phone
- [ ]  Email
- [ ]  Address
- [ ]  Problem description
- [ ]  System type
- [ ]  Urgency level
- [ ]  Preferred appointment time
- [ ]  Other: ___

**For Quote Requests:**

- [ ]  Property type
- [ ]  Square footage
- [ ]  Current system age
- [ ]  Budget range
- [ ]  Timeline
- [ ]  Other: ___

**Client Comments:**

<aside>
💬

[Add any notes about data extraction]

</aside>

---

## FINAL CHECKLIST

**Before submitting this form, confirm you have:**

- [ ]  Provided Odoo access credentials
- [ ]  Listed all service types and pricing
- [ ]  Defined technician roster and scheduling rules
- [ ]  Specified inventory and parts management details
- [ ]  Outlined sales and marketing automation needs
- [ ]  Configured payroll and HR workflows
- [ ]  Set voice and chat bot parameters
- [ ]  Defined KPI metrics and alert rules
- [ ]  Identified systems for integration/migration
- [ ]  Specified testing and training requirements
- [ ]  Provided all stakeholder contact information

---

---

*This comprehensive discovery ensures we build all four AI brains (CORE, OPS, REVENUE, PEOPLE) with accurate business logic integrated seamlessly with your Odoo ERP system.*