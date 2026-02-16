"""
Helpers for managed-account pricing disclosure rules.

Certain property management/commercial accounts should not receive pricing
disclosure from the voice agent during intake/scheduling.
"""

from __future__ import annotations

import re
from typing import Iterable


def _normalize(value: str) -> str:
    """Normalize free-text company input for fuzzy matching."""
    lowered = value.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


# Canonical company names and common spoken/typed aliases.
NO_PRICING_ACCOUNT_ALIASES: dict[str, list[str]] = {
    "Lessen": ["lessen"],
    "Invitation Homes": ["invitation homes", "invitation home"],
    "BridgeHomes": ["bridgehomes", "bridge homes"],
    "Home Partners of America": ["home partners of america", "home partners"],
    "Pathlight": ["pathlight", "path light"],
    "Second Avenue": ["second avenue", "2nd avenue", "second ave"],
    "Tricon": ["tricon", "tricon residential"],
    "AEG Vision": ["aeg vision", "aeg"],
    "Darwin Homes Inc": ["darwin homes inc", "darwin homes"],
    "Divvy Homes": ["divvy homes", "divvy"],
    "JFC North America": ["jfc north america", "jfc"],
    "JPMC": ["jpmc", "jp morgan", "jp morgan chase", "jpmorgan", "chase bank", "chase"],
    "MCR Hotels": ["mcr hotels", "mcr hotel", "mcr"],
    "Hilton Hotel": ["hilton hotel", "hilton hotels", "hilton"],
    "Marriott": ["marriott", "marriot"],
    "Fairfield Hotel": ["fairfield hotel", "fairfield", "fairfield inn"],
    "My Community Homes": ["my community homes", "community homes"],
    "RENU Management": ["renu management", "renu"],
    "RentRedi Inc": ["rentredi inc", "rentredi", "rent redi"],
    "Sylvan Road": ["sylvan road", "sylvan"],
    "Progress Residential": ["progress residential", "progress"],
    "Safety First Services (SFS)": ["safety first services", "sfs", "safety first"],
    "Jollibee": ["jollibee", "jollibee foods"],
}


def _contains_alias(normalized_name: str, aliases: Iterable[str]) -> bool:
    for alias in aliases:
        normalized_alias = _normalize(alias)
        if not normalized_alias:
            continue
        if normalized_alias in normalized_name or normalized_name in normalized_alias:
            return True
    return False


def classify_no_pricing_account(company_name: str | None) -> tuple[bool, str | None]:
    """
    Return (is_no_pricing_account, matched_canonical_name).
    """
    if not company_name:
        return False, None

    normalized_name = _normalize(company_name)
    if not normalized_name:
        return False, None

    for canonical, aliases in NO_PRICING_ACCOUNT_ALIASES.items():
        if _contains_alias(normalized_name, aliases):
            return True, canonical

    return False, None


def normalize_caller_type(value: str | None) -> str | None:
    """
    Normalize caller type into one of:
    - homeowner
    - tenant
    - property_management
    - business
    """
    if not value:
        return None

    v = _normalize(value)
    if v in {"homeowner", "home owner", "owner"}:
        return "homeowner"
    if v in {"renting", "renter", "tenant"}:
        return "tenant"
    if v in {"property management", "property manager", "pm", "management"}:
        return "property_management"
    if v in {"business", "commercial", "company"}:
        return "business"
    return value.strip().lower()
