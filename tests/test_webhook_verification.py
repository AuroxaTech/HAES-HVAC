"""
HAES HVAC - Webhook Verification Tests

Tests for webhook signature verification.
"""

import hashlib
import hmac
import pytest
import time

from src.utils.webhook_verify import (
    verify_vapi_signature,
    MAX_SIGNATURE_AGE_SECONDS,
)


class TestVapiSignatureVerification:
    """Tests for Vapi webhook signature verification."""

    def test_valid_signature_without_timestamp(self):
        """Should verify valid signature without timestamp."""
        body = b'{"test": "data"}'
        secret = "test-secret"
        
        # Generate signature
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        assert verify_vapi_signature(body, expected, secret=secret) is True

    def test_valid_signature_with_timestamp(self):
        """Should verify valid signature with timestamp."""
        body = b'{"test": "data"}'
        secret = "test-secret"
        timestamp = str(int(time.time()))
        
        # Generate signature with timestamp
        payload = f"{timestamp}.".encode() + body
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        assert verify_vapi_signature(body, expected, timestamp, secret) is True

    def test_invalid_signature_rejected(self):
        """Should reject invalid signature."""
        body = b'{"test": "data"}'
        secret = "test-secret"
        wrong_signature = "invalid" * 8
        
        assert verify_vapi_signature(body, wrong_signature, secret=secret) is False

    def test_signature_with_sha256_prefix(self):
        """Should handle sha256= prefix in signature."""
        body = b'{"test": "data"}'
        secret = "test-secret"
        
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        prefixed = f"sha256={expected}"
        
        assert verify_vapi_signature(body, prefixed, secret=secret) is True

    def test_expired_timestamp_rejected(self, mocker):
        """Should reject signature with old timestamp."""
        body = b'{"test": "data"}'
        secret = "test-secret"
        old_timestamp = str(int(time.time()) - MAX_SIGNATURE_AGE_SECONDS - 100)
        
        # Generate valid signature
        payload = f"{old_timestamp}.".encode() + body
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        
        assert verify_vapi_signature(body, signature, old_timestamp, secret) is False

    def test_case_insensitive_comparison(self):
        """Signature comparison should be case insensitive."""
        body = b'{"test": "data"}'
        secret = "test-secret"
        
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        upper_case = expected.upper()
        
        assert verify_vapi_signature(body, upper_case, secret=secret) is True

    def test_empty_body(self):
        """Should handle empty body."""
        body = b""
        secret = "test-secret"
        
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        
        assert verify_vapi_signature(body, expected, secret=secret) is True

    def test_no_secret_in_development(self, mocker):
        """Should skip verification in development without secret."""
        mock_settings = mocker.MagicMock()
        mock_settings.VAPI_WEBHOOK_SECRET = ""
        mock_settings.is_production = False
        
        mocker.patch(
            "src.utils.webhook_verify.get_settings",
            return_value=mock_settings,
        )
        
        # Should return True (skip verification)
        assert verify_vapi_signature(b"data", "invalid") is True

    def test_no_secret_in_production_fails(self, mocker):
        """Should fail in production without secret."""
        mock_settings = mocker.MagicMock()
        mock_settings.VAPI_WEBHOOK_SECRET = ""
        mock_settings.is_production = True
        
        mocker.patch(
            "src.utils.webhook_verify.get_settings",
            return_value=mock_settings,
        )
        
        # Should return False (verification failed)
        assert verify_vapi_signature(b"data", "invalid") is False

