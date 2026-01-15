"""
HAES HVAC - Utility Tools Tests

Tests for utility tools:
- check_business_hours
- get_service_area_info
- get_maintenance_plans
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.vapi.tools.utils.check_business_hours import handle_check_business_hours
from src.vapi.tools.utils.get_service_area_info import handle_get_service_area_info
from src.vapi.tools.utils.get_maintenance_plans import handle_get_maintenance_plans


class TestCheckBusinessHours:
    """Tests for check_business_hours tool."""
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.utils.check_business_hours.is_business_hours")
    async def test_check_business_hours_during_business_hours(self, mock_is_business_hours):
        """Should return business hours status during business hours."""
        mock_is_business_hours.return_value = True
        
        parameters = {}
        
        response = await handle_check_business_hours(
            tool_call_id="tc_business_hours_001",
            parameters=parameters,
            call_id="call_business_hours_001",
        )
        
        assert response.action == "completed"
        assert response.data.get("is_business_hours") is True
        assert "open" in response.speak.lower() or "business hours" in response.speak.lower()
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.utils.check_business_hours.is_business_hours")
    async def test_check_business_hours_after_hours(self, mock_is_business_hours):
        """Should return after-hours status."""
        mock_is_business_hours.return_value = False
        
        parameters = {}
        
        response = await handle_check_business_hours(
            tool_call_id="tc_business_hours_002",
            parameters=parameters,
            call_id="call_business_hours_002",
        )
        
        assert response.action == "completed"
        assert response.data.get("is_business_hours") is False
        assert "closed" in response.speak.lower() or "after hours" in response.speak.lower()


class TestGetServiceAreaInfo:
    """Tests for get_service_area_info tool."""
    
    @pytest.mark.asyncio
    async def test_get_service_area_info_success(self):
        """Should successfully return service area information."""
        parameters = {}
        
        response = await handle_get_service_area_info(
            tool_call_id="tc_service_area_001",
            parameters=parameters,
            call_id="call_service_area_001",
        )
        
        assert response.action == "completed"
        assert "service" in response.speak.lower() or "miles" in response.speak.lower() or "dallas" in response.speak.lower()
        assert response.data.get("service_radius_miles") is not None or response.data.get("service_area") is not None


class TestGetMaintenancePlans:
    """Tests for get_maintenance_plans tool."""
    
    @pytest.mark.asyncio
    async def test_get_maintenance_plans_success(self):
        """Should successfully return maintenance plan information."""
        parameters = {}
        
        response = await handle_get_maintenance_plans(
            tool_call_id="tc_maintenance_plans_001",
            parameters=parameters,
            call_id="call_maintenance_plans_001",
        )
        
        assert response.action == "completed"
        assert "maintenance" in response.speak.lower() or "plan" in response.speak.lower()
        # Tool returns single plan info, not array
        assert response.data.get("plan_name") is not None or response.data.get("maintenance_plans") is not None
        assert response.data.get("annual_price") is not None or (response.data.get("maintenance_plans") and len(response.data["maintenance_plans"]) > 0)
        
        # If plans array exists, check for basic and commercial
        if response.data.get("maintenance_plans"):
            plan_names = [plan["name"].lower() for plan in response.data["maintenance_plans"]]
            assert any("basic" in name for name in plan_names)
            assert any("commercial" in name for name in plan_names)
