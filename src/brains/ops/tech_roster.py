"""
HAES HVAC - OPS Brain Technician Roster

Technician roster and scheduling rules from RDD.
"""

from dataclasses import dataclass, field
from enum import Enum


class SkillLevel(str, Enum):
    """Technician skill level."""
    APPRENTICE = "apprentice"
    JOURNEYMAN = "journeyman"
    SENIOR = "senior"
    MASTER = "master"


class Certification(str, Enum):
    """Technician certifications."""
    EPA_608 = "epa_608"
    NATE = "nate"
    TDLR = "tdlr"
    OSHA_10 = "osha_10"
    COMMERCIAL = "commercial"


@dataclass
class Technician:
    """Technician profile."""
    id: str
    name: str
    phone: str
    email: str
    skill_level: SkillLevel
    certifications: list[Certification] = field(default_factory=list)
    service_areas: list[str] = field(default_factory=list)  # ZIP code prefixes
    can_handle_emergency: bool = True
    can_handle_commercial: bool = False
    daily_capacity_hours: float = 8.0


# Technician roster from RDD Section 4
TECHNICIAN_ROSTER: dict[str, Technician] = {
    "bounthon": Technician(
        id="bounthon",
        name="Bounthon",
        phone="512-555-0001",
        email="bounthon@haes.com",
        skill_level=SkillLevel.MASTER,
        certifications=[
            Certification.EPA_608,
            Certification.NATE,
            Certification.TDLR,
            Certification.OSHA_10,
            Certification.COMMERCIAL,
        ],
        service_areas=["787", "786", "785", "752", "750", "751"],  # Austin + Dallas area
        can_handle_emergency=True,
        can_handle_commercial=True,
    ),
    "junior": Technician(
        id="junior",
        name="Junior",
        phone="512-555-0002",
        email="junior@haes.com",
        skill_level=SkillLevel.MASTER,
        certifications=[
            Certification.EPA_608,
            Certification.NATE,
            Certification.TDLR,
            Certification.COMMERCIAL,
        ],
        service_areas=["787", "786", "785"],
        can_handle_emergency=True,
        can_handle_commercial=True,
    ),
    "aubry": Technician(
        id="aubry",
        name="Aubry",
        phone="512-555-0003",
        email="aubry@haes.com",
        skill_level=SkillLevel.SENIOR,
        certifications=[
            Certification.EPA_608,
            Certification.TDLR,
        ],
        service_areas=["787", "786"],
        can_handle_emergency=True,
        can_handle_commercial=False,
    ),
}


def get_technician(tech_id: str) -> Technician | None:
    """Get technician by ID."""
    return TECHNICIAN_ROSTER.get(tech_id.lower())


def get_available_technicians(
    zip_code: str | None = None,
    is_emergency: bool = False,
    is_commercial: bool = False,
) -> list[Technician]:
    """
    Get technicians available for a job.
    
    Args:
        zip_code: Service area ZIP code
        is_emergency: Whether this is an emergency call
        is_commercial: Whether this is a commercial job
        
    Returns:
        List of matching technicians, sorted by skill level
    """
    available = []
    
    for tech in TECHNICIAN_ROSTER.values():
        # Check emergency capability
        if is_emergency and not tech.can_handle_emergency:
            continue
        
        # Check commercial capability
        if is_commercial and not tech.can_handle_commercial:
            continue
        
        # Check service area if ZIP provided
        if zip_code:
            zip_prefix = zip_code[:3]
            if zip_prefix not in tech.service_areas:
                continue
        
        available.append(tech)
    
    # Sort by skill level (master first)
    skill_order = {
        SkillLevel.MASTER: 0,
        SkillLevel.SENIOR: 1,
        SkillLevel.JOURNEYMAN: 2,
        SkillLevel.APPRENTICE: 3,
    }
    available.sort(key=lambda t: skill_order.get(t.skill_level, 99))
    
    return available


def assign_technician(
    zip_code: str | None = None,
    is_emergency: bool = False,
    is_commercial: bool = False,
    preferred_tech_id: str | None = None,
) -> Technician | None:
    """
    Assign a technician to a job.
    
    Priority:
    1. Preferred tech if specified and available
    2. First available tech matching criteria
    3. None if no match (requires human)
    
    Args:
        zip_code: Service location ZIP code
        is_emergency: Emergency job flag
        is_commercial: Commercial job flag
        preferred_tech_id: Preferred technician ID
        
    Returns:
        Assigned technician or None
    """
    # Check preferred tech first
    if preferred_tech_id:
        tech = get_technician(preferred_tech_id)
        if tech:
            # Verify capabilities
            if is_emergency and not tech.can_handle_emergency:
                pass  # Fall through to other options
            elif is_commercial and not tech.can_handle_commercial:
                pass
            else:
                return tech
    
    # Get available technicians
    available = get_available_technicians(
        zip_code=zip_code,
        is_emergency=is_emergency,
        is_commercial=is_commercial,
    )
    
    if available:
        return available[0]
    
    return None

