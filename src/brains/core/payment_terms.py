"""
HAES HVAC - CORE Brain Payment Terms

Payment terms and late fee rules from RDD Section 3.
"""

from src.brains.core.schema import PaymentTerms


# Payment terms by segment from RDD
PAYMENT_TERMS_BY_SEGMENT = {
    "residential": PaymentTerms(
        segment="residential",
        due_days=0,  # Due on invoice
        late_fee_percent=1.0,
        accepted_methods=["cash", "card", "check", "zelle"],
    ),
    "commercial": PaymentTerms(
        segment="commercial",
        due_days=15,
        late_fee_percent=1.0,
        accepted_methods=["check", "card", "ach", "wire"],
    ),
    "property_management": PaymentTerms(
        segment="property_management",
        due_days=30,
        late_fee_percent=1.0,
        accepted_methods=["check", "ach", "wire"],
    ),
    "national_account": PaymentTerms(
        segment="national_account",
        due_days=30,
        late_fee_percent=1.0,
        accepted_methods=["check", "ach", "wire"],
    ),
}

# Default payment terms for unknown segments
DEFAULT_PAYMENT_TERMS = PaymentTerms(
    segment="default",
    due_days=0,
    late_fee_percent=1.0,
    accepted_methods=["cash", "card", "check"],
)


def get_payment_terms(segment: str | None) -> PaymentTerms:
    """
    Get payment terms for a customer segment.
    
    Args:
        segment: Customer segment (residential, commercial, property_management, etc.)
        
    Returns:
        PaymentTerms for the segment
    """
    if not segment:
        return DEFAULT_PAYMENT_TERMS
    
    segment_lower = segment.lower().replace(" ", "_").replace("-", "_")
    return PAYMENT_TERMS_BY_SEGMENT.get(segment_lower, DEFAULT_PAYMENT_TERMS)


def calculate_late_fee(
    invoice_amount: float,
    days_overdue: int,
    segment: str | None = None,
) -> float:
    """
    Calculate late fee for an overdue invoice.
    
    From RDD: 1% late fee
    
    Args:
        invoice_amount: Original invoice amount
        days_overdue: Number of days past due
        segment: Customer segment
        
    Returns:
        Late fee amount
    """
    if days_overdue <= 0:
        return 0.0
    
    terms = get_payment_terms(segment)
    
    # 1% per period (monthly)
    periods = (days_overdue + 29) // 30  # Round up to nearest month
    fee_rate = terms.late_fee_percent / 100
    
    return invoice_amount * fee_rate * periods


def format_payment_terms_text(segment: str | None) -> str:
    """
    Format payment terms for customer communication.
    
    Args:
        segment: Customer segment
        
    Returns:
        Human-readable payment terms
    """
    terms = get_payment_terms(segment)
    
    if terms.due_days == 0:
        due_text = "Due upon receipt"
    else:
        due_text = f"Net {terms.due_days} days"
    
    methods_text = ", ".join(terms.accepted_methods)
    
    return (
        f"Payment Terms: {due_text}\n"
        f"Late Fee: {terms.late_fee_percent}% per month after due date\n"
        f"Accepted Methods: {methods_text}"
    )

