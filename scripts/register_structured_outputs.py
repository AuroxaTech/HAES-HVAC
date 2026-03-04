"""
Register VAPI Structured Outputs for Post-Call Processing

Creates 4 structured outputs and attaches them to the customer inbound assistant.
Run once to configure, then structured outputs persist in VAPI.

Usage:
    python scripts/register_structured_outputs.py
"""

import os
import sys
import json
import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings

settings = get_settings()
VAPI_API_KEY = settings.VAPI_API_KEY
ASSISTANT_ID = "f639ba5f-7c38-4949-9479-ec2a40428d76"  # Riley Customer - Inbound

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

# ── Structured Output Schemas ────────────────────────────────────────

OUTPUTS = [
    # ── Output 1: Customer Profile ────────────────────────────────────
    {
        "name": "Customer Profile",
        "type": "ai",
        "description": (
            "Extract the customer's contact details and property information from this HVAC service call. "
            "This is for HVAC-R Finest, a residential and commercial HVAC company in the Dallas-Fort Worth area. "
            "The assistant's name is Riley. Callers are typically homeowners, tenants, property managers, or businesses.\n\n"
            "EXTRACTION RULES:\n"
            "- phone is REQUIRED — extract the caller's phone number. If not explicitly stated, use the caller ID number.\n"
            "- Extract firstName and lastName separately. If only a first name is given, leave lastName null.\n"
            "- address should be the full service address (street, city, state, zip) where the HVAC work is needed, not a mailing address.\n"
            "- zipCode should be extracted separately even if it's part of the address.\n"
            "- propertyType: determine from context — 'residential_owner' if they own the home, 'residential_renter' if they rent/lease, "
            "'commercial' for businesses, 'property_management' if calling on behalf of a managed property.\n"
            "- managementCompany: only populate if the caller mentions a property management company (e.g., Invitation Homes, Lessen, Pathlight, Tricon).\n"
            "- callerType: 'homeowner' for someone who owns their home, 'tenant' for renters, 'property_management' for PM companies, 'business' for commercial callers.\n"
            "- confirmedPartnerId: only populate if the assistant called lookup_customer_profile and received an Odoo partner ID in the tool result.\n"
            "- contactOnSite: who should the technician ask for when they arrive? Only populate if different from the caller.\n"
            "- accessInstructions: gate codes, parking instructions, 'use side door', 'call when arriving', etc.\n"
            "- leadSource: how did they hear about HVAC-R Finest? Only populate if explicitly mentioned (e.g., 'Google', 'referral from neighbor', 'Yelp', 'repeat customer').\n"
            "- Leave fields null if the information was not discussed or is unknown."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "firstName": {
                    "type": "string",
                    "description": "Customer's first name as stated during the call",
                },
                "lastName": {
                    "type": "string",
                    "description": "Customer's last name. Null if only first name was provided.",
                },
                "phone": {
                    "type": "string",
                    "description": "Customer's phone number in any format (e.g., '972-555-1234', '+19725551234'). Use caller ID if not explicitly stated.",
                },
                "email": {
                    "type": "string",
                    "description": "Customer's email address for sending appointment confirmations and invoices. Null if not provided.",
                },
                "address": {
                    "type": "string",
                    "description": "Full service address where the HVAC work is needed (street, city, state, zip). This is the property address, not mailing address.",
                },
                "zipCode": {
                    "type": "string",
                    "description": "5-digit ZIP code of the service address. Extract separately even if included in the full address.",
                },
                "propertyType": {
                    "type": "string",
                    "enum": ["residential_owner", "residential_renter", "commercial", "property_management"],
                    "description": (
                        "Type of property needing service. "
                        "'residential_owner' = homeowner, 'residential_renter' = tenant/renter, "
                        "'commercial' = business property, 'property_management' = managed property (tenant or PM calling)."
                    ),
                },
                "managementCompany": {
                    "type": "string",
                    "description": "Name of the property management company if the caller is a tenant or PM representative (e.g., 'Invitation Homes', 'Lessen', 'Pathlight'). Null if not applicable.",
                },
                "callerType": {
                    "type": "string",
                    "enum": ["homeowner", "tenant", "property_management", "business"],
                    "description": (
                        "Who is calling. 'homeowner' = owns the property, 'tenant' = rents/leases, "
                        "'property_management' = calling on behalf of managed properties, 'business' = commercial customer."
                    ),
                },
                "confirmedPartnerId": {
                    "type": "integer",
                    "description": "Odoo CRM partner ID. Only populate if the assistant called lookup_customer_profile and received a numeric partner_id in the tool response. Do not guess or fabricate.",
                },
                "contactOnSite": {
                    "type": "string",
                    "description": "Name of the person the technician should ask for at the property, if different from the caller (e.g., 'Ask for Maria at the front desk').",
                },
                "accessInstructions": {
                    "type": "string",
                    "description": "Special access instructions for the technician: gate codes, parking details, which door to use, 'call when 10 minutes away', apartment/unit number, etc.",
                },
                "leadSource": {
                    "type": "string",
                    "description": "How the customer heard about HVAC-R Finest. Only populate if explicitly mentioned (e.g., 'Google search', 'neighbor referral', 'Yelp', 'drove past your van', 'repeat customer'). Do not guess.",
                },
            },
            "required": ["phone"],
        },
    },
    # ── Output 2: Appointment Action ──────────────────────────────────
    {
        "name": "Appointment Action",
        "type": "ai",
        "description": (
            "Extract appointment booking, rescheduling, or cancellation details from this HVAC service call. "
            "The assistant (Riley) checks availability using the check_availability tool which returns 2 time slots as 4-hour windows "
            "(e.g., 'Monday, January 27, 8 AM to 12 PM'). The customer then picks a slot.\n\n"
            "IMPORTANT — When action is 'book': you MUST set chosenSlotTechnicianId to the technician_id of the slot the customer chose. "
            "From the check_availability tool result: next_available_slots[0] = first option offered, next_available_slots[1] = second option. "
            "If the customer said 'first one' or chose the earlier time, use next_available_slots[0].technician_id; if they chose the second, use next_available_slots[1].technician_id. "
            "This assigns the FSM job to the correct technician. Do not omit chosenSlotTechnicianId when action is 'book'.\n\n"
            "EXTRACTION RULES:\n"
            "- action is REQUIRED. Set to 'book' if the customer confirmed a new appointment, 'reschedule' if they moved an existing one, "
            "'cancel' if they cancelled, 'none' if no appointment action was taken or confirmed.\n"
            "- ONLY set action to 'book', 'reschedule', or 'cancel' if the customer VERBALLY CONFIRMED the action. "
            "If they just discussed scheduling but didn't commit, set action='none'.\n"
            "- chosenSlotStart and chosenSlotEnd: extract the ISO 8601 datetime values from the check_availability tool result "
            "that correspond to the slot the customer chose. These are in the tool response's next_available_slots array "
            "(fields: 'start' and 'end'). Do NOT extract the spoken time — extract the raw ISO datetime from the tool result.\n"
            "- chosenSlotTechnicianId: REQUIRED when action is 'book'. Extract the technician_id from the same slot the customer chose "
            "in the check_availability tool result. It is in next_available_slots[].technician_id (or next_available_slot.technician_id "
            "if they chose the first slot). This is the ID of the technician whose time window the customer selected; the FSM job must be "
            "assigned to this technician. Example: if customer picked the first option, use next_available_slots[0].technician_id.\n"
            "- appointmentWindow: the 4-hour window as spoken (e.g., '8 AM to 12 PM', '12 PM to 4 PM').\n"
            "- serviceType: what HVAC service is needed (e.g., 'AC repair', 'heating not working', 'maintenance tune-up', 'thermostat issue').\n"
            "- problemDescription: detailed description of the HVAC problem in the customer's own words.\n"
            "- urgency: 'emergency' if system is completely down, safety hazard, or extreme temperatures; "
            "'urgent' if needs service within 2-3 days; 'routine' for standard scheduling.\n"
            "- isEmergency: true only for genuine emergencies (no heat in winter, no AC in extreme heat, gas smell, carbon monoxide, flooding from unit).\n"
            "- technicianNotes: special instructions for the tech (e.g., 'unit is on the roof', 'system makes grinding noise on startup', 'dog in backyard').\n"
            "- isWarranty: true if the customer mentioned a warranty, recent installation, or previous repair that should still be covered.\n"
            "- existingAppointmentId: for reschedule/cancel — the appointment ID mentioned by the assistant from check_appointment_status results.\n"
            "- Leave fields null if not discussed."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["book", "reschedule", "cancel", "none"],
                    "description": (
                        "The appointment action the customer CONFIRMED. "
                        "'book' = new appointment confirmed, 'reschedule' = existing appointment moved to new time, "
                        "'cancel' = existing appointment cancelled, 'none' = no appointment action was confirmed."
                    ),
                },
                "chosenSlotStart": {
                    "type": "string",
                    "description": (
                        "ISO 8601 datetime of the appointment start time the customer chose. "
                        "Extract from the check_availability tool result's next_available_slots[].start field, NOT from spoken text. "
                        "Example: '2026-03-05T08:00:00-06:00'. For reschedule, this is the NEW slot start."
                    ),
                },
                "chosenSlotEnd": {
                    "type": "string",
                    "description": (
                        "ISO 8601 datetime of the appointment end time. "
                        "Extract from check_availability tool result's next_available_slots[].end field. "
                        "Example: '2026-03-05T12:00:00-06:00'."
                    ),
                },
                "chosenSlotTechnicianId": {
                    "type": "string",
                    "description": (
                        "REQUIRED when action is 'book'. Technician ID (res.users id) of the slot the customer chose. "
                        "From check_availability tool result: next_available_slots[0].technician_id if customer chose the first option, "
                        "next_available_slots[1].technician_id if they chose the second. Set to null for reschedule/cancel/none. "
                        "Without this, the job may be assigned to the wrong person."
                    ),
                },
                "appointmentWindow": {
                    "type": "string",
                    "description": "The 4-hour service window as spoken to the customer (e.g., '8 AM to 12 PM', '12 PM to 4 PM', '1 PM to 5 PM').",
                },
                "existingAppointmentId": {
                    "type": "string",
                    "description": (
                        "For reschedule or cancel only: the Odoo appointment/event ID of the existing appointment being modified. "
                        "Extract from the check_appointment_status tool result if it was called during the conversation."
                    ),
                },
                "serviceType": {
                    "type": "string",
                    "description": (
                        "The type of HVAC service needed. Examples: 'AC repair', 'heater not working', 'maintenance tune-up', "
                        "'thermostat replacement', 'duct cleaning', 'new system installation', 'refrigerant recharge'."
                    ),
                },
                "problemDescription": {
                    "type": "string",
                    "description": (
                        "Detailed description of the HVAC issue in the customer's own words. "
                        "Include symptoms, when it started, what they've tried, and any relevant details. "
                        "Example: 'AC blowing warm air since yesterday, changed the filter but still not cooling, house is 85 degrees'."
                    ),
                },
                "urgency": {
                    "type": "string",
                    "enum": ["emergency", "urgent", "routine"],
                    "description": (
                        "'emergency' = system fully down, safety hazard, extreme temps (over 95F or below 40F inside); "
                        "'urgent' = significant discomfort, needs service within 2-3 days; "
                        "'routine' = standard scheduling, maintenance, non-critical repairs."
                    ),
                },
                "isEmergency": {
                    "type": "boolean",
                    "description": (
                        "True only for genuine HVAC emergencies: complete system failure in extreme weather, "
                        "gas smell, carbon monoxide alarm, water flooding from unit, no heat with vulnerable occupants. "
                        "False for all routine and non-life-threatening situations."
                    ),
                },
                "technicianNotes": {
                    "type": "string",
                    "description": (
                        "Special notes for the technician visiting the property. Include: equipment location (roof, attic, closet, garage), "
                        "access issues, pets, specific symptoms observed, brand/model if mentioned, previous repair history, "
                        "anything that helps the tech prepare. Example: 'Trane XR15 on the roof, unit making clicking sound, "
                        "tenant says filter was changed last week'."
                    ),
                },
                "isWarranty": {
                    "type": "boolean",
                    "description": "True if the customer mentioned warranty coverage, a recent installation (within 1-2 years), or a previous repair they believe should still be covered.",
                },
                "previousServiceId": {
                    "type": "string",
                    "description": "Reference number of a previous service visit if mentioned (e.g., 'my last service was ticket number 12345'). Null if not discussed.",
                },
                "cancellationReason": {
                    "type": "string",
                    "description": "For cancel action only: why the customer is cancelling (e.g., 'found another company', 'issue resolved itself', 'schedule conflict'). Null if not cancelling.",
                },
                "rescheduleReason": {
                    "type": "string",
                    "description": "For reschedule action only: why the customer is rescheduling (e.g., 'work conflict', 'won't be home', 'need it sooner'). Null if not rescheduling.",
                },
            },
            "required": ["action", "chosenSlotTechnicianId"],
        },
    },
    # ── Output 3: Pending Request ─────────────────────────────────────
    {
        "name": "Pending Request",
        "type": "ai",
        "description": (
            "Extract any pending service requests from this HVAC call that need post-call processing. "
            "These are requests where the customer discussed a need but no real-time tool was called to fulfill it. "
            "The assistant verbally confirms these requests and tells the customer they'll receive follow-up.\n\n"
            "EXTRACTION RULES:\n"
            "- requestType is REQUIRED. Choose the SINGLE most relevant type from the call.\n"
            "- 'quote' = customer wants a price estimate for a new system, replacement, or major work.\n"
            "- 'complaint' = customer is unhappy with a previous service, technician, or experience.\n"
            "- 'invoice' = customer wants a copy of an invoice or billing document emailed to them.\n"
            "- 'membership' = customer wants to enroll in a maintenance plan (Basic $9.99/mo or Commercial $19.99/mo).\n"
            "- 'service_request' = customer described an HVAC issue but did NOT book an appointment (e.g., wanted to check with spouse first, "
            "no slots worked, after-hours call where booking was deferred).\n"
            "- 'none' = no pending request — the call was fully handled (appointment booked, question answered, etc.).\n"
            "- Only populate the sub-object that matches the requestType. Leave others null.\n"
            "- If an appointment was ALSO booked (Appointment Action.action = 'book'), this output captures ADDITIONAL requests beyond the booking."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "requestType": {
                    "type": "string",
                    "enum": ["quote", "complaint", "invoice", "membership", "service_request", "none"],
                    "description": (
                        "The type of pending request. 'quote' = price estimate for new system/major work, "
                        "'complaint' = dissatisfied with previous service, 'invoice' = wants invoice copy emailed, "
                        "'membership' = wants to enroll in maintenance plan, "
                        "'service_request' = described HVAC issue but didn't book appointment, "
                        "'none' = no pending request."
                    ),
                },
                "quoteRequest": {
                    "type": "object",
                    "description": "Details for a quote/estimate request. Only populate when requestType='quote'.",
                    "properties": {
                        "squareFootage": {
                            "type": "string",
                            "description": "Approximate square footage of the home or commercial space (e.g., '2500 sq ft', 'about 3000').",
                        },
                        "systemAge": {
                            "type": "string",
                            "description": "Age of the current HVAC system (e.g., '15 years old', 'installed in 2010', 'original to the house').",
                        },
                        "budgetRange": {
                            "type": "string",
                            "description": "Customer's budget or price sensitivity if mentioned (e.g., 'around $5000', 'looking for financing', 'whatever it takes').",
                        },
                        "timeline": {
                            "type": "string",
                            "description": "When they need the work done (e.g., 'before summer', 'as soon as possible', 'next month', 'just exploring options').",
                        },
                        "systemType": {
                            "type": "string",
                            "description": "Type of system they're interested in or currently have (e.g., 'central AC', 'heat pump', 'mini split', 'furnace replacement').",
                        },
                    },
                },
                "complaint": {
                    "type": "object",
                    "description": "Details for a complaint. Only populate when requestType='complaint'.",
                    "properties": {
                        "details": {
                            "type": "string",
                            "description": "Full description of the complaint in the customer's own words. Include what happened, what went wrong, and what they expected.",
                        },
                        "previousServiceDate": {
                            "type": "string",
                            "description": "When the service they're complaining about occurred (e.g., '2026-02-15', 'last week', 'two weeks ago').",
                        },
                        "previousServiceId": {
                            "type": "string",
                            "description": "Service ticket or work order number from the previous visit, if the customer provided it.",
                        },
                        "requestedManagerCallback": {
                            "type": "boolean",
                            "description": "True if the customer explicitly asked to speak with or get a callback from a manager or supervisor.",
                        },
                    },
                },
                "invoiceRequest": {
                    "type": "object",
                    "description": "Details for an invoice copy request. Only populate when requestType='invoice'.",
                    "properties": {
                        "invoiceNumber": {
                            "type": "string",
                            "description": "Invoice number if the customer provided it. Null if they just want 'my last invoice' or similar.",
                        },
                    },
                },
                "membershipEnrollment": {
                    "type": "object",
                    "description": "Details for maintenance plan enrollment. Only populate when requestType='membership'.",
                    "properties": {
                        "membershipType": {
                            "type": "string",
                            "enum": ["basic", "commercial"],
                            "description": "'basic' = residential plan ($9.99/month, 2 tune-ups/year, 15% parts discount), 'commercial' = commercial plan ($19.99/month, 4 tune-ups/year, 20% parts discount).",
                        },
                        "systemDetails": {
                            "type": "string",
                            "description": "Details about the customer's system relevant to the plan (e.g., 'two AC units', 'residential with 3-ton system', 'commercial rooftop unit').",
                        },
                    },
                },
                "serviceRequest": {
                    "type": "object",
                    "description": (
                        "For HVAC service requests where the customer described a problem but did NOT book an appointment. "
                        "Common reasons: no available slots worked for them, they need to check with spouse, after-hours call, "
                        "or they want someone to call them back. Only populate when requestType='service_request'."
                    ),
                    "properties": {
                        "issueDescription": {
                            "type": "string",
                            "description": "Detailed description of the HVAC issue. Include symptoms, duration, what they've tried, and severity.",
                        },
                        "systemType": {
                            "type": "string",
                            "description": "Type of HVAC system with the issue (e.g., 'central AC', 'gas furnace', 'heat pump', 'mini split', 'rooftop unit').",
                        },
                        "isWarranty": {
                            "type": "boolean",
                            "description": "True if the customer believes the issue should be covered under warranty or a recent installation.",
                        },
                        "previousServiceId": {
                            "type": "string",
                            "description": "Previous service ticket number if this is a follow-up or recurring issue.",
                        },
                        "technicianNotes": {
                            "type": "string",
                            "description": "Any technical details that would help the technician: unit location, brand/model, error codes, noises, smells, etc.",
                        },
                    },
                },
            },
            "required": ["requestType"],
        },
    },
    # ── Output 4: Call Analytics ──────────────────────────────────────
    {
        "name": "Call Analytics",
        "type": "ai",
        "description": (
            "Classify this HVAC service call by intent, resolution, and customer sentiment. "
            "This output runs on EVERY call for analytics and quality tracking.\n\n"
            "EXTRACTION RULES:\n"
            "- primaryIntent: what was the MAIN reason the customer called? Choose the single most dominant intent.\n"
            "- resolution: what was the OUTCOME of the call? How was it resolved?\n"
            "- Match resolution to what actually happened, not what was attempted. "
            "If the customer wanted to book but no slots worked, resolution is 'service_request_created' (not 'appointment_booked').\n"
            "- sentiment: overall customer emotional tone during the call. "
            "'positive' = happy, grateful, satisfied; 'neutral' = matter-of-fact, transactional; "
            "'frustrated' = annoyed, impatient, mildly unhappy; 'angry' = hostile, demanding, threatening.\n"
            "- followUpRequired: true if someone needs to call the customer back, a manager review is needed, "
            "or the issue wasn't fully resolved during the call.\n"
            "- callCompleted: true if the call reached a natural conclusion (goodbye, hang up after resolution). "
            "False if dropped, caller hung up mid-conversation, or the call was cut short.\n"
            "- callSummary: REQUIRED. Write a complete 2-5 sentence narrative of the call: what the customer needed, "
            "what was discussed (issue, urgency, options offered), and the outcome. This is stored in Odoo on the job/lead."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "primaryIntent": {
                    "type": "string",
                    "enum": [
                        "service_repair", "quote", "maintenance", "appointment_check",
                        "reschedule", "cancel", "billing", "complaint", "membership",
                        "invoice_request", "general_question", "other",
                    ],
                    "description": (
                        "The customer's primary reason for calling. "
                        "'service_repair' = something is broken/not working, 'quote' = wants a price estimate for new system or major work, "
                        "'maintenance' = routine tune-up or seasonal check, 'appointment_check' = asking about an existing appointment, "
                        "'reschedule' = wants to change appointment time, 'cancel' = wants to cancel an appointment, "
                        "'billing' = questions about charges, payments, or account balance, 'complaint' = unhappy with previous service, "
                        "'membership' = interested in maintenance plan, 'invoice_request' = wants a copy of an invoice, "
                        "'general_question' = asking about hours, services, service area, etc., 'other' = doesn't fit any category."
                    ),
                },
                "resolution": {
                    "type": "string",
                    "enum": [
                        "appointment_booked", "service_request_created", "quote_requested",
                        "rescheduled", "cancelled", "complaint_filed", "question_answered",
                        "membership_enrolled", "invoice_requested", "transferred", "incomplete",
                    ],
                    "description": (
                        "How the call was resolved. "
                        "'appointment_booked' = customer confirmed a specific appointment slot, "
                        "'service_request_created' = issue noted but no appointment booked (will get callback), "
                        "'quote_requested' = estimate request submitted for follow-up, "
                        "'rescheduled' = existing appointment moved to new time, "
                        "'cancelled' = existing appointment cancelled, "
                        "'complaint_filed' = complaint documented for management review, "
                        "'question_answered' = informational question answered (hours, pricing, service area), "
                        "'membership_enrolled' = maintenance plan enrollment initiated, "
                        "'invoice_requested' = invoice copy will be sent, "
                        "'transferred' = caller was transferred to a human, "
                        "'incomplete' = call ended before resolution (dropped, hung up, unresolved)."
                    ),
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "neutral", "frustrated", "angry"],
                    "description": (
                        "Overall customer emotional tone. "
                        "'positive' = happy, appreciative, satisfied with the interaction; "
                        "'neutral' = calm, business-like, neither happy nor upset; "
                        "'frustrated' = showing annoyance, impatience, or mild dissatisfaction; "
                        "'angry' = hostile, raising voice, making demands or threats."
                    ),
                },
                "followUpRequired": {
                    "type": "boolean",
                    "description": (
                        "True if post-call follow-up is needed: manager callback requested, issue unresolved, "
                        "customer asked to be called back, quote needs to be prepared, or any other reason someone needs to contact the customer."
                    ),
                },
                "followUpReason": {
                    "type": "string",
                    "description": "Why follow-up is needed. Only populate when followUpRequired is true. Be specific (e.g., 'Customer requested manager callback about complaint', 'No available slots — needs scheduling callback').",
                },
                "callCompleted": {
                    "type": "boolean",
                    "description": "True if the call reached a natural conclusion with proper goodbye. False if the call was dropped, the customer hung up abruptly, or was cut short by technical issues.",
                },
                "callSummary": {
                    "type": "string",
                    "description": (
                        "Complete narrative summary of the call in 2-5 sentences: what the customer needed, "
                        "what was discussed (e.g. issue, urgency, slot offered), and the outcome (e.g. appointment confirmed, "
                        "rescheduled, quote requested). This summary is stored in Odoo on the lead and FSM task for technician and office reference."
                    ),
                },
            },
            "required": ["primaryIntent", "resolution"],
        },
    },
]


def main():
    print(f"Registering {len(OUTPUTS)} structured outputs for assistant {ASSISTANT_ID}...\n")

    output_ids = []

    with httpx.Client(timeout=30) as client:
        for output_def in OUTPUTS:
            print(f"  Creating: {output_def['name']}...")
            resp = client.post(
                f"{BASE_URL}/structured-output",
                headers=HEADERS,
                json=output_def,
            )
            if resp.status_code not in (200, 201):
                print(f"    ERROR: {resp.status_code} - {resp.text}")
                continue

            data = resp.json()
            output_id = data.get("id")
            output_ids.append(output_id)
            print(f"    Created: {output_id}")

        if not output_ids:
            print("\nNo outputs created. Aborting.")
            return

        # Attach to assistant via artifactPlan
        print(f"\nAttaching {len(output_ids)} outputs to assistant...")
        resp = client.patch(
            f"{BASE_URL}/assistant/{ASSISTANT_ID}",
            headers=HEADERS,
            json={
                "artifactPlan": {
                    "structuredOutputIds": output_ids,
                },
                "analysisPlan": {
                    "summaryPlan": {"enabled": True},
                    "successEvaluationPlan": {
                        "enabled": True,
                        "rubric": "PassFail",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Did Riley successfully handle the caller's primary request "
                                    "without needing a human transfer? Consider: was an appointment "
                                    "booked, service request created, or question answered?"
                                ),
                            }
                        ],
                    },
                },
            },
        )

        if resp.status_code == 200:
            print("  Success! Structured outputs attached.")
        else:
            print(f"  ERROR attaching: {resp.status_code} - {resp.text}")

    print("\n--- Structured Output IDs ---")
    for i, (output_def, oid) in enumerate(zip(OUTPUTS, output_ids)):
        print(f"  {i+1}. {output_def['name']}: {oid}")

    print("\nDone. These outputs will now run on every call and results will appear in")
    print("call.artifact.structuredOutputs in the end-of-call-report webhook.")


if __name__ == "__main__":
    main()
