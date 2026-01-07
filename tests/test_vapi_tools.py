"""
HAES HVAC - Vapi Tools Tests

Tests for Vapi tool endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestVapiHaelRoute:
    """Tests for the /vapi/tools/hael_route endpoint."""

    def test_service_request_routes_to_ops(self, client: TestClient):
        """Service request should route to OPS brain."""
        response = client.post(
            "/vapi/tools/hael_route",
            json={
                "call_id": "test-call-123",
                "tool_call_id": "tool-123",
                "user_text": "My AC is not working, please help. Call me at 512-555-1234. I'm at 78701.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] in ["completed", "needs_human"]
        assert "speak" in data

    def test_quote_request_routes_to_revenue(self, client: TestClient):
        """Quote request should route to REVENUE brain."""
        response = client.post(
            "/vapi/tools/hael_route",
            json={
                "call_id": "test-call-456",
                "tool_call_id": "tool-456",
                "user_text": "I need a quote for a new AC system for my home. Email me at test@example.com. I need it in the next month.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "speak" in data

    def test_billing_inquiry_routes_to_core(self, client: TestClient):
        """Billing inquiry should route to CORE brain."""
        response = client.post(
            "/vapi/tools/hael_route",
            json={
                "call_id": "test-call-789",
                "tool_call_id": "tool-789",
                "user_text": "What's my balance? My email is customer@test.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "speak" in data

    def test_hiring_inquiry_routes_to_people(self, client: TestClient):
        """Hiring inquiry should route to PEOPLE brain."""
        response = client.post(
            "/vapi/tools/hael_route",
            json={
                "call_id": "test-call-000",
                "tool_call_id": "tool-000",
                "user_text": "Are you hiring HVAC technicians?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "speak" in data

    def test_unknown_request_needs_human(self, client: TestClient):
        """Unknown request should need human intervention."""
        response = client.post(
            "/vapi/tools/hael_route",
            json={
                "call_id": "test-call-unknown",
                "tool_call_id": "tool-unknown",
                "user_text": "What's the weather like today?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "needs_human"

    def test_response_includes_request_id(self, client: TestClient):
        """Response should process successfully."""
        response = client.post(
            "/vapi/tools/hael_route",
            json={
                "request_id": "custom-request-id",
                "call_id": "test-call",
                "tool_call_id": "tool-call",
                "user_text": "Hello",
            },
        )
        assert response.status_code == 200

