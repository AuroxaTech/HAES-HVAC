# Knowledge Base Assignment for Vapi Assistants

**Last Updated:** 2025-01-23

This document specifies which Knowledge Base files should be attached to each Vapi assistant.

---

## 📚 Available Knowledge Base Files

| File | Size | Purpose | Target Audience |
|------|------|---------|----------------|
| `customer_faq.txt` | 8.1KB | Customer FAQ, company info, services, pricing | **Customer-facing** |
| `policies.txt` | 6.1KB | Policies, disclosures, warranties, terms | **Customer-facing** |
| `ops_intake_and_call_policy.txt` | 13KB | Call intake procedures, tool usage, emergency rules | **Internal OPS** |

---

## 🤖 Riley Customer - Inbound

**Assistant ID:** `f639ba5f-7c38-4949-9479-ec2a40428d76`  
**Phone:** `+1-972-597-1644`  
**Purpose:** Customer service & support

### Recommended KB Files (2):

1. ✅ **`customer_faq.txt`** - **REQUIRED**
   - Company information
   - Service areas
   - Business hours
   - Service offerings
   - Pricing information
   - Maintenance plans
   - Financing options

2. ✅ **`policies.txt`** - **REQUIRED**
   - Licensing & certifications
   - Service policies (appointments, cancellations)
   - Emergency service policy
   - Pricing policies
   - Warranty terms
   - Payment terms
   - Disclosures

### Why These Files?
- Both files contain customer-facing information
- Helps AI answer common customer questions without calling tools
- Provides context for policies, warranties, and service terms
- Reduces tool calls for informational queries

---

## 🏢 Riley OPS

**Assistant ID:** `fd35b574-1a9c-4052-99d8-a820e0ebabf7`  
**Phone:** `+1-855-768-3265`  
**Purpose:** Internal operations support

### Recommended KB Files (1-2):

1. ✅ **`ops_intake_and_call_policy.txt`** - **REQUIRED**
   - Call intake procedures
   - Tool usage guidelines
   - Emergency qualification rules
   - Field collection order
   - Validation procedures
   - Prohibited phrases
   - Internal operational guidance

2. ⚠️ **`policies.txt`** - **OPTIONAL**
   - Can be useful for reference on policies
   - Less critical since OPS assistant focuses on internal operations
   - May help with policy questions from employees

### Why These Files?
- `ops_intake_and_call_policy.txt` is essential for internal operations
- Provides guidance on how to handle calls, collect information, and use tools
- Contains emergency rules and safety procedures
- Helps maintain consistency in call handling

---

## 📋 Summary

| Assistant | Required KB Files | Optional KB Files | Total |
|-----------|------------------|-------------------|-------|
| **Riley Customer - Inbound** | `customer_faq.txt`<br>`policies.txt` | None | 2 |
| **Riley OPS** | `ops_intake_and_call_policy.txt` | `policies.txt` | 1-2 |

---

## ✅ Confirmation

**Yes, the current KB files in `doc/vapi/kb/` are appropriate for the two assistants:**

- ✅ **Riley Customer - Inbound** needs: `customer_faq.txt` + `policies.txt`
- ✅ **Riley OPS** needs: `ops_intake_and_call_policy.txt` (+ optionally `policies.txt`)

All three KB files are correctly organized and ready to be uploaded to Vapi Knowledge Base.

---

## 🚀 Next Steps

1. **Create Knowledge Bases in Vapi:**
   - Create "Customer KB" with `customer_faq.txt` + `policies.txt`
   - Create "OPS KB" with `ops_intake_and_call_policy.txt` (+ optionally `policies.txt`)

2. **Attach to Assistants:**
   - Attach "Customer KB" to Riley Customer - Inbound
   - Attach "OPS KB" to Riley OPS

3. **Verify:**
   - Test that assistants can reference KB content
   - Ensure tools still work correctly (KB doesn't replace tools, only supplements)

---

*Note: KB is optional but recommended. The system prompts already contain most information, but KB provides searchable context for better AI responses.*
