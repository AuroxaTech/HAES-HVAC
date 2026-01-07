"""
HAES HVAC - Health Endpoint Tests

Tests for the core health and metadata endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for the root (/) endpoint."""

    def test_root_returns_200(self, client: TestClient):
        """Root endpoint should return HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_service_name(self, client: TestClient):
        """Root endpoint should return service name."""
        response = client.get("/")
        data = response.json()
        assert "service" in data
        assert data["service"] == "HAES HVAC API"

    def test_root_returns_version(self, client: TestClient):
        """Root endpoint should return version."""
        response = client.get("/")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_root_returns_environment(self, client: TestClient):
        """Root endpoint should return environment."""
        response = client.get("/")
        data = response.json()
        assert "environment" in data
        assert data["environment"] in ("development", "production")


class TestHealthEndpoint:
    """Tests for the health (/health) endpoint."""

    def test_health_returns_200(self, client: TestClient):
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status(self, client: TestClient):
        """Health endpoint should return overall status."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_health_returns_database_component(self, client: TestClient):
        """Health endpoint should return database component status."""
        response = client.get("/health")
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]
        assert "status" in data["components"]["database"]


class TestMetricsEndpoint:
    """Tests for the metrics (/monitoring/metrics) endpoint."""

    def test_metrics_returns_200(self, client: TestClient):
        """Metrics endpoint should return HTTP 200."""
        response = client.get("/monitoring/metrics")
        assert response.status_code == 200

    def test_metrics_returns_uptime(self, client: TestClient):
        """Metrics endpoint should return uptime."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_metrics_returns_requests_total(self, client: TestClient):
        """Metrics endpoint should return requests total."""
        response = client.get("/monitoring/metrics")
        data = response.json()
        assert "requests_total" in data
        assert isinstance(data["requests_total"], int)
        assert data["requests_total"] >= 0


class TestRequestId:
    """Tests for request ID handling."""

    def test_response_includes_request_id_header(self, client: TestClient):
        """Response should include X-Request-Id header."""
        response = client.get("/")
        assert "X-Request-Id" in response.headers
        assert len(response.headers["X-Request-Id"]) > 0

    def test_request_id_is_propagated(self, client: TestClient):
        """Provided request ID should be propagated in response."""
        custom_id = "test-request-id-12345"
        response = client.get("/", headers={"X-Request-Id": custom_id})
        assert response.headers.get("X-Request-Id") == custom_id

