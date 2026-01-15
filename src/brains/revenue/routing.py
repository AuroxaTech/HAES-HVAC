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
    Route a lead to the appropriate assignees based on qualification and property type.
    
    Rules from RDD (Test 5.3):
    - Hot leads → Senior tech/sales immediately (Junior)
    - Warm leads → Standard production, follow-up automation (based on property type)
    - Cold leads → Nurture drip, review building (standard assignment but trigger nurture automation)
    
    Additional rules:
    - Residential leads → Bounthon and Aubry (warm/cold)
    - Commercial leads → Junior and Bounthon (warm/cold)
    - High-value leads (>$10k) → Junior (overrides qualification)
    
    Args:
        property_type: residential or commercial
        budget_range: Budget range string
        estimated_value: Estimated deal value
        qualification: Lead qualification level (HOT, WARM, COLD)
        
    Returns:
        Tuple of (list of assignees, routing reason)
    """
    # Check for high-value override (highest priority)
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
    
    # High-value routing takes precedence (overrides qualification)
    if is_high_value:
        return HIGH_VALUE_ASSIGNEES, f"High-value lead (>${HIGH_VALUE_THRESHOLD}) - immediate assignment"
    
    # HOT leads → Senior tech/sales immediately (Junior)
    if qualification == LeadQualification.HOT:
        return ["Junior"], "Hot lead - immediate assignment to senior tech/sales"
    
    # WARM leads → Standard production, follow-up automation (route by property type)
    if qualification == LeadQualification.WARM:
        property_type_lower = (property_type or "").lower()
        
        if property_type_lower in ["commercial", "business", "office", "industrial"]:
            return COMMERCIAL_ASSIGNEES, "Warm commercial lead - standard production routing"
        
        if property_type_lower in ["residential", "home", "house", "apartment", "condo"]:
            return RESIDENTIAL_ASSIGNEES, "Warm residential lead - standard production routing"
        
        # Unknown property type - route to residential by default
        return RESIDENTIAL_ASSIGNEES, "Warm lead - default routing (property type unknown)"
    
    # COLD leads → Nurture drip (route by property type but will trigger nurture automation)
    if qualification == LeadQualification.COLD:
        property_type_lower = (property_type or "").lower()
        
        if property_type_lower in ["commercial", "business", "office", "industrial"]:
            return COMMERCIAL_ASSIGNEES, "Cold commercial lead - nurture drip routing"
        
        if property_type_lower in ["residential", "home", "house", "apartment", "condo"]:
            return RESIDENTIAL_ASSIGNEES, "Cold residential lead - nurture drip routing"
        
        # Unknown property type - route to residential by default
        return RESIDENTIAL_ASSIGNEES, "Cold lead - default routing (property type unknown)"
    
    # Fallback: Route by property type (if qualification not provided or unknown)
    property_type_lower = (property_type or "").lower()
    
    if property_type_lower in ["commercial", "business", "office", "industrial"]:
        return COMMERCIAL_ASSIGNEES, "Commercial property routing (qualification unknown)"
    
    if property_type_lower in ["residential", "home", "house", "apartment", "condo"]:
        return RESIDENTIAL_ASSIGNEES, "Residential property routing (qualification unknown)"
    
    # Unknown property type - route to residential by default
    return RESIDENTIAL_ASSIGNEES, "Default routing (property type and qualification unknown)"


def get_primary_assignee(assignees: list[str]) -> str | None:
    """
    Get the primary assignee from a list.
    
    Args:
        assignees: List of possible assignees
        
    Returns:
        Primary assignee name or None
    """
    return assignees[0] if assignees else None

