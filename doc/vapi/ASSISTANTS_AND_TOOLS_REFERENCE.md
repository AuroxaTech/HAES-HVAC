# Assistants and Tools Reference

This document is the quick reference for Vapi assistants, phone numbers, and attached tools.

## Riley Customer - Inbound

- **Assistant ID**: `f639ba5f-7c38-4949-9479-ec2a40428d76`
- **Phone Number**: `+1-972-597-1644`
- **Source**: 8x8 forwarded line
- **Tool Scope**: customer-facing
- **Total Tools**: 18

### Customer-Facing Tools

#### Appointments (5)
- `schedule_appointment`
- `reschedule_appointment`
- `cancel_appointment`
- `check_appointment_status`
- `check_availability`

#### Leads and Quotes (4)
- `create_service_request`
- `request_quote`
- `check_lead_status`
- `request_membership_enrollment`

#### Billing (3)
- `billing_inquiry`
- `invoice_request`
- `payment_terms_inquiry`

#### Information (5)
- `get_pricing`
- `get_maintenance_plans`
- `get_service_area_info`
- `check_business_hours`
- `send_notification`

#### Complaints (1)
- `create_complaint`

## Riley OPS

- **Assistant ID**: `fd35b574-1a9c-4052-99d8-a820e0ebabf7`
- **Phone Number**: `+1-855-768-3265`
- **Source**: Twilio
- **Tool Scope**: internal operations
- **Total Tools**: 6

### Internal OPS Tools

#### Technician (1)
- `ivr_close_sale`

#### HR (3)
- `payroll_inquiry`
- `onboarding_inquiry`
- `hiring_inquiry`

#### Operations (2)
- `inventory_inquiry`
- `purchase_request`

## Notes

- Server URL endpoint for tool calls: `https://haes-hvac.fly.dev/vapi/server`
- New dual-channel notification tool: `send_notification` (sends SMS and email in one call)
