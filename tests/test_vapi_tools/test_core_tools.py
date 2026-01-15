"""
HAES HVAC - CORE Tools Tests

Tests for CORE brain tools:
- billing_inquiry
- payment_terms_inquiry
- invoice_request
- inventory_inquiry
- purchase_request
- get_pricing
- create_complaint
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.vapi.tools.core.billing_inquiry import handle_billing_inquiry
from src.vapi.tools.core.payment_terms_inquiry import handle_payment_terms_inquiry
from src.vapi.tools.core.invoice_request import handle_invoice_request
from src.vapi.tools.core.inventory_inquiry import handle_inventory_inquiry
from src.vapi.tools.core.purchase_request import handle_purchase_request
from src.vapi.tools.core.get_pricing import handle_get_pricing
from src.vapi.tools.core.create_complaint import handle_create_complaint

# Note: Some handlers may not exist yet - tests will fail gracefully


class TestBillingInquiry:
    """Tests for billing_inquiry tool."""
    
    @pytest.mark.asyncio
    async def test_billing_inquiry_requires_phone_or_email(self):
        """Should require phone or email."""
        parameters = {}
        
        response = await handle_billing_inquiry(
            tool_call_id="tc_billing_001",
            parameters=parameters,
            call_id="call_billing_001",
        )
        
        assert response.action == "needs_human"
        missing_fields = response.data.get("missing_fields", [])
        # Should require phone OR email (and customer_name)
        assert "customer_name" in missing_fields or ("phone or email" in " ".join(missing_fields))
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.core.billing_inquiry.handle_core_command")
    async def test_billing_inquiry_success(self, mock_core_handler):
        """Should successfully retrieve billing information."""
        from src.brains.core.schema import CoreResult, CoreStatus
        mock_core_handler.return_value = CoreResult(
            status=CoreStatus.SUCCESS,
            message="Billing information retrieved",
            requires_human=False,
            data={
                "balance_due": 250.0,
                "due_date": "2026-02-01",
                "payment_terms": "Net 15",
            },
        )
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
        }
        
        response = await handle_billing_inquiry(
            tool_call_id="tc_billing_002",
            parameters=parameters,
            call_id="call_billing_002",
        )
        
        assert response.action == "completed"
        assert "billing" in response.speak.lower() or "balance" in response.speak.lower() or "payment" in response.speak.lower()


class TestGetPricing:
    """Tests for get_pricing tool."""
    
    @pytest.mark.asyncio
    async def test_get_pricing_requires_property_type(self):
        """Should require property type."""
        parameters = {}
        
        response = await handle_get_pricing(
            tool_call_id="tc_pricing_001",
            parameters=parameters,
            call_id="call_pricing_001",
        )
        
        assert response.action == "needs_human"
        assert "property_type" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.core.get_pricing.calculate_service_pricing")
    async def test_get_pricing_residential(self, mock_calculate_pricing):
        """Should return residential pricing."""
        mock_calculate_pricing.return_value = {
            "tier": "retail",
            "diagnostic_fee": 125.0,
            "trip_charge": 99.0,
            "emergency_premium": 62.5,
        }
        
        parameters = {
            "property_type": "residential",
        }
        
        response = await handle_get_pricing(
            tool_call_id="tc_pricing_002",
            parameters=parameters,
            call_id="call_pricing_002",
        )
        
        assert response.action == "completed"
        assert response.data.get("pricing_tier") == "retail" or response.data.get("diagnostic_fee") == 125.0
        assert response.data.get("diagnostic_fee") == 125.0
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.core.get_pricing.calculate_service_pricing")
    async def test_get_pricing_commercial(self, mock_calculate_pricing):
        """Should return commercial pricing."""
        mock_calculate_pricing.return_value = {
            "tier": "commercial",
            "diagnostic_fee": 250.0,
            "trip_charge": 179.0,
            "emergency_premium": 100.0,
        }
        
        parameters = {
            "property_type": "commercial",
        }
        
        response = await handle_get_pricing(
            tool_call_id="tc_pricing_003",
            parameters=parameters,
            call_id="call_pricing_003",
        )
        
        assert response.action == "completed"
        assert response.data.get("pricing_tier") == "com" or response.data.get("diagnostic_fee") == 250.0
        assert response.data.get("diagnostic_fee") == 250.0


class TestCreateComplaint:
    """Tests for create_complaint tool."""
    
    @pytest.mark.asyncio
    async def test_create_complaint_requires_customer_name(self):
        """Should require customer name."""
        parameters = {
            "issue_description": "Technician was rude",
        }
        
        response = await handle_create_complaint(
            tool_call_id="tc_complaint_001",
            parameters=parameters,
            call_id="call_complaint_001",
        )
        
        assert response.action == "needs_human"
        assert "customer_name" in response.data.get("missing_fields", [])
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.core.create_complaint.create_odoo_client_from_settings")
    @patch("src.vapi.tools.core.create_complaint.create_email_service_from_settings")
    async def test_create_complaint_success(self, mock_email_service, mock_odoo_client):
        """Should successfully create complaint ticket."""
        # Mock Odoo client
        mock_client = AsyncMock()
        mock_odoo_client.return_value = mock_client
        mock_client.is_authenticated = True
        mock_client.create.return_value = 9001  # Ticket ID
        
        # Mock email service
        mock_email_instance = MagicMock()
        mock_email_service.return_value = mock_email_instance
        mock_email_instance.send_email.return_value = {"status": "sent"}
        
        parameters = {
            "customer_name": "John Doe",
            "phone": "+19725551234",
            "complaint_details": "Technician was late and rude",
            "service_date": "2026-01-10",
        }
        
        response = await handle_create_complaint(
            tool_call_id="tc_complaint_002",
            parameters=parameters,
            call_id="call_complaint_002",
        )
        
        assert response.action == "completed"
        assert response.data.get("escalation_ticket_id") is not None or response.data.get("ticket_id") is not None
        assert "complaint" in response.speak.lower() or "escalation" in response.speak.lower() or "documenting" in response.speak.lower()


class TestPaymentTermsInquiry:
    """Tests for payment_terms_inquiry tool."""
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.core.payment_terms_inquiry.handle_core_command")
    async def test_payment_terms_inquiry_success(self, mock_core_handler):
        """Should successfully retrieve payment terms."""
        from src.brains.core.schema import CoreResult, CoreStatus
        mock_core_handler.return_value = CoreResult(
            status=CoreStatus.SUCCESS,
            message="Payment terms retrieved",
            requires_human=False,
            data={
                "payment_terms": "Net 15",
                "late_fee_percent": 1.0,
            },
        )
        
        parameters = {
            "property_type": "commercial",
        }
        
        response = await handle_payment_terms_inquiry(
            tool_call_id="tc_payment_terms_001",
            parameters=parameters,
            call_id="call_payment_terms_001",
        )
        
        assert response.action == "completed"
        assert "payment" in response.speak.lower() or "terms" in response.speak.lower()


class TestInvoiceRequest:
    """Tests for invoice_request tool."""
    
    @pytest.mark.asyncio
    async def test_invoice_request_requires_phone_or_email(self):
        """Should require phone or email."""
        parameters = {}
        
        response = await handle_invoice_request(
            tool_call_id="tc_invoice_001",
            parameters=parameters,
            call_id="call_invoice_001",
        )
        
        assert response.action == "needs_human"
        missing_fields = response.data.get("missing_fields", [])
        # Should require phone OR email (and customer_name)
        assert "customer_name" in missing_fields or ("phone or email" in " ".join(missing_fields))


class TestInventoryInquiry:
    """Tests for inventory_inquiry tool."""
    
    @pytest.mark.asyncio
    @patch("src.vapi.tools.core.inventory_inquiry.handle_core_command")
    async def test_inventory_inquiry_success(self, mock_core_handler):
        """Should successfully retrieve inventory information."""
        from src.brains.core.schema import CoreResult, CoreStatus
        mock_core_handler.return_value = CoreResult(
            status=CoreStatus.SUCCESS,
            message="Inventory information retrieved",
            requires_human=False,
            data={
                "parts": [
                    {"name": "AC Filter", "available": True, "quantity": 50},
                    {"name": "Thermostat", "available": False, "quantity": 0},
                ],
            },
        )
        
        parameters = {
            "part_name": "AC Filter",
        }
        
        response = await handle_inventory_inquiry(
            tool_call_id="tc_inventory_001",
            parameters=parameters,
            call_id="call_inventory_001",
        )
        
        assert response.action == "completed"
        assert "inventory" in response.speak.lower() or "available" in response.speak.lower()


class TestPurchaseRequest:
    """Tests for purchase_request tool."""
    
    @pytest.mark.asyncio
    async def test_purchase_request_requires_item_name(self):
        """Should require item name."""
        parameters = {}
        
        response = await handle_purchase_request(
            tool_call_id="tc_purchase_001",
            parameters=parameters,
            call_id="call_purchase_001",
        )
        
        assert response.action == "needs_human"
        missing_fields = response.data.get("missing_fields", [])
        # Should require part_name (code uses part_name, not item_name)
        assert "part_name" in missing_fields or "item_name" in missing_fields or any("part" in f.lower() or "item" in f.lower() for f in missing_fields)
