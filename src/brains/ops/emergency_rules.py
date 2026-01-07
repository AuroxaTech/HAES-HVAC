"""
HAES HVAC - OPS Brain Emergency Rules

Deterministic emergency qualification rules from RDD.
"""

from dataclasses import dataclass

from src.hael.schema import Entity, UrgencyLevel


@dataclass
class EmergencyResult:
    """Result of emergency qualification."""
    is_emergency: bool
    reason: str
    priority_override: int  # 1 = immediate


# Emergency keywords that always qualify
ALWAYS_EMERGENCY_KEYWORDS = [
    "gas leak",
    "smell gas",
    "carbon monoxide",
    "co detector",
    "burning smell",
    "electrical smell",
    "smoke",
    "sparks",
    "fire",
    "flames",
    "flooding",
    "water damage",
    "refrigerant leak",
    "server room",
    "data center",
    "medical equipment",
    "medication storage",
    "freezer failure",
    "walk-in cooler",
]

# Temperature thresholds from RDD
NO_HEAT_TEMP_THRESHOLD = 55  # °F - below this, no heat is emergency
NO_AC_TEMP_THRESHOLD = 85    # °F - above this, no AC is emergency


def qualify_emergency(
    problem_description: str,
    urgency_level: UrgencyLevel,
    temperature_mentioned: int | None = None,
) -> EmergencyResult:
    """
    Determine if a service request qualifies as emergency.
    
    Rules from RDD:
    - Gas leak / carbon monoxide → always emergency
    - Electrical burning smell / breaker tripping → always emergency
    - Refrigerant leak visible/audible → always emergency
    - Flooding/water damage from HVAC → always emergency
    - Medical/refrigeration/server room → always emergency
    - No heat + outside temp < 55°F → emergency
    - No AC + outside temp > 85°F → emergency
    
    Args:
        problem_description: Description of the problem
        urgency_level: Urgency from HAEL extraction
        temperature_mentioned: Temperature if mentioned by caller
        
    Returns:
        EmergencyResult with qualification status
    """
    desc_lower = problem_description.lower()
    
    # Check always-emergency keywords
    for keyword in ALWAYS_EMERGENCY_KEYWORDS:
        if keyword in desc_lower:
            return EmergencyResult(
                is_emergency=True,
                reason=f"Emergency condition detected: {keyword}",
                priority_override=1,
            )
    
    # Temperature-based emergency detection
    if temperature_mentioned is not None:
        # No heat emergency
        if ("no heat" in desc_lower or "heating not working" in desc_lower):
            if temperature_mentioned < NO_HEAT_TEMP_THRESHOLD:
                return EmergencyResult(
                    is_emergency=True,
                    reason=f"No heat emergency: temperature {temperature_mentioned}°F below {NO_HEAT_TEMP_THRESHOLD}°F threshold",
                    priority_override=1,
                )
        
        # No AC emergency
        if ("no ac" in desc_lower or "no cooling" in desc_lower or 
            "ac not working" in desc_lower or "air conditioning not working" in desc_lower):
            if temperature_mentioned > NO_AC_TEMP_THRESHOLD:
                return EmergencyResult(
                    is_emergency=True,
                    reason=f"No AC emergency: temperature {temperature_mentioned}°F above {NO_AC_TEMP_THRESHOLD}°F threshold",
                    priority_override=1,
                )
    
    # Check if HAEL already classified as emergency
    if urgency_level == UrgencyLevel.EMERGENCY:
        return EmergencyResult(
            is_emergency=True,
            reason="Emergency urgency level from caller context",
            priority_override=1,
        )
    
    # Not an emergency
    return EmergencyResult(
        is_emergency=False,
        reason="Standard service request",
        priority_override=5,
    )


def get_emergency_dispatch_instructions(result: EmergencyResult) -> str:
    """
    Get dispatch instructions for emergency situations.
    
    Returns:
        Human-readable dispatch instructions
    """
    if not result.is_emergency:
        return "Standard scheduling applies."
    
    return (
        f"EMERGENCY DISPATCH REQUIRED\n"
        f"Reason: {result.reason}\n"
        f"Action: Dispatch nearest available technician immediately.\n"
        f"Priority: {result.priority_override} (Highest)\n"
        f"Note: Override normal scheduling queue."
    )

