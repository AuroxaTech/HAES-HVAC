"""
HAES HVAC - REVENUE Brain Follow-up Sequences

Deterministic follow-up plan generation from RDD Section 5.
"""

from datetime import datetime, timedelta

from src.brains.revenue.schema import FollowUpAction, LeadQualification


# Follow-up sequences from RDD
# Quote sent:
# - Immediate thank you
# - +2 days reminder if no response
# - +7 days nurture if "maybe"
# - +90 days reactivation if "lost"


def generate_quote_followups(
    quote_sent_at: datetime,
    qualification: LeadQualification,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> list[FollowUpAction]:
    """
    Generate follow-up actions for a quote.
    
    Sequence from RDD:
    1. Immediate thank you
    2. +2 days reminder
    3. +7 days nurture sequence
    4. +90 days reactivation
    
    Args:
        quote_sent_at: When the quote was sent
        qualification: Lead qualification level
        customer_email: Customer email for delivery
        customer_phone: Customer phone for SMS
        
    Returns:
        List of scheduled follow-up actions
    """
    followups = []
    
    # Determine channel preference
    channel = "email" if customer_email else "sms" if customer_phone else "call"
    
    # 1. Immediate thank you
    followups.append(FollowUpAction(
        action_type="thank_you",
        scheduled_at=quote_sent_at,
        message_template="thank_you_quote",
        channel=channel,
    ))
    
    # 2. +2 days reminder (if no response)
    followups.append(FollowUpAction(
        action_type="reminder",
        scheduled_at=quote_sent_at + timedelta(days=2),
        message_template="quote_reminder_2day",
        channel=channel,
    ))
    
    # 3. +7 days nurture (for warm/cold leads)
    if qualification in [LeadQualification.WARM, LeadQualification.COLD]:
        followups.append(FollowUpAction(
            action_type="nurture",
            scheduled_at=quote_sent_at + timedelta(days=7),
            message_template="quote_nurture_7day",
            channel=channel,
        ))
    
    # 4. +90 days reactivation (for all)
    followups.append(FollowUpAction(
        action_type="reactivation",
        scheduled_at=quote_sent_at + timedelta(days=90),
        message_template="quote_reactivation_90day",
        channel=channel,
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

