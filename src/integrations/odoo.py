"""
HAES HVAC - Odoo Integration Client

Async HTTP client for Odoo 18 Enterprise via JSON-RPC.

Usage:
    client = OdooClient(
        base_url="https://example.odoo.com",
        db="mydb",
        username="user@example.com",
        password="api_key_or_password",
    )
    await client.authenticate()
    users = await client.search_read("res.users", [], fields=["name", "login"])
    await client.close()
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import httpx

from src.utils.errors import OdooAuthError, OdooRPCError, OdooTransportError

logger = logging.getLogger(__name__)

# Fields to redact from logs
REDACT_FIELDS = {"password", "api_key", "token", "Authorization", "secret"}


def _redact_payload(data: Any) -> Any:
    """Redact sensitive fields from a payload for logging."""
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if k.lower() in {f.lower() for f in REDACT_FIELDS} else _redact_payload(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [_redact_payload(item) for item in data]
    return data


class OdooClient:
    """
    Async client for Odoo JSON-RPC API.

    Provides authentication and common CRUD operations via JSON-RPC.
    """

    def __init__(
        self,
        base_url: str,
        db: str,
        username: str,
        password: str,
        timeout_seconds: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        """
        Initialize the Odoo client.

        Args:
            base_url: Odoo instance URL (e.g., https://mycompany.odoo.com)
            db: Odoo database name
            username: Odoo username/email
            password: Odoo password or API key
            timeout_seconds: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.db = db
        self.username = username
        self._password = password  # Never logged
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl

        self._uid: int | None = None
        self._client: httpx.AsyncClient | None = None
        self._request_id = 0

    @property
    def uid(self) -> int | None:
        """Get the authenticated user ID."""
        return self._uid

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._uid is not None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                verify=self.verify_ssl,
            )
        return self._client

    def _next_request_id(self) -> int:
        """Generate the next JSON-RPC request ID."""
        self._request_id += 1
        return self._request_id

    async def _json_rpc(self, endpoint: str, params: dict[str, Any]) -> Any:
        """
        Make a JSON-RPC call to Odoo.

        Args:
            endpoint: API endpoint (e.g., /web/session/authenticate)
            params: Request parameters

        Returns:
            The 'result' field from the JSON-RPC response

        Raises:
            OdooTransportError: On network/connection errors
            OdooRPCError: On JSON-RPC errors
        """
        client = self._get_client()
        url = f"{self.base_url}{endpoint}"
        request_id = self._next_request_id()

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": request_id,
        }

        # Log request (redacted)
        logger.debug(
            f"Odoo RPC request: {endpoint} | params={_redact_payload(params)}"
        )

        start_time = datetime.now()

        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except httpx.TimeoutException as e:
            logger.error(f"Odoo request timeout: {endpoint}")
            raise OdooTransportError(f"Odoo request timeout: {e}")
        except httpx.ConnectError as e:
            logger.error(f"Odoo connection error: {endpoint} - {e}")
            raise OdooTransportError(f"Odoo connection error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Odoo request error: {endpoint} - {e}")
            raise OdooTransportError(f"Odoo request error: {e}")

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Log response metadata
        logger.debug(
            f"Odoo RPC response: {endpoint} | status={response.status_code} | duration_ms={duration_ms:.2f}"
        )

        # Check HTTP status
        if response.status_code != 200:
            logger.error(f"Odoo HTTP error: {response.status_code}")
            raise OdooTransportError(f"Odoo HTTP error: {response.status_code}")

        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Odoo invalid JSON response: {e}")
            raise OdooRPCError(f"Invalid JSON response from Odoo: {e}")

        # Check for JSON-RPC error
        if "error" in data:
            error = data["error"]
            error_message = error.get("message", "Unknown Odoo error")
            error_data = error.get("data", {})
            
            # Log full error structure for debugging
            logger.error(
                f"Odoo RPC error - Full error structure: {json.dumps(error, indent=2, default=str)}"
            )
            logger.error(f"Odoo RPC error message: {error_message}")
            logger.error(f"Odoo RPC error data: {json.dumps(error_data, indent=2, default=str)}")
            
            raise OdooRPCError(
                message=error_message,
                odoo_error=error_data,
            )

        return data.get("result")

    async def authenticate(self) -> int:
        """
        Authenticate with Odoo and store the session.

        Returns:
            User ID (uid) on successful authentication

        Raises:
            OdooAuthError: On authentication failure
            OdooTransportError: On connection errors
        """
        logger.info(f"Authenticating to Odoo: {self.base_url} db={self.db} user={self.username}")

        try:
            result = await self._json_rpc(
                "/web/session/authenticate",
                {
                    "db": self.db,
                    "login": self.username,
                    "password": self._password,
                },
            )
        except OdooRPCError as e:
            raise OdooAuthError(f"Authentication failed: {e.message}")

        if not result or not result.get("uid"):
            raise OdooAuthError(
                "Authentication failed: Invalid database, username, or password"
            )

        self._uid = result["uid"]
        logger.info(f"Odoo authentication successful: uid={self._uid}")
        return self._uid

    async def call_kw(
        self,
        model: str,
        method: str,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> Any:
        """
        Call a method on an Odoo model via JSON-RPC.

        Args:
            model: Odoo model name (e.g., res.partner)
            method: Method name (e.g., search_read)
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Method result

        Raises:
            OdooRPCError: On RPC errors
        """
        if not self.is_authenticated:
            raise OdooRPCError(
                message="Not authenticated. Call authenticate() first.",
                model=model,
                method=method,
            )

        args = args or []
        kwargs = kwargs or {}

        try:
            result = await self._json_rpc(
                "/web/dataset/call_kw",
                {
                    "model": model,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs,
                },
            )
            return result
        except OdooRPCError as e:
            # Add model/method context to error
            raise OdooRPCError(
                message=e.message,
                model=model,
                method=method,
                odoo_error=e.details.get("odoo_error"),
            )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def search(
        self,
        model: str,
        domain: list,
        offset: int = 0,
        limit: int = 0,
        order: str | None = None,
    ) -> list[int]:
        """
        Search for record IDs matching a domain.

        Args:
            model: Odoo model name
            domain: Search domain (list of tuples)
            offset: Number of records to skip
            limit: Maximum number of records (0 = no limit)
            order: Sort order (e.g., "name asc")

        Returns:
            List of matching record IDs
        """
        kwargs: dict[str, Any] = {"offset": offset}
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order

        return await self.call_kw(model, "search", [domain], kwargs)

    async def read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None,
    ) -> list[dict]:
        """
        Read records by IDs.

        Args:
            model: Odoo model name
            ids: List of record IDs to read
            fields: Fields to read (None = all fields)

        Returns:
            List of record dictionaries
        """
        kwargs = {}
        if fields:
            kwargs["fields"] = fields
        return await self.call_kw(model, "read", [ids], kwargs)

    async def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str] | None = None,
        offset: int = 0,
        limit: int = 0,
        order: str | None = None,
    ) -> list[dict]:
        """
        Search and read records in one call.

        Args:
            model: Odoo model name
            domain: Search domain
            fields: Fields to read
            offset: Number of records to skip
            limit: Maximum number of records
            order: Sort order

        Returns:
            List of record dictionaries
        """
        kwargs: dict[str, Any] = {"offset": offset}
        if fields:
            kwargs["fields"] = fields
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order

        return await self.call_kw(model, "search_read", [domain], kwargs)

    async def create(self, model: str, values: dict) -> int:
        """
        Create a new record.

        Args:
            model: Odoo model name
            values: Field values for the new record

        Returns:
            ID of the created record
        """
        return await self.call_kw(model, "create", [values])

    async def write(self, model: str, ids: list[int], values: dict) -> bool:
        """
        Update existing records.

        Args:
            model: Odoo model name
            ids: Record IDs to update
            values: Field values to update

        Returns:
            True on success
        """
        return await self.call_kw(model, "write", [ids, values])

    async def unlink(self, model: str, ids: list[int]) -> bool:
        """
        Delete records.

        Args:
            model: Odoo model name
            ids: Record IDs to delete

        Returns:
            True on success
        """
        return await self.call_kw(model, "unlink", [ids])

    async def fields_get(
        self,
        model: str,
        attributes: list[str] | None = None,
    ) -> dict:
        """
        Get field definitions for a model.

        Args:
            model: Odoo model name
            attributes: Field attributes to return (e.g., ["string", "type"])

        Returns:
            Dictionary of field definitions
        """
        kwargs = {}
        if attributes:
            kwargs["attributes"] = attributes
        return await self.call_kw(model, "fields_get", [], kwargs)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Odoo client closed")


# =============================================================================
# Factory Function
# =============================================================================


def create_odoo_client_from_settings() -> OdooClient:
    """
    Create an OdooClient from application settings.

    Returns:
        Configured OdooClient instance (not yet authenticated)
    """
    from src.config.settings import get_settings

    settings = get_settings()

    if not settings.ODOO_BASE_URL:
        raise ValueError("ODOO_BASE_URL is not configured")
    if not settings.ODOO_DB:
        raise ValueError("ODOO_DB is not configured")
    if not settings.ODOO_USERNAME:
        raise ValueError("ODOO_USERNAME is not configured")
    if not settings.ODOO_PASSWORD:
        raise ValueError("ODOO_PASSWORD is not configured")

    return OdooClient(
        base_url=settings.ODOO_BASE_URL,
        db=settings.ODOO_DB,
        username=settings.ODOO_USERNAME,
        password=settings.ODOO_PASSWORD,
        timeout_seconds=settings.ODOO_TIMEOUT_SECONDS,
        verify_ssl=settings.ODOO_VERIFY_SSL,
    )

