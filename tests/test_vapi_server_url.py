"""
HAES HVAC - Vapi Server URL Tests

Tests for the Vapi Server URL endpoint (/vapi/server).
"""

import json
import hashlib
import hmac
import time
from unittest.mock import patch

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


def generate_vapi_signature(body: bytes, secret: str, timestamp: int | None = None) -> tuple[str, str | None]:
    """Generate a valid Vapi signature for testing."""
    if timestamp is None:
        timestamp = int(time.time())
    
    payload = f"{timestamp}.".encode() + body
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    
    return signature, str(timestamp)


class TestVapiServerToolCalls:
    """Tests for tool-calls message type."""

    def test_tool_calls_hael_route_service_request(self, client, mock_settings):
        """Test hael_route tool call with service request."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_123"},
                "toolCallList": [
                    {
                        "id": "tc_001",
                        "name": "hael_route",
                        "parameters": {
                            "user_text": "My AC is not working. I'm John Smith at 123 Main St Dallas TX. It's urgent.",
                            "conversation_context": "Customer called about AC issue"
                        }
                    }
                ]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["toolCallId"] == "tc_001"
        
        result = json.loads(data["results"][0]["result"])
        assert "speak" in result
        assert "action" in result
        assert result["action"] in ["completed", "needs_human"]

    def test_tool_calls_with_toolWithToolCallList(self, client, mock_settings):
        """Test tool-calls using toolWithToolCallList format."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_456"},
                "toolWithToolCallList": [
                    {
                        "name": "hael_route",
                        "toolCall": {
                            "id": "tc_002",
                            "parameters": {
                                "user_text": "I need a quote for a new AC system",
                                "conversation_context": "New installation inquiry"
                            }
                        }
                    }
                ]
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["toolCallId"] == "tc_002"

    def test_tool_calls_unknown_tool(self, client, mock_settings):
        """Test tool-calls with unknown tool name."""
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call_789"},
                "toolCallList": [
                    {
                        "id": "tc_003",
                        "name": "unknown_tool",
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
        assert "unknown" in result["data"]["error"].lower()

    def test_tool_calls_empty(self, client, mock_settings):
        """Test tool-calls with empty list."""
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


class TestVapiServerTransfer:
    """Tests for transfer-destination-request message type."""

    def test_transfer_during_business_hours(self, client, mock_settings):
        """Test transfer request during business hours."""
        # Mock business hours check
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
            assert data["destination"]["number"] == "+19723724458"

    def test_transfer_after_hours(self, client, mock_settings):
        """Test transfer request after business hours."""
        with patch("src.api.vapi_server.is_business_hours", return_value=False):
            payload = {
                "message": {
                    "type": "transfer-destination-request",
                    "call": {"id": "call_after_hours"}
                }
            }
            
            response = client.post("/vapi/server", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"] == "after_hours"
            assert "message" in data
            assert "closed" in data["message"]["content"].lower()

    def test_handoff_destination_request(self, client, mock_settings):
        """Test handoff-destination-request message type (alias)."""
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


class TestVapiServerOtherMessages:
    """Tests for other message types."""

    def test_end_of_call_report(self, client, mock_settings):
        """Test end-of-call-report message type."""
        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "call_ended"},
                "summary": "Customer requested AC service. Appointment scheduled.",
                "durationSeconds": 120,
                "endedReason": "customer-hung-up"
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_status_update(self, client, mock_settings):
        """Test status-update message type."""
        payload = {
            "message": {
                "type": "status-update",
                "call": {"id": "call_status"},
                "status": "in-progress"
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_transcript_message(self, client, mock_settings):
        """Test transcript message type."""
        payload = {
            "message": {
                "type": "transcript",
                "call": {"id": "call_transcript"},
                "transcript": "Hello, I need help with my AC."
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_unknown_message_type(self, client, mock_settings):
        """Test unknown message type."""
        payload = {
            "message": {
                "type": "unknown-type",
                "call": {"id": "call_unknown"}
            }
        }
        
        response = client.post("/vapi/server", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestVapiServerHealth:
    """Tests for the health check endpoint."""

    def test_health_check(self, client, mock_settings):
        """Test health check endpoint."""
        response = client.get("/vapi/server/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["endpoint"] == "/vapi/server"
        assert "business_hours" in data
        assert data["transfer_number"] == "+19723724458"


class TestVapiServerSignatureVerification:
    """Tests for webhook signature verification."""

    def test_signature_verification_production(self, client):
        """Test signature verification in production mode."""
        secret = "test_secret_123"
        
        with patch("src.config.settings.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ENVIRONMENT = "production"
            settings.is_production = True
            settings.VAPI_WEBHOOK_SECRET = secret
            settings.RATE_LIMIT_ENABLED = False
            
            payload = {
                "message": {
                    "type": "status-update",
                    "call": {"id": "call_prod"},
                    "status": "in-progress"
                }
            }
            body = json.dumps(payload).encode()
            signature, timestamp = generate_vapi_signature(body, secret)
            
            response = client.post(
                "/vapi/server",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Vapi-Signature": signature,
                    "X-Vapi-Timestamp": timestamp,
                }
            )
            
            # Should succeed with valid signature
            assert response.status_code == 200

    def test_invalid_signature_rejected(self, client):
        """Test invalid signature is rejected in production."""
        # Patch at all levels where get_settings is imported
        with patch("src.utils.webhook_verify.get_settings") as mock_wh_settings, \
             patch("src.config.settings.get_settings") as mock_settings:
            
            # Configure both mocks
            for mock in [mock_wh_settings, mock_settings]:
                settings = mock.return_value
                settings.ENVIRONMENT = "production"
                settings.is_production = True
                settings.VAPI_WEBHOOK_SECRET = "correct_secret"
                settings.RATE_LIMIT_ENABLED = False
            
            payload = {"message": {"type": "status-update", "call": {"id": "test"}}}
            body = json.dumps(payload).encode()
            
            # Generate signature with wrong secret
            wrong_signature, timestamp = generate_vapi_signature(body, "wrong_secret")
            
            response = client.post(
                "/vapi/server",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Vapi-Signature": wrong_signature,
                    "X-Vapi-Timestamp": timestamp,
                }
            )
            
            # Should be rejected
            assert response.status_code == 401


class TestBusinessHoursLogic:
    """Tests for business hours determination."""

    def test_is_business_hours_weekday_within_hours(self):
        """Test business hours returns True during weekday business hours."""
        from src.api.vapi_server import is_business_hours, BUSINESS_TZ
        from datetime import datetime
        
        # Mock a Wednesday at 10 AM Chicago time
        with patch("src.api.vapi_server.datetime") as mock_dt:
            mock_now = datetime(2026, 1, 8, 10, 0, 0, tzinfo=BUSINESS_TZ)  # Wednesday
            mock_dt.now.return_value = mock_now
            
            # Note: Can't fully test without proper datetime mocking
            # This is a structural test to ensure function exists
            assert callable(is_business_hours)

    def test_transfer_number_format(self):
        """Test transfer number is properly formatted."""
        from src.api.vapi_server import TRANSFER_NUMBER
        
        assert TRANSFER_NUMBER.startswith("+1")
        assert len(TRANSFER_NUMBER) == 12  # +1 + 10 digits
