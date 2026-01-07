"""
HAES HVAC - OPS Brain Service Catalog

Service types, durations, and priorities from RDD.
"""

from dataclasses import dataclass
from enum import Enum


class ServiceCategory(str, Enum):
    """Service category classification."""
    DIAGNOSTIC = "diagnostic"
    REPAIR = "repair"
    MAINTENANCE = "maintenance"
    INSTALLATION = "installation"
    EMERGENCY = "emergency"


@dataclass
class ServiceType:
    """Service type definition."""
    code: str
    name: str
    category: ServiceCategory
    duration_minutes_min: int
    duration_minutes_max: int
    priority_default: int  # 1 = highest, 5 = lowest


# Service catalog from RDD Section 4
SERVICE_CATALOG: dict[str, ServiceType] = {
    # Diagnostic/Assessment
    "diag_residential": ServiceType(
        code="diag_residential",
        name="Residential Diagnostic",
        category=ServiceCategory.DIAGNOSTIC,
        duration_minutes_min=45,
        duration_minutes_max=90,
        priority_default=3,
    ),
    "diag_commercial": ServiceType(
        code="diag_commercial",
        name="Commercial Diagnostic",
        category=ServiceCategory.DIAGNOSTIC,
        duration_minutes_min=60,
        duration_minutes_max=120,
        priority_default=3,
    ),
    
    # Repairs
    "repair_minor": ServiceType(
        code="repair_minor",
        name="Minor Repair",
        category=ServiceCategory.REPAIR,
        duration_minutes_min=60,
        duration_minutes_max=120,
        priority_default=3,
    ),
    "repair_major": ServiceType(
        code="repair_major",
        name="Major Repair",
        category=ServiceCategory.REPAIR,
        duration_minutes_min=120,
        duration_minutes_max=240,
        priority_default=2,
    ),
    
    # Maintenance
    "pm_residential": ServiceType(
        code="pm_residential",
        name="Residential Preventive Maintenance",
        category=ServiceCategory.MAINTENANCE,
        duration_minutes_min=45,
        duration_minutes_max=90,
        priority_default=4,
    ),
    "pm_commercial": ServiceType(
        code="pm_commercial",
        name="Commercial Preventive Maintenance",
        category=ServiceCategory.MAINTENANCE,
        duration_minutes_min=60,
        duration_minutes_max=180,
        priority_default=4,
    ),
    
    # Installation
    "install_equipment": ServiceType(
        code="install_equipment",
        name="Equipment Installation",
        category=ServiceCategory.INSTALLATION,
        duration_minutes_min=240,
        duration_minutes_max=480,
        priority_default=3,
    ),
    "install_system": ServiceType(
        code="install_system",
        name="Full System Installation",
        category=ServiceCategory.INSTALLATION,
        duration_minutes_min=480,
        duration_minutes_max=960,
        priority_default=3,
    ),
    
    # Emergency
    "emergency_service": ServiceType(
        code="emergency_service",
        name="Emergency Service Call",
        category=ServiceCategory.EMERGENCY,
        duration_minutes_min=60,
        duration_minutes_max=180,
        priority_default=1,
    ),
}


def get_service_type(code: str) -> ServiceType | None:
    """Get service type by code."""
    return SERVICE_CATALOG.get(code)


def get_default_service_type(category: ServiceCategory) -> ServiceType:
    """Get default service type for a category."""
    defaults = {
        ServiceCategory.DIAGNOSTIC: SERVICE_CATALOG["diag_residential"],
        ServiceCategory.REPAIR: SERVICE_CATALOG["repair_minor"],
        ServiceCategory.MAINTENANCE: SERVICE_CATALOG["pm_residential"],
        ServiceCategory.INSTALLATION: SERVICE_CATALOG["install_equipment"],
        ServiceCategory.EMERGENCY: SERVICE_CATALOG["emergency_service"],
    }
    return defaults.get(category, SERVICE_CATALOG["diag_residential"])


def infer_service_type_from_description(description: str) -> ServiceType:
    """
    Infer service type from problem description.
    
    Simple keyword-based inference for MVP.
    """
    desc_lower = description.lower()
    
    # Emergency keywords
    if any(kw in desc_lower for kw in ["emergency", "gas leak", "no heat", "no cooling", "urgent"]):
        return SERVICE_CATALOG["emergency_service"]
    
    # Installation keywords
    if any(kw in desc_lower for kw in ["install", "new system", "replacement", "new unit"]):
        return SERVICE_CATALOG["install_equipment"]
    
    # Maintenance keywords
    if any(kw in desc_lower for kw in ["maintenance", "tune-up", "check-up", "annual", "pm"]):
        return SERVICE_CATALOG["pm_residential"]
    
    # Major repair keywords
    if any(kw in desc_lower for kw in ["compressor", "condenser", "coil", "major"]):
        return SERVICE_CATALOG["repair_major"]
    
    # Minor repair
    if any(kw in desc_lower for kw in ["repair", "fix", "broken", "not working"]):
        return SERVICE_CATALOG["repair_minor"]
    
    # Default to diagnostic
    return SERVICE_CATALOG["diag_residential"]

