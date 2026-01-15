"""
HAES HVAC - REVENUE Tools Tests

Tests for REVENUE brain tools:
- request_quote
- check_lead_status
- request_membership_enrollment
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.vapi.tools.revenue.request_quote import handle_request_quote
from src.vapi.tools.revenue.check_lead_status import handle_check_lead_status
from src.vapi.tools.revenue.request_membership_enrollment import handle_request_membership_enrollment


class TestRequestQuote:
    """Tests for request_quote tool."""
    
    @pytest.mark.asyncio
    async def test_request_quote_requires_customer_name(self):
        """Should require customer name."""
        parameters = {
            "phone": "+19725551234",
            "address": "123 Main St, Dallas, TX 75201",
            "property_type": "residential",
            "timeline": "within 2 weeks",
        }
        
        response = await handle_request_quote(
            tool_call_id="tc_quote_001",
            parameters=parameters,
            call_id="call_quote_001",
        )
        
        assert response.action == "needs_human"
        assert "customer_name" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.integrations.odoo_leads.create_lead_service")
    @patch("src.integrations.odoo_quotes.create_quote_service")
    @patch("src.vapi.tools.revenue.request_quote.handle_revenue_command")
    async def test_request_quote_success(self, mock_revenue_handler, mock_quote_service, mock_lead_service):
        """Should successfully create quote request."""
        # Mock REVENUE handler
        from src.brains.revenue.schema import RevenueResult, RevenueStatus, LeadQualification
        mock_revenue_handler.return_value = RevenueResult(
            status=RevenueStatus.SUCCESS,
            message="Quote request captured - HOT lead",
            requires_human=False,
            qualification=LeadQualification.HOT,
            data={
                "quote_data": {
                    "needs_quote_creation": True,
                }
            }
        )
        
        # Mock lead creation (create_lead_service is async and returns a service instance)
        mock_lead_service_instance = AsyncMock()
        mock_lead_service.return_value = mock_lead_service_instance
        mock_lead_service_instance.upsert_service_lead = AsyncMock(return_value={
            "lead_id": 5001,
            "action": "created",
            "status": "success",
        })
        
        # Mock quote creation (create_quote_service is async and returns a service instance)
        mock_quote_service_instance = AsyncMock()
        mock_quote_service.return_value = mock_quote_service_instance
        mock_quote_service_instance.create_quote = AsyncMock(return_value={
            "quote_id": 6001,
            "quote_total": 7500.0,
            "quote_status": "draft",
            "requires_approval": False,
        })
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
            "address": "123 Main St, Dallas, TX 75201",
            "property_type": "residential",
            "timeline": "within 2 weeks",
            "square_footage": 2000,
            "system_type": "complete_split_system",
        }
        
        response = await handle_request_quote(
            tool_call_id="tc_quote_002",
            parameters=parameters,
            call_id="call_quote_002",
        )
        
        assert response.action == "completed"
        assert response.data.get("lead_id") is not None
        assert response.data.get("quote_id") is not None
        assert "financing" in response.speak.lower() or "quote" in response.speak.lower()
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.revenue.request_quote.handle_revenue_command")
    async def test_request_quote_includes_financing_options(self, mock_revenue_handler):
        """Should include financing options in response."""
        from src.brains.revenue.schema import RevenueResult, RevenueStatus
        mock_revenue_handler.return_value = RevenueResult(
            status=RevenueStatus.SUCCESS,
            message="Quote request captured",
            requires_human=False,
        )
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
            "address": "123 Main St, Dallas, TX 75201",
            "property_type": "residential",
            "timeline": "within 2 weeks",
        }
        
        response = await handle_request_quote(
            tool_call_id="tc_quote_003",
            parameters=parameters,
            call_id="call_quote_003",
        )
        
        assert response.action == "completed"
        assert response.data.get("financing_options") is not None
        assert response.data["financing_options"]["available"] is True
        assert len(response.data["financing_options"]["partners"]) > 0


class TestCheckLeadStatus:
    """Tests for check_lead_status tool."""
    
    @pytest.mark.asyncio
    async def test_check_lead_status_requires_phone_or_email(self):
        """Should require phone or email."""
        parameters = {}
        
        response = await handle_check_lead_status(
            tool_call_id="tc_lead_status_001",
            parameters=parameters,
            call_id="call_lead_status_001",
        )
        
        assert response.action == "needs_human"
        assert "phone" in response.data.get("missing_fields", []) or "email" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.revenue.check_lead_status.create_odoo_client_from_settings")
    async def test_check_lead_status_success(self, mock_create_odoo_client):
        """Should successfully find lead status."""
        # Mock Odoo client
        mock_client = AsyncMock()
        mock_create_odoo_client.return_value = mock_client
        mock_client.is_authenticated = False
        mock_client.authenticate.return_value = None
        
        mock_lead = {
            "id": 7001,
            "name": "Service Request - Test",
            "stage_id": [1, "Qualified"],
            "probability": 50.0,
            "expected_revenue": 8000.0,
        }
        mock_client.search_read.return_value = [mock_lead]
        
        parameters = {
            "phone": "+19725551234",
        }
        
        response = await handle_check_lead_status(
            tool_call_id="tc_lead_status_002",
            parameters=parameters,
            call_id="call_lead_status_002",
        )
        
        assert response.action == "completed"
        assert "lead" in response.speak.lower() or "status" in response.speak.lower() or "quote" in response.speak.lower() or "stage" in response.speak.lower()
        assert response.data.get("lead_id") is not None or response.data.get("leads") is not None or response.data.get("lead") is not None


class TestRequestMembershipEnrollment:
    """Tests for request_membership_enrollment tool."""
    
    @pytest.mark.asyncio
    async def test_request_membership_enrollment_requires_customer_name(self):
        """Should require customer name."""
        parameters = {
            "phone": "+19725551234",
            "membership_type": "basic",
        }
        
        response = await handle_request_membership_enrollment(
            tool_call_id="tc_membership_001",
            parameters=parameters,
            call_id="call_membership_001",
        )
        
        assert response.action == "needs_human"
        assert "customer_name" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.integrations.odoo_leads.create_lead_service")
    @patch("src.integrations.twilio_sms.create_twilio_client_from_settings")
    @patch("src.integrations.email_notifications.create_email_service_from_settings")
    @patch("src.vapi.tools.revenue.request_membership_enrollment.handle_revenue_command")
    async def test_request_membership_enrollment_success(self, mock_revenue_handler, mock_email_service, mock_sms_client, mock_lead_service):
        """Should successfully create membership enrollment."""
        # Mock REVENUE handler
        from src.brains.revenue.schema import RevenueResult, RevenueStatus, LeadQualification
        mock_revenue_handler.return_value = RevenueResult(
            status=RevenueStatus.SUCCESS,
            message="Membership enrollment captured",
            requires_human=False,
            qualification=LeadQualification.WARM,
        )
        
        # Mock lead creation (create_lead_service is async and returns a service instance)
        mock_lead_service_instance = AsyncMock()
        mock_lead_service.return_value = mock_lead_service_instance
        mock_lead_service_instance.upsert_service_lead = AsyncMock(return_value={
            "lead_id": 8001,
            "action": "created",
            "status": "success",
        })
        
        # Mock SMS client
        mock_sms_instance = AsyncMock()
        mock_sms_client.return_value = mock_sms_instance
        mock_sms_instance.send_sms.return_value = {"status": "sent", "message_sid": "SM123"}
        
        # Mock email service
        mock_email_instance = MagicMock()
        mock_email_service.return_value = mock_email_instance
        mock_email_instance.send_email.return_value = {"status": "sent"}
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
            "email": "john@example.com",
            "address": "123 Main St, Dallas, TX 75201",
            "property_type": "residential",
            "membership_type": "basic",
        }
        
        response = await handle_request_membership_enrollment(
            tool_call_id="tc_membership_002",
            parameters=parameters,
            call_id="call_membership_002",
        )
        
        assert response.action == "completed"
        assert response.data.get("lead_id") is not None
        assert "membership" in response.speak.lower() or "enrollment" in response.speak.lower()
        assert "VIP" in response.speak or "benefits" in response.speak.lower()
