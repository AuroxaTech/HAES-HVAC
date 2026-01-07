"""
HAES HVAC - PEOPLE Brain Onboarding Catalog

Onboarding checklist items from RDD Section 6.
"""

from src.brains.people.schema import OnboardingCategory, OnboardingItem


# Onboarding checklist from RDD Section 6
ONBOARDING_CATALOG: list[OnboardingItem] = [
    # HR & Identity Verification
    OnboardingItem(
        id="id_government",
        category=OnboardingCategory.HR_IDENTITY,
        name="Government ID Verification",
        description="Valid driver's license or state ID",
        required=True,
    ),
    OnboardingItem(
        id="id_i9",
        category=OnboardingCategory.HR_IDENTITY,
        name="I-9 Form",
        description="Employment Eligibility Verification",
        required=True,
    ),
    OnboardingItem(
        id="id_ssn",
        category=OnboardingCategory.HR_IDENTITY,
        name="SSN Verification",
        description="Social Security Number verification",
        required=True,
    ),
    OnboardingItem(
        id="bg_background",
        category=OnboardingCategory.HR_IDENTITY,
        name="Background Check",
        description="Criminal background check completed",
        required=True,
    ),
    OnboardingItem(
        id="bg_drug",
        category=OnboardingCategory.HR_IDENTITY,
        name="Drug Screening",
        description="Pre-employment drug test",
        required=True,
    ),
    OnboardingItem(
        id="bg_mvr",
        category=OnboardingCategory.HR_IDENTITY,
        name="MVR Check",
        description="Motor Vehicle Record check",
        required=True,
    ),
    OnboardingItem(
        id="cert_license",
        category=OnboardingCategory.HR_IDENTITY,
        name="License Verification",
        description="HVAC license verification (if applicable)",
        required=False,
    ),
    OnboardingItem(
        id="cert_epa",
        category=OnboardingCategory.HR_IDENTITY,
        name="EPA 608 Certification",
        description="EPA Section 608 certification",
        required=True,
    ),
    OnboardingItem(
        id="cert_tdlr",
        category=OnboardingCategory.HR_IDENTITY,
        name="TDLR Registration",
        description="Texas TDLR registration",
        required=True,
    ),

    # Employment Agreements (Odoo Sign)
    OnboardingItem(
        id="agree_offer",
        category=OnboardingCategory.EMPLOYMENT_AGREEMENTS,
        name="Offer Letter",
        description="Signed offer letter via Odoo Sign",
        required=True,
    ),
    OnboardingItem(
        id="agree_handbook",
        category=OnboardingCategory.EMPLOYMENT_AGREEMENTS,
        name="Employee Handbook Acknowledgment",
        description="Signed acknowledgment of employee handbook",
        required=True,
    ),
    OnboardingItem(
        id="agree_safety",
        category=OnboardingCategory.EMPLOYMENT_AGREEMENTS,
        name="Safety Policy Acknowledgment",
        description="Signed safety policies and procedures",
        required=True,
    ),
    OnboardingItem(
        id="agree_confidentiality",
        category=OnboardingCategory.EMPLOYMENT_AGREEMENTS,
        name="Confidentiality Agreement",
        description="Non-disclosure and confidentiality agreement",
        required=True,
    ),

    # Payroll & Banking Activation
    OnboardingItem(
        id="pay_w4",
        category=OnboardingCategory.PAYROLL_BANKING,
        name="W-4 Form",
        description="Federal tax withholding form",
        required=True,
    ),
    OnboardingItem(
        id="pay_direct",
        category=OnboardingCategory.PAYROLL_BANKING,
        name="Direct Deposit Setup",
        description="Banking information for direct deposit",
        required=True,
    ),
    OnboardingItem(
        id="pay_state",
        category=OnboardingCategory.PAYROLL_BANKING,
        name="State Tax Form",
        description="State withholding form (if applicable)",
        required=False,
    ),

    # Minimum System Access
    OnboardingItem(
        id="sys_odoo",
        category=OnboardingCategory.SYSTEM_ACCESS,
        name="Odoo Account",
        description="Odoo user account created and configured",
        required=True,
    ),
    OnboardingItem(
        id="sys_email",
        category=OnboardingCategory.SYSTEM_ACCESS,
        name="Company Email",
        description="Company email address created",
        required=True,
    ),
    OnboardingItem(
        id="sys_phone",
        category=OnboardingCategory.SYSTEM_ACCESS,
        name="Company Phone",
        description="Company phone number assigned",
        required=True,
    ),
    OnboardingItem(
        id="sys_vehicle",
        category=OnboardingCategory.SYSTEM_ACCESS,
        name="Vehicle Assignment",
        description="Company vehicle assigned (if applicable)",
        required=False,
    ),
]


def get_onboarding_checklist() -> list[OnboardingItem]:
    """Get the full onboarding checklist."""
    return ONBOARDING_CATALOG.copy()


def get_onboarding_by_category(category: OnboardingCategory) -> list[OnboardingItem]:
    """Get onboarding items for a specific category."""
    return [item for item in ONBOARDING_CATALOG if item.category == category]


def get_required_onboarding_items() -> list[OnboardingItem]:
    """Get only required onboarding items."""
    return [item for item in ONBOARDING_CATALOG if item.required]


def get_onboarding_summary() -> dict:
    """Get summary of onboarding checklist."""
    by_category = {}
    for category in OnboardingCategory:
        items = get_onboarding_by_category(category)
        by_category[category.value] = {
            "count": len(items),
            "required": len([i for i in items if i.required]),
        }

    return {
        "total_items": len(ONBOARDING_CATALOG),
        "required_items": len(get_required_onboarding_items()),
        "by_category": by_category,
    }

