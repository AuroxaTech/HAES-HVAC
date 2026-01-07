"""
HAES HVAC - Security Tests

Tests for security headers and utilities.
"""

import pytest
from fastapi.testclient import TestClient

from src.utils.security import mask_sensitive_data, validate_environment_secrets


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_x_content_type_options_present(self, client: TestClient):
        """Response should include X-Content-Type-Options header."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_present(self, client: TestClient):
        """Response should include X-Frame-Options header."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection_present(self, client: TestClient):
        """Response should include X-XSS-Protection header."""
        response = client.get("/")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy_present(self, client: TestClient):
        """Response should include Referrer-Policy header."""
        response = client.get("/")
        assert "strict-origin" in response.headers.get("Referrer-Policy", "")

    def test_permissions_policy_present(self, client: TestClient):
        """Response should include Permissions-Policy header."""
        response = client.get("/")
        permissions = response.headers.get("Permissions-Policy", "")
        assert "camera=()" in permissions
        assert "microphone=()" in permissions


class TestMaskSensitiveData:
    """Tests for sensitive data masking."""

    def test_masks_password_field(self):
        """Should mask password fields."""
        data = {"username": "admin", "password": "secret123"}
        masked = mask_sensitive_data(data)
        
        assert masked["username"] == "admin"
        assert masked["password"] != "secret123"
        assert "****" in masked["password"] or "*" in masked["password"]

    def test_masks_token_field(self):
        """Should mask token fields."""
        data = {"auth_token": "abc123xyz789"}
        masked = mask_sensitive_data(data)
        
        assert masked["auth_token"] != "abc123xyz789"

    def test_masks_api_key_field(self):
        """Should mask API key fields."""
        data = {"api_key": "sk-1234567890"}
        masked = mask_sensitive_data(data)
        
        assert masked["api_key"] != "sk-1234567890"

    def test_preserves_non_sensitive_fields(self):
        """Should preserve non-sensitive fields."""
        data = {"name": "John", "email": "john@example.com"}
        masked = mask_sensitive_data(data)
        
        assert masked["name"] == "John"
        assert masked["email"] == "john@example.com"

    def test_handles_nested_dicts(self):
        """Should handle nested dictionaries."""
        data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "secret",
                },
            }
        }
        masked = mask_sensitive_data(data)
        
        assert masked["user"]["name"] == "John"
        assert masked["user"]["credentials"]["password"] != "secret"

    def test_short_values_fully_masked(self):
        """Short values should be fully masked."""
        data = {"password": "abc"}
        masked = mask_sensitive_data(data)
        
        assert masked["password"] == "****"

    def test_custom_keys_to_mask(self):
        """Should use custom keys to mask."""
        data = {"my_secret_field": "value123"}
        masked = mask_sensitive_data(data, {"my_secret_field"})
        
        assert masked["my_secret_field"] != "value123"


class TestValidateEnvironmentSecrets:
    """Tests for environment secret validation."""

    def test_returns_warnings_for_missing_secrets(self, mocker):
        """Should return warnings for missing production secrets."""
        mock_settings = mocker.MagicMock()
        mock_settings.is_production = True
        mock_settings.VAPI_WEBHOOK_SECRET = ""
        mock_settings.TWILIO_AUTH_TOKEN = ""
        mock_settings.DATABASE_URL = "postgresql://localhost/test"
        
        mocker.patch(
            "src.utils.security.get_settings",
            return_value=mock_settings,
        )
        
        warnings = validate_environment_secrets()
        
        assert len(warnings) >= 2
        assert any("VAPI_WEBHOOK_SECRET" in w for w in warnings)
        assert any("TWILIO_AUTH_TOKEN" in w for w in warnings)

    def test_no_warnings_in_development(self, mocker):
        """Should not return warnings in development."""
        mock_settings = mocker.MagicMock()
        mock_settings.is_production = False
        
        mocker.patch(
            "src.utils.security.get_settings",
            return_value=mock_settings,
        )
        
        warnings = validate_environment_secrets()
        
        assert len(warnings) == 0

