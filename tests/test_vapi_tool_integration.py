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
