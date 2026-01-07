# HAES Simple Vendor Guide
## AI-Powered HVAC Business Automation System

**Duration:** 7 Weeks

**Objective:** Build four specialized AI modules that automate dispatch, sales, marketing, finance, inventory, HR, and compliance through voice/chat interfaces integrated with Odoo.

---

## What We're Building

Four AI "brains" that process customer interactions and execute business operations automatically:

- **CORE-BRAIN:** Pricing, accounting, compliance, reporting
- **OPS-BRAIN:** Dispatch, scheduling, fleet routing, inventory
- **REVENUE-BRAIN:** Marketing, leads, quoting, sales closing
- **PEOPLE-BRAIN:** Hiring, onboarding, training, payroll, KPIs

**Flow:** Customer calls/chats → AI converts to commands → correct brain processes → Odoo updates → KPIs track automatically.

---

## System Components

### Customer Interaction

- **Voice IVR Bot:** Handles all incoming calls 24/7
- **Website Chat Bot:** Handles all website visitor inquiries

### Processing Engine

- **Command Engine (HAEL):** Converts conversations into structured business commands
- **AI Brain Microservices:** Four specialized modules processing different business functions
- **Odoo API Integration Layer:** Connects all AI modules to Odoo in real-time

### Analytics

- **KPI Dashboard:** Real-time business performance tracking across all operations

---

## Core Workflows Automated

- **Customer Calls:** Booking, scheduling, service updates, quote requests
- **Dispatching:** Technician assignment, routing, parts allocation
- **Sales:** Lead qualification, quoting, financing options, follow-ups
- **Invoicing:** Auto-generation after service completion
- **Inventory:** Parts ordering at reorder points
- **Payroll:** Auto-processing per defined rules
- **Reporting:** Automated KPI updates and alerts

---

## 7-Week Timeline

### Weeks 1-2: Foundation Setup

Voice platform configuration, chat bot deployment, Odoo API integration, development environment setup.

### Weeks 3-4: AI Brain Development

Build four intelligence modules, command engine, populate knowledge bases with business rules and pricing.

### Weeks 5-6: Workflow Integration

Connect all workflows end-to-end (calls → dispatch → invoicing, leads → quotes → sales, parts ordering, payroll processing).

### Week 7: Testing & QA

Comprehensive testing across all scenarios, performance optimization, bug fixes, security validation.

---

## Requirements From HAES

- Odoo access with API credentials
- Customer/vendor/employee databases
- Service catalog and pricing structures
- Business rules and operational policies
- Phone number preference
- Project point of contact

---

## Success Definition

### At Launch

- Calls book automatically without human intervention
- Invoices auto-send after service completion
- Payroll auto-runs per schedule
- Parts auto-order at reorder points
- KPIs auto-optimize based on performance data

### Efficiency Goal

Modular microservices architecture, reuse Odoo native modules, centralize logic in four brains to reduce cost, simplify maintenance, improve reliability.
