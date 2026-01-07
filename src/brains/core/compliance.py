"""
HAES HVAC - CORE Brain Compliance

Required disclosures, license info, and warranty terms from RDD.
"""

from src.brains.core.schema import ComplianceDisclosure


# Texas TDLR license information from RDD
TDLR_LICENSE_NUMBER = "TACLA123456C"  # Placeholder - actual from RDD
TDLR_REGULATORY_BODY = "Texas Department of Licensing and Regulation (TDLR)"

# Required disclosure text from RDD
TDLR_DISCLOSURE_TEXT = (
    "Licensed and regulated by the Texas Department of Licensing and Regulation, "
    "P.O. Box 12157, Austin, Texas 78711, 1-800-803-9202, 512-463-6599, "
    "www.tdlr.texas.gov"
)

# Warranty terms from RDD Section 3
WARRANTY_TERMS = {
    "labor_repair": {
        "duration_days": 30,
        "description": "30-day labor warranty on repairs",
        "conditions": "Covers labor only on replaced parts",
    },
    "labor_equipment": {
        "duration_years": 1,
        "description": "1-year labor warranty on equipment replacement",
        "conditions": "Covers labor for equipment installed by HAES",
    },
    "manufacturer": {
        "duration_years": "varies",
        "description": "Manufacturer equipment warranty",
        "conditions": "Per manufacturer terms, typically 5-10 years on parts",
    },
}

WARRANTY_TERMS_TEXT = (
    "HAES HVAC provides a 30-day labor warranty on all repairs (covering parts replaced). "
    "Equipment replacements include a 1-year labor warranty. "
    "Manufacturer warranties on equipment parts vary by brand (typically 5-10 years). "
    "Warranty work must be scheduled through HAES to remain valid."
)


def get_required_disclosures() -> ComplianceDisclosure:
    """
    Get all required compliance disclosures.
    
    Returns:
        ComplianceDisclosure with all required information
    """
    return ComplianceDisclosure(
        license_number=TDLR_LICENSE_NUMBER,
        regulatory_body=TDLR_REGULATORY_BODY,
        disclosure_text=TDLR_DISCLOSURE_TEXT,
        warranty_terms=WARRANTY_TERMS_TEXT,
    )


def get_warranty_for_service_type(service_type: str) -> dict:
    """
    Get warranty information for a specific service type.
    
    Args:
        service_type: Type of service (repair, equipment, etc.)
        
    Returns:
        Warranty details dictionary
    """
    if "install" in service_type.lower() or "replacement" in service_type.lower():
        return WARRANTY_TERMS["labor_equipment"]
    elif "repair" in service_type.lower():
        return WARRANTY_TERMS["labor_repair"]
    else:
        return WARRANTY_TERMS["labor_repair"]


def format_invoice_disclosures() -> str:
    """
    Get formatted disclosures for invoices.
    
    Returns:
        Formatted disclosure text for invoice footer
    """
    return (
        f"License: {TDLR_LICENSE_NUMBER}\n"
        f"{TDLR_DISCLOSURE_TEXT}\n\n"
        f"Warranty: {WARRANTY_TERMS_TEXT}"
    )

