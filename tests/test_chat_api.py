"""
HAES HVAC - Chat API Tests

Tests for the chat message endpoint.
"""

import pytest
from fastapi.testclient import TestClient


class TestChatMessage:
    """Tests for the /chat/message endpoint."""

    def test_chat_returns_reply(self, client: TestClient):
        """Chat should return a reply."""
        response = client.post(
            "/chat/message",
            json={
                "session_id": "test-session-123",
                "user_text": "Hello, I need help with my HVAC",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply_text" in data
        assert "action" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"

    def test_service_request_via_chat(self, client: TestClient):
        """Service request via chat should work."""
        response = client.post(
            "/chat/message",
            json={
                "session_id": "test-session-456",
                "user_text": "My AC is broken. Call me at 512-555-9999. I'm in 78702.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] in ["completed", "needs_human"]

    def test_quote_request_via_chat(self, client: TestClient):
        """Quote request via chat should work."""
        response = client.post(
            "/chat/message",
            json={
                "session_id": "test-session-789",
                "user_text": "I want a quote for a new AC. Email: user@example.com. Residential home. Need it this month.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply_text" in data

    def test_unknown_request_via_chat(self, client: TestClient):
        """Unknown request should indicate needs human."""
        response = client.post(
            "/chat/message",
            json={
                "session_id": "test-session-unknown",
                "user_text": "What color is the sky?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "needs_human"

    def test_chat_session_id_preserved(self, client: TestClient):
        """Session ID should be preserved in response."""
        session_id = "unique-session-12345"
        response = client.post(
            "/chat/message",
            json={
                "session_id": session_id,
                "user_text": "Test message",
            },
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

