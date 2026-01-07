"""
HAES HVAC - Odoo Client Unit Tests

Unit tests for OdooClient with mocked HTTP responses.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.odoo import OdooClient, _redact_payload
from src.utils.errors import OdooAuthError, OdooRPCError, OdooTransportError


class TestRedactPayload:
    """Tests for payload redaction."""

    def test_redacts_password_field(self):
        """Should redact password field."""
        data = {"login": "user", "password": "secret123"}
        result = _redact_payload(data)
        assert result["login"] == "user"
        assert result["password"] == "***REDACTED***"

    def test_redacts_api_key_field(self):
        """Should redact api_key field."""
        data = {"api_key": "secret", "other": "value"}
        result = _redact_payload(data)
        assert result["api_key"] == "***REDACTED***"
        assert result["other"] == "value"

    def test_redacts_nested_fields(self):
        """Should redact nested sensitive fields."""
        data = {"outer": {"password": "secret"}}
        result = _redact_payload(data)
        assert result["outer"]["password"] == "***REDACTED***"

    def test_redacts_in_lists(self):
        """Should redact sensitive fields in lists."""
        data = [{"password": "secret1"}, {"password": "secret2"}]
        result = _redact_payload(data)
        assert result[0]["password"] == "***REDACTED***"
        assert result[1]["password"] == "***REDACTED***"


class TestOdooClientInit:
    """Tests for OdooClient initialization."""

    def test_stores_config(self):
        """Should store configuration correctly."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user@example.com",
            password="secret",
            timeout_seconds=60,
            verify_ssl=False,
        )
        assert client.base_url == "https://example.odoo.com"
        assert client.db == "testdb"
        assert client.username == "user@example.com"
        assert client.timeout_seconds == 60
        assert client.verify_ssl is False

    def test_strips_trailing_slash(self):
        """Should strip trailing slash from base_url."""
        client = OdooClient(
            base_url="https://example.odoo.com/",
            db="testdb",
            username="user",
            password="pass",
        )
        assert client.base_url == "https://example.odoo.com"

    def test_not_authenticated_initially(self):
        """Should not be authenticated initially."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )
        assert client.is_authenticated is False
        assert client.uid is None


class TestOdooClientAuthenticate:
    """Tests for OdooClient.authenticate()."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Should authenticate successfully and return uid."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user@example.com",
            password="secret",
        )

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"uid": 42, "session_id": "abc123"},
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            uid = await client.authenticate()

            assert uid == 42
            assert client.is_authenticated is True
            assert client.uid == 42

    @pytest.mark.asyncio
    async def test_authenticate_failure_invalid_credentials(self):
        """Should raise OdooAuthError on invalid credentials."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user@example.com",
            password="wrong",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"uid": False},  # Odoo returns False on auth failure
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(OdooAuthError) as exc_info:
                await client.authenticate()

            assert "Invalid database, username, or password" in str(exc_info.value)


class TestOdooClientCallKw:
    """Tests for OdooClient.call_kw()."""

    @pytest.mark.asyncio
    async def test_call_kw_requires_authentication(self):
        """Should raise error if not authenticated."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )

        with pytest.raises(OdooRPCError) as exc_info:
            await client.call_kw("res.partner", "search", [[]])

        assert "Not authenticated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_kw_success(self):
        """Should call Odoo method successfully."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )
        client._uid = 42  # Simulate authenticated state

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [1, 2, 3],
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.call_kw("res.partner", "search", [[]])

            assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_call_kw_error_includes_model_method(self):
        """Should include model and method in RPC error."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )
        client._uid = 42

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "message": "Access denied",
                "data": {"name": "odoo.exceptions.AccessDenied"},
            },
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            with pytest.raises(OdooRPCError) as exc_info:
                await client.call_kw("res.partner", "create", [{"name": "Test"}])

            assert exc_info.value.details.get("model") == "res.partner"
            assert exc_info.value.details.get("method") == "create"


class TestOdooClientConvenienceMethods:
    """Tests for OdooClient convenience methods."""

    @pytest.mark.asyncio
    async def test_search_read(self):
        """Should call search_read correctly."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )
        client._uid = 42

        expected_result = [{"id": 1, "name": "Test"}]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": expected_result,
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.search_read(
                "res.partner",
                [("is_company", "=", True)],
                fields=["name"],
                limit=10,
            )

            assert result == expected_result

    @pytest.mark.asyncio
    async def test_fields_get(self):
        """Should call fields_get correctly."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )
        client._uid = 42

        expected_result = {
            "name": {"type": "char", "string": "Name"},
            "email": {"type": "char", "string": "Email"},
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": expected_result,
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response
            mock_get_client.return_value = mock_http_client

            result = await client.fields_get("res.partner", attributes=["type", "string"])

            assert result == expected_result


class TestOdooClientClose:
    """Tests for OdooClient.close()."""

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Should close the HTTP client."""
        client = OdooClient(
            base_url="https://example.odoo.com",
            db="testdb",
            username="user",
            password="pass",
        )

        # Create a mock client
        mock_http_client = AsyncMock()
        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_called_once()
        assert client._client is None

