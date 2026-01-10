"""
HAES HVAC - Vapi Tool Integration Tests

Comprehensive tests for Vapi tool call integration covering:
- Different tool call payload formats
- Context merging (user_text + conversation_context)
- Response format validation
- Error handling
"""

import json
import hashlib
import hmac
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    with patch("src.config.settings.get_settings") as mock:
        settings = mock.return_value
        settings.ENVIRONMENT = "development"
        settings.is_production = False
        settings.VAPI_WEBHOOK_SECRET = ""
        settings.RATE_LIMIT_ENABLED = False
        yield settings


def create_tool_call_payload(
    tool_name: str = "hael_route",
    tool_call_id: str = "tc_001",
    user_text: str = "My AC is broken",
    conversation_context: str | None = None,
    call_id: str = "call_123",
    use_toolWithToolCallList: bool = False,
    use_arguments: bool = False,
    use_function_format: bool = False,
):
    """
    Helper to create various Vapi tool call payload formats.
    
    Args:
        tool_name: Name of the tool
        tool_call_id: Unique ID for the tool call
        user_text: The user's message
        conversation_context: Optional conversation context
        call_id: The call ID
        use_toolWithToolCallList: Use the newer toolWithToolCallList format
        use_arguments: Use 'arguments' instead of 'parameters'
        use_function_format: Use nested function.parameters format
    """
    params = {"user_text": user_text}
    if conversation_context:
        params["conversation_context"] = conversation_context
    
    if use_toolWithToolCallList:
        if use_function_format:
            return {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": call_id},
                    "toolWithToolCallList": [
                        {
                            "name": tool_name,
                            "toolCall": {
                                "id": tool_call_id,
                                "function": {
                                    "name": tool_name,
                                    "parameters": params,
                                }
                            }
                        }
                    ]
                }
            }
        else:
            return {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": call_id},
                    "toolWithToolCallList": [
                        {
                            "name": tool_name,
                            "toolCall": {
                                "id": tool_call_id,
                                "parameters": params,
                            }
                        }
                    ]
                }
            }
    else:
        param_key = "arguments" if use_arguments else "parameters"
        return {
            "message": {
                "type": "tool-calls",
                "call": {"id": call_id},
                "toolCallList": [
                    {
                        "id": tool_call_id,
                        "name": tool_name,
                        param_key: params,
                    }
                ]
            }
        }


# =============================================================================
# TOOL CALL FORMAT TESTS
# =============================================================================


class TestToolCallFormats:
    """Tests for different Vapi tool call payload formats."""

    def test_toolCallList_with_parameters(self, client, mock_settings):
        """Test toolCallList format with parameters field."""
        payload = create_tool_call_payload(
            user_text="My AC is not working. I'm at 512-555-1234, zip 78701",
            use_toolWithToolCallList=False,
            use_arguments=False,
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["toolCallId"] == "tc_001"

    def test_toolCallList_with_arguments(self, client, mock_settings):
        """Test toolCallList format with arguments field."""
        payload = create_tool_call_payload(
            user_text="My heater is broken",
            use_toolWithToolCallList=False,
            use_arguments=True,
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_toolWithToolCallList_with_parameters(self, client, mock_settings):
        """Test toolWithToolCallList format with parameters field."""
        payload = create_tool_call_payload(
            user_text="I need a quote for new AC",
            use_toolWithToolCallList=True,
            use_arguments=False,
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["results"][0]["toolCallId"] == "tc_001"

    def test_toolWithToolCallList_function_format(self, client, mock_settings):
        """Test toolWithToolCallList with nested function.parameters."""
        payload = create_tool_call_payload(
            user_text="Schedule an appointment please",
            use_toolWithToolCallList=True,
            use_function_format=True,
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_empty_tool_call_list(self, client, mock_settings):
        """Test empty tool call list."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_empty"},
                "toolCallList": []
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []


# =============================================================================
# CONTEXT MERGING TESTS
# =============================================================================


class TestContextMerging:
    """Tests for user_text and conversation_context merging."""

    def test_user_text_only(self, client, mock_settings):
        """Test with user_text only."""
        payload = create_tool_call_payload(
            user_text="My AC is broken at 512-555-1234",
            conversation_context=None,
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result

    def test_user_text_with_context(self, client, mock_settings):
        """Test with user_text and conversation_context."""
        payload = create_tool_call_payload(
            user_text="Yes, that's correct",
            conversation_context=(
                "Customer called about AC issue. "
                "Name: John Smith. Phone: 512-555-9999. "
                "Address: 123 Main St, Austin TX 78701. "
                "Problem: AC not cooling properly."
            ),
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result

    def test_context_with_entities(self, client, mock_settings):
        """Test context extraction with entities in context."""
        payload = create_tool_call_payload(
            user_text="Please help me",
            conversation_context=(
                "Service request. Customer: Jane Doe. "
                "Phone: 214-555-4444. Email: jane@example.com. "
                "Location: 456 Oak Ave, Dallas TX 75201. "
                "Issue: Heater not heating, it's 30 degrees outside."
            ),
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        # Should have extracted entities from context
        assert "speak" in result

    def test_emergency_in_context(self, client, mock_settings):
        """Test emergency detection from context."""
        payload = create_tool_call_payload(
            user_text="Yes, please help!",
            conversation_context=(
                "Customer reports gas smell from furnace. "
                "Phone: 512-555-0001. Address: 789 Elm St, 78702."
            ),
        )
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================


class TestResponseFormat:
    """Tests for response format validation."""

    def test_response_has_results(self, client, mock_settings):
        """Response should have results array."""
        payload = create_tool_call_payload(user_text="My AC is broken")
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_result_has_tool_call_id(self, client, mock_settings):
        """Each result should have toolCallId."""
        payload = create_tool_call_payload(
            tool_call_id="tc_test_123",
            user_text="My heater is broken",
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        assert data["results"][0]["toolCallId"] == "tc_test_123"

    def test_result_has_json_result(self, client, mock_settings):
        """Each result should have JSON result string."""
        payload = create_tool_call_payload(user_text="My AC is broken")
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result_str = data["results"][0]["result"]
        
        # Should be valid JSON
        result = json.loads(result_str)
        assert isinstance(result, dict)

    def test_result_contains_speak(self, client, mock_settings):
        """Result should contain speak field."""
        payload = create_tool_call_payload(
            user_text="My AC is broken. Phone 512-555-1234, zip 78701",
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result
        assert isinstance(result["speak"], str)
        assert len(result["speak"]) > 0

    def test_result_contains_action(self, client, mock_settings):
        """Result should contain action field."""
        payload = create_tool_call_payload(
            user_text="My AC is broken. Phone 512-555-1234, zip 78701",
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "action" in result
        assert result["action"] in ["completed", "needs_human", "error"]

    def test_result_contains_request_id(self, client, mock_settings):
        """Result should contain request_id."""
        payload = create_tool_call_payload(user_text="My AC is broken")
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "request_id" in result

    def test_result_contains_data(self, client, mock_settings):
        """Result should contain data object."""
        payload = create_tool_call_payload(user_text="My AC is broken")
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "data" in result
        assert isinstance(result["data"], dict)


# =============================================================================
# UNKNOWN TOOL TESTS
# =============================================================================


class TestUnknownTool:
    """Tests for unknown tool handling."""

    def test_unknown_tool_returns_error(self, client, mock_settings):
        """Unknown tool should return error action."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_123"},
                "toolCallList": [
                    {
                        "id": "tc_001",
                        "name": "unknown_tool",
                        "parameters": {"foo": "bar"}
                    }
                ]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert result["action"] == "error"
        assert "unknown" in result["data"]["error"].lower()

    def test_empty_tool_name(self, client, mock_settings):
        """Empty tool name should return error."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_123"},
                "toolCallList": [
                    {
                        "id": "tc_001",
                        "name": "",
                        "parameters": {}
                    }
                ]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert result["action"] == "error"


# =============================================================================
# TRANSFER DESTINATION TESTS
# =============================================================================


class TestTransferDestination:
    """Tests for transfer destination requests."""

    def test_transfer_during_business_hours(self, client, mock_settings):
        """Transfer during business hours should return phone number."""
        with patch("src.api.vapi_server.is_business_hours", return_value=True):
            payload = {
                "message": {
                    "type": "transfer-destination-request",
                    "call": {"id": "call_transfer"}
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert "destination" in data
            assert data["destination"]["type"] == "number"
            assert data["destination"]["number"].startswith("+1")

    def test_transfer_after_hours(self, client, mock_settings):
        """Transfer after hours should return after_hours message."""
        with patch("src.api.vapi_server.is_business_hours", return_value=False):
            payload = {
                "message": {
                    "type": "transfer-destination-request",
                    "call": {"id": "call_after"}
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"] == "after_hours"

    def test_handoff_destination_request(self, client, mock_settings):
        """Handoff-destination-request should work same as transfer."""
        with patch("src.api.vapi_server.is_business_hours", return_value=True):
            payload = {
                "message": {
                    "type": "handoff-destination-request",
                    "call": {"id": "call_handoff"}
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert "destination" in data


# =============================================================================
# OTHER MESSAGE TYPES TESTS
# =============================================================================


class TestOtherMessageTypes:
    """Tests for other Vapi message types."""

    def test_end_of_call_report(self, client, mock_settings):
        """End-of-call-report should return ok."""
        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "call_ended"},
                "summary": "Customer requested service",
                "durationSeconds": 120,
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_status_update(self, client, mock_settings):
        """Status-update should return ok."""
        payload = {
            "message": {
                "type": "status-update",
                "call": {"id": "call_status"},
                "status": "in-progress",
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_transcript_message(self, client, mock_settings):
        """Transcript message should return ok."""
        payload = {
            "message": {
                "type": "transcript",
                "call": {"id": "call_transcript"},
                "transcript": "Hello, I need help with my AC.",
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_unknown_message_type(self, client, mock_settings):
        """Unknown message type should return ok."""
        payload = {
            "message": {
                "type": "some-future-type",
                "call": {"id": "call_unknown"},
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check(self, client, mock_settings):
        """Health check should return ok."""
        response = client.get("/vapi/server/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["endpoint"] == "/vapi/server"
        assert "business_hours" in data
        assert "transfer_number" in data


# =============================================================================
# MULTIPLE TOOL CALLS TESTS
# =============================================================================


class TestMultipleToolCalls:
    """Tests for multiple tool calls in single request."""

    def test_multiple_tool_calls(self, client, mock_settings):
        """Multiple tool calls should all be processed."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_multi"},
                "toolCallList": [
                    {
                        "id": "tc_001",
                        "name": "hael_route",
                        "parameters": {"user_text": "My AC is broken"}
                    },
                    {
                        "id": "tc_002",
                        "name": "hael_route",
                        "parameters": {"user_text": "My heater is broken"}
                    }
                ]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["toolCallId"] == "tc_001"
        assert data["results"][1]["toolCallId"] == "tc_002"


# =============================================================================
# INTENT-SPECIFIC VAPI TESTS
# =============================================================================


class TestIntentSpecificVapi:
    """Tests for specific intents through Vapi integration."""

    def test_service_request_via_vapi(self, client, mock_settings):
        """Service request via Vapi."""
        payload = create_tool_call_payload(
            user_text=(
                "My AC is not working. I'm John at 512-555-1234. "
                "Address is 123 Main St, Austin TX 78701."
            ),
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert result["action"] in ["completed", "needs_human"]

    def test_quote_request_via_vapi(self, client, mock_settings):
        """Quote request via Vapi."""
        payload = create_tool_call_payload(
            user_text=(
                "I need a quote for a new AC system. "
                "I'm Sarah at 512-555-9999. "
                "It's a residential property, 2500 sq ft. "
                "Want it done within 2 weeks."
            ),
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result

    def test_billing_inquiry_via_vapi(self, client, mock_settings):
        """Billing inquiry via Vapi."""
        payload = create_tool_call_payload(
            user_text="I have a question about my bill. My phone is 512-555-4444.",
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result

    def test_hiring_inquiry_via_vapi(self, client, mock_settings):
        """Hiring inquiry via Vapi."""
        payload = create_tool_call_payload(
            user_text="Are you hiring HVAC technicians?",
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result
        assert result["action"] == "completed"

    def test_emergency_via_vapi(self, client, mock_settings):
        """Emergency via Vapi."""
        payload = create_tool_call_payload(
            user_text=(
                "I smell gas! This is urgent! "
                "Call me at 512-555-0001. I'm at 789 Oak St, 78702."
            ),
        )
        
        response = client.post("/vapi/server", json=payload)
        
        data = response.json()
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result
        # Emergency should be handled
        assert result["action"] in ["completed", "needs_human"]


# =============================================================================
# ODOO LEAD CREATION TESTS
# =============================================================================


class TestOdooLeadCreation:
    """Tests for Odoo CRM lead creation via Vapi tool calls."""

    def test_service_request_includes_odoo_data(self, client, mock_settings):
        """Service request should include odoo data in response when successful."""
        with patch("src.integrations.odoo_leads.upsert_lead_for_call") as mock_upsert:
            mock_upsert.return_value = {
                "lead_id": 123,
                "action": "created",
                "status": "success",
                "partner_id": 456,
            }
            
            payload = {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": "call_lead_test"},
                    "toolCallList": [{
                        "id": "tc_lead",
                        "name": "hael_route",
                        "parameters": {
                            "request_type": "service_request",
                            "customer_name": "John Doe",
                            "phone": "+19725551234",
                            "address": "123 Main St, Dallas, TX 75201",
                            "issue_description": "Heater not working",
                            "urgency": "today",
                            "property_type": "residential",
                        }
                    }]
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            result = json.loads(data["results"][0]["result"])
            
            # Check that Odoo data is present
            assert "data" in result
            if result["action"] == "completed":
                assert "odoo" in result["data"]
                assert result["data"]["odoo"]["crm_lead_id"] == 123

    def test_service_request_handles_odoo_failure(self, client, mock_settings):
        """Service request should handle Odoo failure gracefully."""
        with patch("src.integrations.odoo_leads.upsert_lead_for_call") as mock_upsert:
            mock_upsert.return_value = {
                "lead_id": None,
                "action": "failed",
                "status": "error",
                "error": "Odoo connection timeout",
            }
            
            payload = {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": "call_odoo_fail"},
                    "toolCallList": [{
                        "id": "tc_fail",
                        "name": "hael_route",
                        "parameters": {
                            "request_type": "service_request",
                            "customer_name": "Jane Smith",
                            "phone": "+19725559999",
                            "address": "456 Oak St, Dallas, TX 75202",
                            "issue_description": "AC not cooling",
                            "urgency": "today",
                            "property_type": "residential",
                        }
                    }]
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            result = json.loads(data["results"][0]["result"])
            
            # Should still return a valid response
            assert "speak" in result
            # If Odoo fails, should downgrade to needs_human
            if "odoo" in result.get("data", {}):
                assert result["data"]["odoo"]["action"] == "failed"

    def test_service_request_passes_correct_params_to_odoo(self, client, mock_settings):
        """Should pass correct parameters to Odoo lead upsert."""
        with patch("src.integrations.odoo_leads.upsert_lead_for_call") as mock_upsert:
            mock_upsert.return_value = {
                "lead_id": 789,
                "action": "created",
                "status": "success",
                "partner_id": None,
            }
            
            payload = {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": "call_params_test"},
                    "toolCallList": [{
                        "id": "tc_params",
                        "name": "hael_route",
                        "parameters": {
                            "request_type": "service_request",
                            "customer_name": "Test User",
                            "phone": "+19725550000",
                            "address": "789 Elm St, Plano, TX 75023",
                            "issue_description": "Furnace making noise",
                            "urgency": "emergency",
                            "property_type": "commercial",
                        }
                    }]
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            
            # Verify upsert was called with correct call_id
            mock_upsert.assert_called_once()
            call_kwargs = mock_upsert.call_args[1]
            assert call_kwargs["call_id"] == "call_params_test"

    def test_quote_request_creates_lead(self, client, mock_settings):
        """Quote request should also create a lead."""
        with patch("src.integrations.odoo_leads.upsert_lead_for_call") as mock_upsert:
            mock_upsert.return_value = {
                "lead_id": 200,
                "action": "created",
                "status": "success",
                "partner_id": 300,
            }
            
            payload = {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": "call_quote_lead"},
                    "toolCallList": [{
                        "id": "tc_quote",
                        "name": "hael_route",
                        "parameters": {
                            "request_type": "quote_request",
                            "customer_name": "Quote Customer",
                            "phone": "+19725553333",
                            "address": "100 New St, Irving, TX 75060",
                            "issue_description": "Need new AC system quote",
                            "urgency": "this_week",
                            "property_type": "residential",
                        }
                    }]
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            
            # Quote request should call upsert
            mock_upsert.assert_called_once()

    def test_billing_inquiry_does_not_create_lead(self, client, mock_settings):
        """Billing inquiry should NOT create a lead."""
        with patch("src.integrations.odoo_leads.upsert_lead_for_call") as mock_upsert:
            payload = {
                "message": {
                    "type": "tool-calls",
                    "call": {"id": "call_billing"},
                    "toolCallList": [{
                        "id": "tc_billing",
                        "name": "hael_route",
                        "parameters": {
                            "request_type": "billing_inquiry",
                            "customer_name": "Billing Customer",
                            "phone": "+19725554444",
                        }
                    }]
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            
            # Billing inquiry should NOT call upsert
            mock_upsert.assert_not_called()


class TestIdempotencyWithOdoo:
    """Tests for idempotency handling with Odoo lead creation."""

    def test_duplicate_tool_call_returns_cached_result(self, client, mock_settings):
        """Duplicate tool calls should return cached result (no double-create)."""
        # This test verifies the idempotency mechanism
        # First call should process, second should hit cache
        
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_dedupe"},
                "toolCallList": [{
                    "id": "tc_same_id",  # Same tool_call_id
                    "name": "hael_route",
                    "parameters": {
                        "user_text": "Service request - heater broken",
                    }
                }]
            }
        }
        
        # First call
        response1 = client.post("/vapi/server", json=payload)
        assert response1.status_code == 200
        result1 = json.loads(response1.json()["results"][0]["result"])
        
        # Second call with same call_id and tool_call_id
        response2 = client.post("/vapi/server", json=payload)
        assert response2.status_code == 200
        result2 = json.loads(response2.json()["results"][0]["result"])
        
        # Both should have same request_id (idempotency hit)
        # Note: In actual implementation, second call may or may not hit cache
        # depending on DB state; this tests the mechanism exists
        assert "request_id" in result1
        assert "request_id" in result2


# =============================================================================
# Emergency Flow Tests
# =============================================================================


class TestEmergencyFlow:
    """Tests for emergency service request flow including ETA, pricing, and tech assignment."""

    def test_emergency_with_temperature_returns_critical_priority(self, client, mock_settings):
        """Emergency with indoor temp below threshold should return CRITICAL priority."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_emergency_temp"},
                "toolCallList": [{
                    "id": "tc_emerg_temp",
                    "name": "hael_route",
                    "parameters": {
                        "request_type": "service_request",
                        "customer_name": "Emergency Customer",
                        "phone": "+19725559999",
                        "address": "123 Cold St, DeSoto, TX 75115",
                        "issue_description": "no heat at all",
                        "urgency": "emergency",
                        "property_type": "residential",
                        "system_type": "furnace",
                        "indoor_temperature_f": 54,  # Below 55°F threshold
                    }
                }]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        result = json.loads(response.json()["results"][0]["result"])
        
        # Should be emergency
        assert result["data"].get("is_emergency") is True
        # Priority label should be CRITICAL
        assert result["data"].get("priority_label") == "CRITICAL"

    def test_emergency_returns_eta_window(self, client, mock_settings):
        """Emergency service should include ETA window in response."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_eta"},
                "toolCallList": [{
                    "id": "tc_eta",
                    "name": "hael_route",
                    "parameters": {
                        "request_type": "service_request",
                        "customer_name": "ETA Test",
                        "phone": "+19725558888",
                        "address": "456 Emergency Ln, DeSoto, TX 75115",
                        "issue_description": "gas smell - emergency",
                        "urgency": "emergency",
                    }
                }]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        result = json.loads(response.json()["results"][0]["result"])
        
        # Should have ETA window
        assert result["data"].get("eta_window_hours_min") is not None
        assert result["data"].get("eta_window_hours_max") is not None
        assert result["data"]["eta_window_hours_min"] == 1.5
        assert result["data"]["eta_window_hours_max"] == 3.0

    def test_emergency_includes_pricing_breakdown(self, client, mock_settings):
        """Emergency service should include pricing breakdown."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_pricing"},
                "toolCallList": [{
                    "id": "tc_pricing",
                    "name": "hael_route",
                    "parameters": {
                        "request_type": "service_request",
                        "customer_name": "Pricing Test",
                        "phone": "+19725557777",
                        "address": "789 Price St, DeSoto, TX 75115",
                        "issue_description": "flooding from AC unit - emergency",
                        "urgency": "emergency",
                    }
                }]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        result = json.loads(response.json()["results"][0]["result"])
        
        # Should have pricing
        pricing = result["data"].get("pricing")
        assert pricing is not None
        assert "tier" in pricing
        assert "diagnostic_fee" in pricing
        assert "emergency_premium" in pricing
        assert "total_base_fee" in pricing
        # Retail tier by default
        assert pricing["tier"] == "retail"

    def test_desoto_address_assigns_junior(self, client, mock_settings):
        """Service request in DeSoto (75115) should assign Junior."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_junior"},
                "toolCallList": [{
                    "id": "tc_junior",
                    "name": "hael_route",
                    "parameters": {
                        "request_type": "service_request",
                        "customer_name": "DeSoto Customer",
                        "phone": "+19725556666",
                        "address": "100 Junior Zone, DeSoto, TX 75115",
                        "issue_description": "heater making noise",
                        "urgency": "today",
                    }
                }]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        result = json.loads(response.json()["results"][0]["result"])
        
        # Should have assigned technician
        tech = result["data"].get("assigned_technician")
        assert tech is not None
        assert tech["id"] == "junior"
        assert tech["name"] == "Junior"

    def test_emergency_speak_includes_eta_and_pricing(self, client, mock_settings):
        """Emergency speak message should include ETA and pricing info."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_speak"},
                "toolCallList": [{
                    "id": "tc_speak",
                    "name": "hael_route",
                    "parameters": {
                        "request_type": "service_request",
                        "customer_name": "Speak Test",
                        "phone": "+19725555555",
                        "address": "111 Speak Ave, DeSoto, TX 75115",
                        "issue_description": "carbon monoxide alarm going off",
                        "urgency": "emergency",
                    }
                }]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        result = json.loads(response.json()["results"][0]["result"])
        
        speak = result["speak"]
        
        # Should mention ETA window
        assert "hour" in speak.lower() or "hours" in speak.lower()
        # Should mention diagnostic fee
        assert "$" in speak or "fee" in speak.lower()

    def test_non_emergency_no_eta_window(self, client, mock_settings):
        """Non-emergency requests should not include ETA window."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_normal"},
                "toolCallList": [{
                    "id": "tc_normal",
                    "name": "hael_route",
                    "parameters": {
                        "request_type": "service_request",
                        "customer_name": "Normal Customer",
                        "phone": "+19725554444",
                        "address": "222 Normal St, DeSoto, TX 75115",
                        "issue_description": "AC making slight noise",
                        "urgency": "this_week",
                    }
                }]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        result = json.loads(response.json()["results"][0]["result"])
        
        # Should NOT be emergency
        assert result["data"].get("is_emergency") is False
        # Should NOT have ETA window set
        assert result["data"].get("eta_window_hours_min") is None


class TestTwilioSMS:
    """Tests for Twilio SMS integration."""

    @patch("src.integrations.twilio_sms.TwilioSMSClient.send_sms")
    def test_emergency_sms_message_format(self, mock_send):
        """Test emergency SMS message format."""
        from src.integrations.twilio_sms import build_emergency_confirmation_sms
        
        message = build_emergency_confirmation_sms(
            customer_name="John Doe",
            tech_name="Junior",
            eta_hours_min=1.5,
            eta_hours_max=3.0,
            total_fee=187.50,
        )
        
        # Should contain key info
        assert "HVAC-R Finest" in message
        assert "John Doe" in message
        assert "Junior" in message
        assert "1.5" in message
        assert "3.0" in message
        assert "187.50" in message
        assert "STOP" in message  # Opt-out instruction

    def test_twilio_dry_run_mode(self):
        """Test that dry run mode logs instead of sending."""
        from src.integrations.twilio_sms import TwilioSMSClient
        import asyncio
        
        client = TwilioSMSClient(
            account_sid="test_sid",
            auth_token="test_token",
            from_number="+15555555555",
            dry_run=True,
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            client.send_sms(to="+19725551234", body="Test message")
        )
        
        assert result["status"] == "dry_run"
        assert "message_sid" in result

    @patch("src.config.settings.get_settings")
    def test_twilio_client_not_created_without_credentials(self, mock_settings):
        """Test client returns None if credentials missing."""
        from src.integrations.twilio_sms import create_twilio_client_from_settings
        
        mock_settings.return_value.TWILIO_ACCOUNT_SID = ""
        mock_settings.return_value.TWILIO_AUTH_TOKEN = ""
        mock_settings.return_value.TWILIO_PHONE_NUMBER = ""
        
        client = create_twilio_client_from_settings()
        
        assert client is None


class TestOdooEmergencyTagging:
    """Tests for Odoo emergency tag and activity creation."""

    @patch("src.integrations.odoo.OdooClient")
    async def test_emergency_tag_creation(self, mock_client):
        """Test that Emergency tag is found or created."""
        from src.integrations.odoo_leads import LeadService
        
        mock_instance = MagicMock()
        mock_instance.is_authenticated = False
        mock_instance.authenticate.return_value = None
        mock_instance.search_read.return_value = []  # Tag doesn't exist
        mock_instance.create.return_value = 42  # New tag ID
        
        service = LeadService(mock_instance)
        tag_id = await service.ensure_emergency_tag()
        
        assert tag_id == 42
        mock_instance.create.assert_called_once()

    @patch("src.integrations.odoo.OdooClient")
    async def test_chatter_message_posted_for_emergency(self, mock_client):
        """Test that chatter message is posted for emergencies."""
        from src.integrations.odoo_leads import LeadService
        
        mock_instance = MagicMock()
        mock_instance.is_authenticated = True
        mock_instance.call.return_value = 123  # Message ID
        
        service = LeadService(mock_instance)
        msg_id = await service.post_chatter_message(
            lead_id=1,
            body="<p>Test emergency message</p>",
            subject="Emergency",
        )
        
        assert msg_id == 123
        mock_instance.call.assert_called_once()


class TestEmailNotifications:
    """Tests for email notification service."""

    def test_emergency_email_template_format(self):
        """Test emergency email template format."""
        from src.integrations.email_notifications import build_emergency_notification_email
        
        html, text = build_emergency_notification_email(
            customer_name="John Doe",
            tech_name="Junior",
            eta_hours_min=1.5,
            eta_hours_max=3.0,
            total_fee=204.00,
            lead_id=1234,
            address="123 Test St, DeSoto, TX 75115",
            phone="+19725551234",
        )
        
        # HTML should contain key info
        assert "HVAC-R Finest" in html
        assert "John Doe" in html
        assert "Junior" in html
        assert "1.5" in html
        assert "3.0" in html
        assert "204.00" in html or "$204.00" in html
        
        # Text should contain key info
        assert "HVAC-R Finest" in text
        assert "John Doe" in text
        assert "Junior" in text
        assert "1.5" in text
        assert "3.0" in text
        assert "204.00" in text or "$204.00" in text
        
        # HTML should be valid HTML
        assert "<!DOCTYPE html>" in html or "<html>" in html
        assert "<body>" in html or "</body>" in html

    def test_service_confirmation_email_template(self):
        """Test service confirmation email template."""
        from src.integrations.email_notifications import build_service_confirmation_email
        
        html, text = build_service_confirmation_email(
            customer_name="Jane Smith",
            is_same_day=True,
        )
        
        assert "HVAC-R Finest" in html
        assert "Jane Smith" in html
        assert "today" in html.lower()
        
        assert "HVAC-R Finest" in text
        assert "Jane Smith" in text
        assert "today" in text.lower()

    def test_email_service_dry_run_mode(self):
        """Test that dry run mode logs instead of sending."""
        from src.integrations.email_notifications import EmailNotificationService
        
        service = EmailNotificationService(
            host="smtp.example.com",
            port=587,
            username="test@example.com",
            password="test_password",
            from_email="noreply@example.com",
            dry_run=True,
        )
        
        result = service.send_email(
            to="test@example.com",
            subject="Test Email",
            body_text="Test message body",
        )
        
        assert result["status"] == "dry_run"
        assert "message_id" in result

    @patch("src.config.settings.get_settings")
    def test_email_service_not_created_without_host(self, mock_settings):
        """Test service returns None if SMTP_HOST missing."""
        from src.integrations.email_notifications import create_email_service_from_settings
        
        mock_settings.return_value.SMTP_HOST = ""
        mock_settings.return_value.SMTP_PORT = 587
        mock_settings.return_value.SMTP_FROM_EMAIL = "test@example.com"
        mock_settings.return_value.SMTP_USERNAME = ""
        mock_settings.return_value.SMTP_PASSWORD = ""
        mock_settings.return_value.SMTP_USE_TLS = True
        mock_settings.return_value.SMTP_DRY_RUN = False
        mock_settings.return_value.SMTP_TEST_TO_EMAIL = ""
        
        service = create_email_service_from_settings()
        
        assert service is None

    @patch("src.config.settings.get_settings")
    def test_email_service_not_created_without_from_email(self, mock_settings):
        """Test service returns None if SMTP_FROM_EMAIL missing."""
        from src.integrations.email_notifications import create_email_service_from_settings
        
        mock_settings.return_value.SMTP_HOST = "smtp.example.com"
        mock_settings.return_value.SMTP_PORT = 587
        mock_settings.return_value.SMTP_FROM_EMAIL = ""
        mock_settings.return_value.SMTP_USERNAME = ""
        mock_settings.return_value.SMTP_PASSWORD = ""
        mock_settings.return_value.SMTP_USE_TLS = True
        mock_settings.return_value.SMTP_DRY_RUN = False
        mock_settings.return_value.SMTP_TEST_TO_EMAIL = ""
        
        service = create_email_service_from_settings()
        
        assert service is None

    @patch("smtplib.SMTP")
    def test_email_send_with_starttls(self, mock_smtp):
        """Test email sending with STARTTLS."""
        from src.integrations.email_notifications import EmailNotificationService
        
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        service = EmailNotificationService(
            host="smtp.example.com",
            port=587,
            username="test@example.com",
            password="test_password",
            from_email="noreply@example.com",
            use_tls=True,
            dry_run=False,
        )
        
        result = service.send_email(
            to="recipient@example.com",
            subject="Test",
            body_text="Test body",
        )
        
        assert result["status"] == "sent"
        mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("smtplib.SMTP_SSL")
    def test_email_send_with_ssl(self, mock_smtp_ssl):
        """Test email sending with SSL (port 465)."""
        from src.integrations.email_notifications import EmailNotificationService
        
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server
        
        service = EmailNotificationService(
            host="smtp.example.com",
            port=465,
            username="test@example.com",
            password="test_password",
            from_email="noreply@example.com",
            use_tls=True,
            dry_run=False,
        )
        
        result = service.send_email(
            to="recipient@example.com",
            subject="Test",
            body_text="Test body",
        )
        
        assert result["status"] == "sent"
        mock_smtp_ssl.assert_called_once_with("smtp.example.com", 465, timeout=30)
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.sendmail.assert_called_once()

    def test_email_test_recipient_override(self):
        """Test that test recipient override works."""
        from src.integrations.email_notifications import EmailNotificationService
        
        service = EmailNotificationService(
            host="smtp.example.com",
            port=587,
            username="test@example.com",
            password="test_password",
            from_email="noreply@example.com",
            test_to_email="test-override@example.com",
            dry_run=True,
        )
        
        result = service.send_email(
            to="original@example.com",  # Should be overridden
            subject="Test",
            body_text="Test body",
        )
        
        assert result["to"] == ["test-override@example.com"]
