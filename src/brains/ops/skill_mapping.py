"""
HAES HVAC - OPS Skill Mapping

Maps service types and job descriptions to required technician skills.
Used by check_availability and schedule flow to filter technicians by skill.
Skill names must match Odoo HR Skills (e.g. Electrical Diagnostics, Heat Pump).
"""

from typing import Any

from src.brains.ops.service_catalog import ServiceType, infer_service_type_from_description

# Service type code -> list of required skill names (match Odoo skill names)
SERVICE_TYPE_REQUIRED_SKILLS: dict[str, list[str]] = {
    "diag_residential": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "diag_commercial": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "repair_minor": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "repair_major": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "pm_residential": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "pm_commercial": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "install_equipment": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "install_system": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
    "emergency_service": ["Electrical Diagnostics", "Low Voltage Troubleshooting"],
}

# Description keywords -> extra required skills (e.g. equipment type)
DESCRIPTION_SKILL_HINTS: list[tuple[list[str], list[str]]] = [
    (["heat pump", "heatpump"], ["Heat Pump"]),
    (["heat pump repair", "heat pump diagnostic"], ["Heat Pump", "Electrical Diagnostics"]),
]


def get_required_skills_for_service(
    service_type: ServiceType,
    description: str | None = None,
) -> list[str]:
    """
    Return required skill names for a service type and optional description.

    Skill names match Odoo (e.g. "Electrical Diagnostics", "Heat Pump").
    If description contains hints (e.g. "heat pump"), extra skills are added.
    """
    skills: list[str] = list(
        SERVICE_TYPE_REQUIRED_SKILLS.get(service_type.code, [])
    )
    desc = (description or "").strip().lower()
    if not desc:
        return skills
    for keywords, extra_skills in DESCRIPTION_SKILL_HINTS:
        if any(kw in desc for kw in keywords):
            for s in extra_skills:
                if s not in skills:
                    skills.append(s)
    return skills


def technician_has_required_skills(
    skill_list: list[dict[str, Any]],
    required_skills: list[str],
) -> bool:
    """
    Return True if technician's skill_list contains all required_skills.

    Match is case-insensitive on skill_name. required_skills empty -> True.
    """
    if not required_skills:
        return True
    tech_skill_names = {
        str(s.get("skill_name") or "").strip().lower()
        for s in (skill_list or [])
        if s.get("skill_name")
    }
    for req in required_skills:
        if not req or not req.strip():
            continue
        if req.strip().lower() not in tech_skill_names:
            return False
    return True


def filter_technicians_by_skills(
    technicians: list[dict[str, Any]],
    skills_by_employee_id: dict[int, list[dict[str, Any]]],
    required_skills: list[str],
) -> list[dict[str, Any]]:
    """
    Return technicians who have all required_skills.

    technicians: list of dicts with "id" (user_id) and "employee_id".
    skills_by_employee_id: from get_technician_skills().
    If required_skills is empty, returns all technicians unchanged.
    """
    if not required_skills:
        return technicians
    filtered = []
    for tech in technicians:
        emp_id = tech.get("employee_id")
        if emp_id is None:
            continue
        if isinstance(emp_id, list) and emp_id:
            emp_id = emp_id[0]
        skill_list = skills_by_employee_id.get(int(emp_id), [])
        if technician_has_required_skills(skill_list, required_skills):
            filtered.append(tech)
    return filtered
