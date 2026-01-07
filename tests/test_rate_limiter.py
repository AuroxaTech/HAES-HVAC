"""
HAES HVAC - Rate Limiter Tests

Tests for rate limiting functionality.
"""

import pytest
import time
from fastapi.testclient import TestClient

from src.utils.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    get_client_ip,
)


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_allows_requests_under_limit(self):
        """Should allow requests under the limit."""
        config = RateLimitConfig(requests_per_window=5, window_seconds=60)
        limiter = RateLimiter(config)

        for i in range(5):
            allowed, remaining, _ = limiter.is_allowed("test-key")
            assert allowed is True
            assert remaining == 4 - i

    def test_blocks_requests_over_limit(self):
        """Should block requests over the limit."""
        config = RateLimitConfig(requests_per_window=3, window_seconds=60)
        limiter = RateLimiter(config)

        # Exhaust the limit
        for _ in range(3):
            limiter.is_allowed("test-key")

        # Next request should be blocked
        allowed, remaining, retry_after = limiter.is_allowed("test-key")
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_different_keys_independent(self):
        """Different keys should have independent limits."""
        config = RateLimitConfig(requests_per_window=2, window_seconds=60)
        limiter = RateLimiter(config)

        # Exhaust key1
        limiter.is_allowed("key1")
        limiter.is_allowed("key1")
        allowed1, _, _ = limiter.is_allowed("key1")
        assert allowed1 is False

        # key2 should still be allowed
        allowed2, _, _ = limiter.is_allowed("key2")
        assert allowed2 is True

    def test_window_expires(self):
        """Requests should be allowed after window expires."""
        config = RateLimitConfig(requests_per_window=1, window_seconds=1)
        limiter = RateLimiter(config)

        # Use up the limit
        limiter.is_allowed("test-key")
        allowed, _, _ = limiter.is_allowed("test-key")
        assert allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, _, _ = limiter.is_allowed("test-key")
        assert allowed is True

    def test_disabled_limiter_always_allows(self):
        """Disabled limiter should always allow requests."""
        config = RateLimitConfig(enabled=False)
        limiter = RateLimiter(config)

        for _ in range(1000):
            allowed, _, _ = limiter.is_allowed("test-key")
            assert allowed is True

    def test_reset_clears_key(self):
        """Reset should clear a specific key."""
        config = RateLimitConfig(requests_per_window=2, window_seconds=60)
        limiter = RateLimiter(config)

        # Exhaust the limit
        limiter.is_allowed("test-key")
        limiter.is_allowed("test-key")

        # Reset
        limiter.reset("test-key")

        # Should be allowed again
        allowed, _, _ = limiter.is_allowed("test-key")
        assert allowed is True

    def test_clear_all_clears_everything(self):
        """Clear all should clear all keys."""
        config = RateLimitConfig(requests_per_window=1, window_seconds=60)
        limiter = RateLimiter(config)

        # Use up limits for multiple keys
        limiter.is_allowed("key1")
        limiter.is_allowed("key2")

        # Clear all
        limiter.clear_all()

        # Both should be allowed
        allowed1, _, _ = limiter.is_allowed("key1")
        allowed2, _, _ = limiter.is_allowed("key2")
        assert allowed1 is True
        assert allowed2 is True


class TestGetClientIp:
    """Tests for client IP extraction."""

    def test_uses_x_forwarded_for(self, mocker):
        """Should use X-Forwarded-For header if present."""
        mock_request = mocker.MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        
        ip = get_client_ip(mock_request)
        
        assert ip == "192.168.1.1"

    def test_uses_client_host_if_no_header(self, mocker):
        """Should use client.host if no forwarded header."""
        mock_request = mocker.MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"
        
        ip = get_client_ip(mock_request)
        
        assert ip == "127.0.0.1"

    def test_returns_unknown_if_no_client(self, mocker):
        """Should return 'unknown' if no client info available."""
        mock_request = mocker.MagicMock()
        mock_request.headers = {}
        mock_request.client = None
        
        ip = get_client_ip(mock_request)
        
        assert ip == "unknown"


class TestRateLimitMiddlewareIntegration:
    """Integration tests for rate limit middleware."""

    def test_rate_limit_headers_present(self, client: TestClient):
        """Response should include rate limit headers."""
        response = client.post(
            "/chat/message",
            json={"session_id": "test", "user_text": "hello"},
        )
        
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Limit" in response.headers

    def test_health_endpoint_bypasses_rate_limit(self, client: TestClient):
        """Health endpoint should bypass rate limiting."""
        # Health endpoint should always work, no rate limit headers
        response = client.get("/health")
        assert response.status_code == 200

