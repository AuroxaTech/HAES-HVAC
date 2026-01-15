"""
HAES HVAC - REVENUE Brain Follow-up Sequences

Deterministic follow-up plan generation from RDD Section 5.
Matches exact test sequences from Test 5.5.
"""

from datetime import datetime, timedelta

from src.brains.revenue.schema import FollowUpAction, LeadQualification


# Follow-up sequences from Test 5.5:
# 1. Quote Sent: Immediate thank-you text + financing options + scheduling link
# 2. 2 days no response: Auto reminder text + email + call task for CSR
# 3. "Maybe" response: Day 1 education email, Day 3 testimonial, Day 7 financing reminder
# 4. Lost deal: Day 30 check-in, Day 60 seasonal promo, Day 90 rebate alert


def generate_quote_followups(
    quote_sent_at: datetime,
    qualification: LeadQualification,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    lead_id: int | None = None,
    odoo_url: str | None = None,
) -> list[FollowUpAction]:
    """
    Generate follow-up actions for a quote (Test 5.5 - Scenario 1).
    
    Sequence:
    1. Immediate thank-you text + financing options + scheduling link
    2. +2 days: Auto reminder text + email + call task for CSR
    3. "Maybe" response sequence (triggered separately)
    4. Lost deal reactivation (triggered separately)
    
    Args:
        quote_sent_at: When the quote was sent
        qualification: Lead qualification level
        customer_email: Customer email for delivery
        customer_phone: Customer phone for SMS
        lead_id: Odoo lead ID for links
        odoo_url: Odoo lead URL for scheduling
        
    Returns:
        List of scheduled follow-up actions
    """
    followups = []
    
    # Determine channel preference
    channel = "email" if customer_email else "sms" if customer_phone else "call"
    
    # 1. Immediate: Thank-you text + financing options + scheduling link
    # Send via both SMS (if phone) and email (if email) for better delivery
    if customer_phone:
        followups.append(FollowUpAction(
            action_type="thank_you",
            scheduled_at=quote_sent_at,
            message_template="quote_thank_you_immediate_sms",
            channel="sms",
            metadata={
                "include_financing_options": True,
                "include_scheduling_link": True,
                "scheduling_link": odoo_url or (f"https://hvacrfinest.odoo.com/web#id={lead_id}&model=crm.lead&view_type=form" if lead_id else ""),
                "financing_partners": ["Greensky", "FTL", "Microft"],
            },
        ))
    
    if customer_email:
        followups.append(FollowUpAction(
            action_type="thank_you",
            scheduled_at=quote_sent_at,
            message_template="quote_thank_you_immediate_email",
            channel="email",
            metadata={
                "include_financing_options": True,
                "include_scheduling_link": True,
                "scheduling_link": odoo_url or (f"https://hvacrfinest.odoo.com/web#id={lead_id}&model=crm.lead&view_type=form" if lead_id else ""),
                "financing_partners": ["Greensky", "FTL", "Microft"],
            },
        ))
    
    # 2. +2 days: Auto reminder text + email + call task for CSR
    # (Only if no response - this would be conditionally triggered by tracking)
    two_day_mark = quote_sent_at + timedelta(days=2)
    
    if customer_phone:
        followups.append(FollowUpAction(
            action_type="reminder",
            scheduled_at=two_day_mark,
            message_template="quote_reminder_2day_sms",
            channel="sms",
            metadata={
                "conditional": "no_response",
                "create_csr_task": True,
                "lead_id": lead_id,
            },
        ))
    
    if customer_email:
        followups.append(FollowUpAction(
            action_type="reminder",
            scheduled_at=two_day_mark,
            message_template="quote_reminder_2day_email",
            channel="email",
            metadata={
                "conditional": "no_response",
                "create_csr_task": True,
                "lead_id": lead_id,
            },
        ))
    
    # CSR call task (to be created in Odoo)
    followups.append(FollowUpAction(
        action_type="csr_call_task",
        scheduled_at=two_day_mark,
        message_template="quote_csr_call_task",
        channel="odoo_task",
        metadata={
            "conditional": "no_response",
            "lead_id": lead_id,
            "task_type": "call_customer",
            "priority": "medium",
        },
    ))
    
    return followups


def generate_maybe_response_followups(
    maybe_date: datetime,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    lead_id: int | None = None,
) -> list[FollowUpAction]:
    """
    Generate follow-up sequence for "maybe" response (Test 5.5 - Scenario 2).
    
    Sequence:
    - Day 1: Education email
    - Day 3: Testimonial
    - Day 7: Financing reminder
    
    Args:
        maybe_date: When customer said "maybe"
        customer_email: Customer email
        customer_phone: Customer phone
        lead_id: Odoo lead ID
        
    Returns:
        List of scheduled follow-up actions
    """
    followups = []
    
    # Day 1: Education email
    if customer_email:
        followups.append(FollowUpAction(
            action_type="nurture",
            scheduled_at=maybe_date + timedelta(days=1),
            message_template="maybe_education_email",
            channel="email",
            metadata={
                "sequence": "maybe_response",
                "day": 1,
                "lead_id": lead_id,
            },
        ))
    
    # Day 3: Testimonial
    if customer_email:
        followups.append(FollowUpAction(
            action_type="nurture",
            scheduled_at=maybe_date + timedelta(days=3),
            message_template="maybe_testimonial_email",
            channel="email",
            metadata={
                "sequence": "maybe_response",
                "day": 3,
                "lead_id": lead_id,
            },
        ))
    
    # Day 7: Financing reminder
    if customer_email:
        followups.append(FollowUpAction(
            action_type="nurture",
            scheduled_at=maybe_date + timedelta(days=7),
            message_template="maybe_financing_reminder_email",
            channel="email",
            metadata={
                "sequence": "maybe_response",
                "day": 7,
                "lead_id": lead_id,
                "financing_partners": ["Greensky", "FTL", "Microft"],
            },
        ))
    
    return followups


def generate_lost_deal_followups(
    lost_date: datetime,
    customer_email: str | None = None,
    customer_phone: str | None = None,
    lead_id: int | None = None,
) -> list[FollowUpAction]:
    """
    Generate reactivation sequence for lost deal (Test 5.5 - Scenario 3).
    
    Sequence:
    - Day 30: Check-in email
    - Day 60: Seasonal promo
    - Day 90: Rebate alert
    
    Args:
        lost_date: When deal was marked as lost
        customer_email: Customer email
        customer_phone: Customer phone
        lead_id: Odoo lead ID
        
    Returns:
        List of scheduled follow-up actions
    """
    followups = []
    
    # Day 30: Check-in email
    if customer_email:
        followups.append(FollowUpAction(
            action_type="reactivation",
            scheduled_at=lost_date + timedelta(days=30),
            message_template="lost_deal_checkin_30day",
            channel="email",
            metadata={
                "sequence": "lost_deal",
                "day": 30,
                "lead_id": lead_id,
            },
        ))
    
    # Day 60: Seasonal promo
    if customer_email:
        followups.append(FollowUpAction(
            action_type="reactivation",
            scheduled_at=lost_date + timedelta(days=60),
            message_template="lost_deal_seasonal_promo_60day",
            channel="email",
            metadata={
                "sequence": "lost_deal",
                "day": 60,
                "lead_id": lead_id,
            },
        ))
    
    # Day 90: Rebate alert
    if customer_email:
        followups.append(FollowUpAction(
            action_type="reactivation",
            scheduled_at=lost_date + timedelta(days=90),
            message_template="lost_deal_rebate_alert_90day",
            channel="email",
            metadata={
                "sequence": "lost_deal",
                "day": 90,
                "lead_id": lead_id,
            },
        ))
    
    return followups


def generate_lead_followups(
    lead_created_at: datetime,
    qualification: LeadQualification,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> list[FollowUpAction]:
    """
    Generate follow-up actions for a new lead.
    
    Args:
        lead_created_at: When the lead was created
        qualification: Lead qualification level
        customer_email: Customer email
        customer_phone: Customer phone
        
    Returns:
        List of scheduled follow-up actions
    """
    followups = []
    channel = "email" if customer_email else "sms" if customer_phone else "call"
    
    # Hot leads get faster follow-up
    if qualification == LeadQualification.HOT:
        # Immediate call back
        followups.append(FollowUpAction(
            action_type="callback",
            scheduled_at=lead_created_at + timedelta(minutes=15),
            message_template="hot_lead_callback",
            channel="call",
        ))
        # Same day follow-up if not reached
        followups.append(FollowUpAction(
            action_type="reminder",
            scheduled_at=lead_created_at + timedelta(hours=4),
            message_template="hot_lead_followup",
            channel=channel,
        ))
    else:
        # Standard follow-up
        followups.append(FollowUpAction(
            action_type="initial_contact",
            scheduled_at=lead_created_at + timedelta(hours=1),
            message_template="new_lead_contact",
            channel=channel,
        ))
    
    return followups

