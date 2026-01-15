"""
HAES HVAC - REVENUE Brain Lead Qualification

Deterministic hot/warm/cold classification from RDD Section 5.
"""

from src.hael.schema import Entity, UrgencyLevel
from src.brains.revenue.schema import LeadQualification


# Hot lead indicators from RDD
HOT_KEYWORDS = [
    "emergency", "urgent", "asap", "immediately",
    "today", "right now", "schedule today",
    "ready to book", "ready to schedule",
    "need it done", "can't wait",
    "decision maker", "budget approved",
    "within 72 hours", "next 3 days",
]

# Warm lead indicators from RDD
WARM_KEYWORDS = [
    "this week", "next week",
    "soon", "looking to",
    "planning", "thinking about",
    "discomfort", "uncomfortable",
    "3 to 14 days", "couple weeks",
]

# Cold lead indicators from RDD
COLD_KEYWORDS = [
    "just looking", "price shopping",
    "no rush", "no urgency",
    "maybe later", "next month",
    "15 days", "few weeks out",
    "comparing quotes", "getting quotes",
]


def qualify_lead(
    problem_description: str | None,
    timeline: str | None,
    urgency_level: UrgencyLevel,
    budget_range: str | None = None,
) -> tuple[LeadQualification, float, str]:
    """
    Qualify a lead as hot, warm, or cold.
    
    Rules from RDD Section 5:
    - Hot: Emergency, ready to schedule today, install within 72h, decision maker + budget
    - Warm: Discomfort but working, 3-14 days
    - Cold: Price shopping, no urgency, 15+ days
    
    Args:
        problem_description: Description of need
        timeline: Expressed timeline
        urgency_level: HAEL urgency classification
        budget_range: Budget if mentioned
        
    Returns:
        Tuple of (qualification, confidence, reason)
    """
    # Combine text for keyword matching
    text = " ".join([
        problem_description or "",
        timeline or "",
        budget_range or "",
    ]).lower()
    
    # Check for emergency/urgency from HAEL
    if urgency_level == UrgencyLevel.EMERGENCY:
        return LeadQualification.HOT, 0.95, "Emergency-qualified from urgency level"
    
    # Check hot keywords
    hot_matches = [kw for kw in HOT_KEYWORDS if kw in text]
    if hot_matches:
        return LeadQualification.HOT, 0.85, f"Hot indicators: {', '.join(hot_matches[:3])}"
    
    # Check cold keywords (before warm, as cold is more specific)
    cold_matches = [kw for kw in COLD_KEYWORDS if kw in text]
    if cold_matches:
        return LeadQualification.COLD, 0.8, f"Cold indicators: {', '.join(cold_matches[:3])}"
    
    # Check warm keywords
    warm_matches = [kw for kw in WARM_KEYWORDS if kw in text]
    if warm_matches:
        return LeadQualification.WARM, 0.75, f"Warm indicators: {', '.join(warm_matches[:3])}"
    
    # High urgency from HAEL
    if urgency_level == UrgencyLevel.HIGH:
        return LeadQualification.HOT, 0.7, "High urgency level"
    
    if urgency_level == UrgencyLevel.MEDIUM:
        return LeadQualification.WARM, 0.65, "Medium urgency level"
    
    # Default to warm with moderate confidence (timeline-based)
    # If timeline mentions "week" or "weeks", it's likely warm
    if timeline and "week" in timeline.lower():
        return LeadQualification.WARM, 0.65, "Timeline-based classification (weeks)"
    # Default to warm with moderate confidence
    return LeadQualification.WARM, 0.6, "Default classification"


def get_response_time_goal(qualification: LeadQualification) -> int:
    """
    Get response time goal in minutes from RDD.
    
    Args:
        qualification: Lead qualification level
        
    Returns:
        Target response time in minutes
    """
    goals = {
        LeadQualification.HOT: 15,    # 15 minutes
        LeadQualification.WARM: 60,   # 1 hour
        LeadQualification.COLD: 240,  # 4 hours
    }
    return goals.get(qualification, 60)

