"""
HAES HVAC - PEOPLE Tools Tests

Tests for PEOPLE brain tools:
- hiring_inquiry
- onboarding_inquiry
- payroll_inquiry
"""

import pytest
from unittest.mock import patch, MagicMock

from src.vapi.tools.people.hiring_inquiry import handle_hiring_inquiry
from src.vapi.tools.people.onboarding_inquiry import handle_onboarding_inquiry
from src.vapi.tools.people.payroll_inquiry import handle_payroll_inquiry


class TestHiringInquiry:
    """Tests for hiring_inquiry tool."""
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.people.hiring_inquiry.handle_people_command")
    async def test_hiring_inquiry_success(self, mock_people_handler):
        """Should successfully return hiring information."""
        from src.brains.people.schema import PeopleResult, PeopleStatus
        mock_people_handler.return_value = PeopleResult(
            status=PeopleStatus.SUCCESS,
            message="Hiring requirements retrieved",
            requires_human=False,
            data={
                "hiring_requirements": {
                    "required_documents": ["EPA 608", "TDLR License"],
                    "experience_required": "2+ years",
                },
            },
        )
        
        parameters = {}
        
        response = await handle_hiring_inquiry(
            tool_call_id="tc_hiring_001",
            parameters=parameters,
            call_id="call_hiring_001",
        )
        
        assert response.action == "completed"
        assert "hiring" in response.speak.lower() or "position" in response.speak.lower()


class TestOnboardingInquiry:
    """Tests for onboarding_inquiry tool."""
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.people.onboarding_inquiry.handle_people_command")
    async def test_onboarding_inquiry_success(self, mock_people_handler):
        """Should successfully return onboarding information."""
        from src.brains.people.schema import PeopleResult, PeopleStatus
        mock_people_handler.return_value = PeopleResult(
            status=PeopleStatus.SUCCESS,
            message="Onboarding checklist retrieved",
            requires_human=False,
            data={
                "onboarding_items": [
                    {"name": "Complete W-4", "completed": False},
                    {"name": "Submit I-9", "completed": False},
                ],
            },
        )
        
        parameters = {}
        
        response = await handle_onboarding_inquiry(
            tool_call_id="tc_onboarding_001",
            parameters=parameters,
            call_id="call_onboarding_001",
        )
        
        assert response.action == "completed"
        assert "onboarding" in response.speak.lower() or "checklist" in response.speak.lower()


class TestPayrollInquiry:
    """Tests for payroll_inquiry tool."""
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.people.payroll_inquiry.handle_people_command")
    async def test_payroll_inquiry_success(self, mock_people_handler):
        """Should successfully return payroll information."""
        from src.brains.people.schema import PeopleResult, PeopleStatus
        mock_people_handler.return_value = PeopleResult(
            status=PeopleStatus.SUCCESS,
            message="Payroll information retrieved",
            requires_human=False,
            data={
                "payroll_config": {
                    "pay_period": "biweekly",
                    "commission_rules": [],
                },
            },
        )
        
        parameters = {
            "employee_email": "john@hvacrfinest.com",
        }
        
        response = await handle_payroll_inquiry(
            tool_call_id="tc_payroll_001",
            parameters=parameters,
            call_id="call_payroll_001",
        )
        
        assert response.action == "completed"
        assert "payroll" in response.speak.lower() or "commission" in response.speak.lower()
