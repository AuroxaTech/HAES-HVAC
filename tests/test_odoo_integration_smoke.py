"""
HAES HVAC - Odoo Integration Smoke Tests

Real Odoo integration tests - skipped by default.
Run with: RUN_ODOO_INTEGRATION_TESTS=1 uv run pytest -k odoo_smoke
"""

import os
import pytest

from src.config.settings import get_settings

# Skip all tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_ODOO_INTEGRATION_TESTS") != "1",
    reason="Odoo integration tests disabled. Set RUN_ODOO_INTEGRATION_TESTS=1 to enable."
)


@pytest.fixture
async def odoo_client():
    """Create an authenticated Odoo client."""
    from src.integrations.odoo import create_odoo_client_from_settings

    client = create_odoo_client_from_settings()
    await client.authenticate()
    yield client
    await client.close()


class TestOdooIntegrationSmoke:
    """Smoke tests for real Odoo integration."""

    @pytest.mark.asyncio
    async def test_authenticate(self, odoo_client):
        """Should authenticate successfully."""
        assert odoo_client.is_authenticated
        assert odoo_client.uid is not None
        assert odoo_client.uid > 0

    @pytest.mark.asyncio
    async def test_read_current_user(self, odoo_client):
        """Should read current user info."""
        users = await odoo_client.read(
            "res.users",
            [odoo_client.uid],
            fields=["name", "login"],
        )
        assert len(users) == 1
        assert "name" in users[0]
        assert "login" in users[0]

    @pytest.mark.asyncio
    async def test_search_partners(self, odoo_client):
        """Should search for partners."""
        partners = await odoo_client.search_read(
            "res.partner",
            [],
            fields=["name"],
            limit=5,
        )
        assert isinstance(partners, list)
        # There should be at least one partner (the company)
        assert len(partners) >= 1

    @pytest.mark.asyncio
    async def test_fields_get_partner(self, odoo_client):
        """Should get field definitions for res.partner."""
        fields = await odoo_client.fields_get(
            "res.partner",
            attributes=["type", "string"],
        )
        assert isinstance(fields, dict)
        assert "name" in fields
        assert "email" in fields

