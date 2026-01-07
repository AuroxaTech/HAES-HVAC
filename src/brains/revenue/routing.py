"""
HAES HVAC - REVENUE Brain Lead Routing

Deterministic lead assignment rules from RDD Section 5.
"""

from src.brains.revenue.schema import LeadQualification


# Lead routing rules from RDD
# Residential leads → Bounthon and Aubry
# Commercial leads → Junior and Bounthon
# High-value leads (>$10k) → Junior

RESIDENTIAL_ASSIGNEES = ["Bounthon", "Aubry"]
COMMERCIAL_ASSIGNEES = ["Junior", "Bounthon"]
HIGH_VALUE_THRESHOLD = 10000
HIGH_VALUE_ASSIGNEES = ["Junior"]


def route_lead(
    property_type: str | None,
    budget_range: str | None = None,
    estimated_value: float | None = None,
    qualification: LeadQualification = LeadQualification.WARM,
) -> tuple[list[str], str]:
    """
    Route a lead to the appropriate assignees.
    
    Rules from RDD:
    - Residential leads → Bounthon and Aubry
    - Commercial leads → Junior and Bounthon
    - High-value leads (>$10k) → Junior
    
    Args:
        property_type: residential or commercial
        budget_range: Budget range string
        estimated_value: Estimated deal value
        qualification: Lead qualification level
        
    Returns:
        Tuple of (list of assignees, routing reason)
    """
    # Check for high-value override
    is_high_value = False
    if estimated_value and estimated_value > HIGH_VALUE_THRESHOLD:
        is_high_value = True
    
    # Try to parse budget range for high-value check
    if budget_range and not is_high_value:
        budget_lower = budget_range.lower().replace(",", "").replace("$", "")
        try:
            # Look for numbers in budget string
            import re
            numbers = re.findall(r'\d+', budget_lower)
            if numbers:
                max_budget = max(int(n) for n in numbers)
                if max_budget > HIGH_VALUE_THRESHOLD:
                    is_high_value = True
        except (ValueError, AttributeError):
            pass
    
    # High-value routing takes precedence
    if is_high_value:
        return HIGH_VALUE_ASSIGNEES, f"High-value lead (>${HIGH_VALUE_THRESHOLD})"
    
    # Route by property type
    property_type_lower = (property_type or "").lower()
    
    if property_type_lower in ["commercial", "business", "office", "industrial"]:
        return COMMERCIAL_ASSIGNEES, "Commercial property routing"
    
    if property_type_lower in ["residential", "home", "house", "apartment", "condo"]:
        return RESIDENTIAL_ASSIGNEES, "Residential property routing"
    
    # Unknown property type - route to residential by default
    # but flag for human review
    return RESIDENTIAL_ASSIGNEES, "Default routing (property type unknown)"


def get_primary_assignee(assignees: list[str]) -> str | None:
    """
    Get the primary assignee from a list.
    
    Args:
        assignees: List of possible assignees
        
    Returns:
        Primary assignee name or None
    """
    return assignees[0] if assignees else None

