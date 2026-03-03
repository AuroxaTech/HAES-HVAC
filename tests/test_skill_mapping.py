"""
Tests for skill_mapping: required skills and technician filtering.
"""

import pytest

from src.brains.ops.skill_mapping import (
    get_required_skills_for_service,
    technician_has_required_skills,
    filter_technicians_by_skills,
)
from src.brains.ops.service_catalog import (
    SERVICE_CATALOG,
    infer_service_type_from_description,
)


class TestGetRequiredSkillsForService:
    """Tests for get_required_skills_for_service."""

    def test_returns_skills_for_diagnostic(self):
        st = SERVICE_CATALOG["diag_residential"]
        skills = get_required_skills_for_service(st, None)
        assert "Electrical Diagnostics" in skills
        assert "Low Voltage Troubleshooting" in skills

    def test_adds_heat_pump_from_description(self):
        st = SERVICE_CATALOG["repair_minor"]
        skills = get_required_skills_for_service(st, "heat pump not working")
        assert "Heat Pump" in skills
        assert "Electrical Diagnostics" in skills


class TestTechnicianHasRequiredSkills:
    """Tests for technician_has_required_skills."""

    def test_empty_required_returns_true(self):
        assert technician_has_required_skills([], []) is True
        assert technician_has_required_skills(
            [{"skill_name": "Electrical Diagnostics"}], []
        ) is True

    def test_has_all_returns_true(self):
        skill_list = [
            {"skill_name": "Electrical Diagnostics"},
            {"skill_name": "Low Voltage Troubleshooting"},
        ]
        assert technician_has_required_skills(
            skill_list, ["Electrical Diagnostics", "Low Voltage Troubleshooting"]
        ) is True

    def test_missing_one_returns_false(self):
        skill_list = [{"skill_name": "Electrical Diagnostics"}]
        assert technician_has_required_skills(
            skill_list, ["Electrical Diagnostics", "Low Voltage Troubleshooting"]
        ) is False

    def test_case_insensitive(self):
        skill_list = [{"skill_name": "electrical diagnostics"}]
        assert technician_has_required_skills(
            skill_list, ["Electrical Diagnostics"]
        ) is True


class TestFilterTechniciansBySkills:
    """Tests for filter_technicians_by_skills."""

    def test_empty_required_returns_all(self):
        techs = [{"id": 1, "employee_id": 10}, {"id": 2, "employee_id": 20}]
        result = filter_technicians_by_skills(techs, {}, [])
        assert len(result) == 2

    def test_filters_to_matching_only(self):
        techs = [
            {"id": 1, "employee_id": 10},
            {"id": 2, "employee_id": 20},
        ]
        skills_by_emp = {
            10: [{"skill_name": "Electrical Diagnostics"}, {"skill_name": "Low Voltage Troubleshooting"}],
            20: [{"skill_name": "Electrical Diagnostics"}],
        }
        result = filter_technicians_by_skills(
            techs, skills_by_emp, ["Electrical Diagnostics", "Low Voltage Troubleshooting"]
        )
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_skips_tech_without_employee_id_when_required_skills(self):
        techs = [{"id": 1, "employee_id": None}, {"id": 2, "employee_id": 20}]
        skills_by_emp = {
            20: [{"skill_name": "Electrical Diagnostics"}, {"skill_name": "Low Voltage Troubleshooting"}],
        }
        result = filter_technicians_by_skills(
            techs, skills_by_emp, ["Electrical Diagnostics"]
        )
        assert len(result) == 1
        assert result[0]["id"] == 2
