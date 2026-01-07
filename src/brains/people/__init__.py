"""
HAES HVAC - PEOPLE Brain

Handles HR, onboarding, training, and payroll rules.
"""

from src.brains.people.handlers import handle_people_command
from src.brains.people.schema import PeopleResult, PeopleStatus
from src.brains.people.hiring_policy import get_hiring_requirements
from src.brains.people.onboarding_catalog import get_onboarding_checklist
from src.brains.people.training_catalog import get_training_program
from src.brains.people.payroll_rules import calculate_commission

__all__ = [
    "handle_people_command",
    "PeopleResult",
    "PeopleStatus",
    "get_hiring_requirements",
    "get_onboarding_checklist",
    "get_training_program",
    "calculate_commission",
]

