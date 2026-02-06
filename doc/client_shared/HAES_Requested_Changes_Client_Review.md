# HAES HVAC - Requested Changes Summary

**Date:** February 6, 2026  
**Project:** HAES HVAC-R FINEST AI Voice Agent System  
**Purpose:** Review & Validation  

---

## Dear Junior & Linda,

We've reviewed the 5 voice recordings you shared with us and documented all the changes you'd like to see in the AI voice agent system. Please review this summary to confirm we've captured everything correctly.

---

## RESIDENTIAL SERVICE CHANGES

### 1. Ring Delay Before Bot Answers
The phone should ring for a few seconds (2-3 seconds) before the bot picks up, rather than answering immediately. This creates a more natural phone experience for customers.

### 2. Enhanced Diagnostic Questions
When customers call with an issue, the bot needs to ask more detailed questions to help technicians identify the problem faster:

- **For water leaks:** Where is the water leak located? Where do you see the water? Is it coming from the inside unit or outside unit?

- **For units not working:** Is it the outside unit or the inside unit that's not working? When did you first notice the problem? How long have you lived in the house?

- **For cooling/heating issues:** Is the unit making any noise? When did you notice it's not cooling or heating properly? Has this happened before?

- **For appliance identification:** Do you have an electric or gas stove? What type of appliance is having the issue?

The goal is to collect detailed information so technicians can prepare properly before arriving on-site.

### 3. Automatic Callback on Call Disconnection
If a call accidentally hangs up or gets disconnected, the bot should automatically call the customer back and pick up the conversation where it left off. Customers shouldn't have to start over from the beginning.

### 4. Returning Customer Recognition
The bot should detect when it's a returning customer (by phone number lookup) and address them by name. The bot should pull up their existing customer profile automatically instead of creating a new customer record.

### 5. Photo Submission via SMS
After the call ends and the appointment is scheduled, customers should be able to text photos of their problem to the same phone number. This allows technicians to see the issue before they arrive.

### 6. Two Time Slot Selection
When scheduling appointments, the bot must offer exactly 2 available time slots for the customer to choose from. For example: "I have Tuesday at 10 AM or Wednesday at 2 PM available. Which works better for you?"

### 7. Lead Source Tracking
Before finalizing the call, the bot should ask: "How did you hear about us?" The response should be tagged in the CRM so you can track which marketing channels are working (Google, referral, social media, previous customer, etc.).

### 8. Information Confirmation Before Finalizing
Before completing the appointment, the bot must repeat all collected information back to the customer for confirmation: name, address, phone number, service type, problem description, and scheduled appointment date/time. The bot asks: "Is all of this information correct?"

### 9. SMS and Email Confirmations After Call
Immediately after the call ends, send both an SMS and an email confirmation to the customer with all appointment details including date, time, service type, and confirmation number.

### 10. Six Question Maintenance Assessment
For maintenance calls, the bot should ask these six specific questions:

1. How has your HVAC system been operating? (If issues mentioned, probe deeper; if no issues, move to next question)
2. Have you noticed any hot or cold spots in different rooms?
3. Have you experienced unusually high electricity bills?
4. Does your home feel too sticky during summer or too dry during winter?
5. Has anyone in your household experienced allergy issues or increased sickness?
6. Have you noticed an increase in dust around the house?
7. Bonus: Do you know your air filter size? (If yes, note it so you can bring a replacement)

---

## PROPERTY MANAGEMENT CHANGES

### 11. Tenant vs Property Management Team Identification
At the beginning of the call, the bot needs to ask: "Are you calling as a tenant or as part of the property management team?" This determines the workflow:

- **Property Management Team:** Streamlined scheduling process, can schedule multiple properties
- **Tenant:** Standard service workflow with tenant details collected and property management notified

### 12. Scheduling Access for Both Caller Types
Both tenants and property management team members should be able to schedule service calls. Both should receive 2 available time slot options to choose from. The notification recipients will differ based on who called (tenant calls notify both tenant and PM; PM calls notify PM only).

---

## COMMERCIAL SERVICE CHANGES

### 13. Urgency Assessment
At the start of commercial calls, the bot should ask: "Is this an urgent issue requiring immediate attention, or can this be scheduled at your convenience?" This determines priority level and affects scheduling timeline.

### 14. Property Type-Specific Questions

**For Hotels:**
- Which room(s) are affected? (Room number, floor level, how many rooms total)
- Is there ladder access available? Do we need to bring our own ladder?
- Who should the technician check in with upon arrival? (Name, phone number, location)
- Are guests currently in the affected rooms?

**For Warehouses:**
- Where is ladder access available? What's the height of ceiling/units?
- What type of HVAC equipment do you have? (Rooftop units, package units, split systems)
- How many units need to be addressed? Are they all the same type?
- Will warehouse operations continue during service? Any safety protocols we need to follow?

**For Schools:**
- Where can we access ladders? Do we need to bring specific equipment?
- What type of HVAC system? How many units need service?
- Which areas of school are affected? (Classroom, gym, cafeteria, etc.)
- What time should technician arrive? School hours or after-hours preferred?
- Security check-in procedures? Background check requirements?

### 15. Multiple Work Orders for Same Location
When a commercial property (like a hotel) calls with multiple units or rooms needing service at the same address, the bot should create separate work orders for each issue. For example: Hotel calls with 3 rooms needing service → create 3 separate work orders (Work Order A: Room 305, Work Order B: Room 412, Work Order C: Room 518). All work orders are linked to the same customer/location, but tracked separately.

### 16. Commercial Details Checklist
Every commercial call must capture: sense of urgency (immediate or scheduled), property type (hotel, warehouse, school, restaurant, etc.), ladder access availability and location, equipment type and quantity, point of contact (name, phone, location), access restrictions (time, security, safety), business hours constraints, and any safety concerns or special requirements.

---

## CALL ROUTING & GENERAL CHANGES

### 17. Call Purpose Identification at Start
After the greeting, the bot should immediately ask: "I can help you with several things today. Are you calling for: (1) Service or repair, (2) Equipment replacement, (3) Scheduled maintenance, or (4) Do you have a question I can answer?" This routes the caller to the appropriate workflow right away.

### 18. Spanish Language Support (Future Phase)
You asked: "I'm curious if we're able to offer Spanish after we're done with this?" Yes, we can add Spanish language support as a Phase 2 enhancement after the English version is complete and working smoothly. The system would offer: "For English, press 1 or say English. Para español, oprima dos o diga español."

---

## CUSTOMER HISTORY & WARRANTY CHANGES

### 19. Enhanced Warranty Question
Change the question from "Have you called us before?" to "Have we provided service or warranty work at your house before?" This broader question captures more returning customers and includes warranty work, not just regular service calls.

### 20. Automatic Customer Profile Lookup
When a customer says yes to the warranty/service history question, the bot should automatically search for their existing profile by phone number and address. The bot confirms: "I found your profile, Mr. Smith at 123 Main Street, is that correct?" If confirmed, the bot loads the existing customer profile and creates a NEW work order under that existing customer (not a new customer record). This prevents duplicate customer records and maintains complete service history.

