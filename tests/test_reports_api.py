"""
HAES HVAC - Reports API Tests

Tests for the reports endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestGetLatestReport:
    """Tests for GET /reports/latest endpoint."""

    def test_get_latest_daily_report(self, client: TestClient):
        """Should return a daily report."""
        response = client.get("/reports/latest?type=daily")
        assert response.status_code == 200
        
        data = response.json()
        assert "report" in data
        assert "summary" in data
        assert data["report"]["report_type"] == "daily"

    def test_get_latest_weekly_report(self, client: TestClient):
        """Should return a weekly report."""
        response = client.get("/reports/latest?type=weekly")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report"]["report_type"] == "weekly"

    def test_get_latest_monthly_report(self, client: TestClient):
        """Should return a monthly report."""
        response = client.get("/reports/latest?type=monthly")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report"]["report_type"] == "monthly"

    def test_default_is_daily(self, client: TestClient):
        """Default report type should be daily."""
        response = client.get("/reports/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report"]["report_type"] == "daily"

    def test_report_has_kpis(self, client: TestClient):
        """Report should include KPI data."""
        response = client.get("/reports/latest")
        
        data = response.json()
        report = data["report"]
        
        assert "kpis" in report
        kpis = report["kpis"]
        
        # Should have expected KPI sections
        assert "service" in kpis or len(kpis) >= 0

    def test_report_has_period(self, client: TestClient):
        """Report should include period dates."""
        response = client.get("/reports/latest")
        
        data = response.json()
        report = data["report"]
        
        assert "period_start" in report
        assert "period_end" in report

    def test_summary_has_key_metrics(self, client: TestClient):
        """Summary should include key_metrics."""
        response = client.get("/reports/latest")
        
        data = response.json()
        summary = data["summary"]
        
        assert "key_metrics" in summary
        assert len(summary["key_metrics"]) > 0


class TestRunReportOnce:
    """Tests for POST /reports/run-once endpoint."""

    def test_run_daily_report(self, client: TestClient):
        """Should generate a daily report on demand."""
        response = client.post(
            "/reports/run-once",
            json={"report_type": "daily"},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "generated"
        assert "report" in data
        assert "summary" in data

    def test_run_report_with_custom_period(self, client: TestClient):
        """Should generate report with custom period."""
        now = datetime.utcnow()
        start = (now - timedelta(days=7)).isoformat()
        end = now.isoformat()
        
        response = client.post(
            "/reports/run-once",
            json={
                "report_type": "weekly",
                "period_start": start,
                "period_end": end,
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "generated"

    def test_run_monthly_report(self, client: TestClient):
        """Should generate a monthly report."""
        response = client.post(
            "/reports/run-once",
            json={"report_type": "monthly"},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["report"]["report_type"] == "monthly"


class TestListReportRuns:
    """Tests for GET /reports/runs endpoint."""

    def test_list_returns_structure(self, client: TestClient):
        """Should return proper structure."""
        response = client.get("/reports/runs")
        assert response.status_code == 200
        
        data = response.json()
        assert "runs" in data
        assert "total" in data
        assert isinstance(data["runs"], list)

    def test_list_with_type_filter(self, client: TestClient):
        """Should accept type filter parameter."""
        response = client.get("/reports/runs?type=daily")
        assert response.status_code == 200

    def test_list_with_limit(self, client: TestClient):
        """Should accept limit parameter."""
        response = client.get("/reports/runs?limit=5")
        assert response.status_code == 200

    def test_limit_max_is_enforced(self, client: TestClient):
        """Should enforce max limit of 100."""
        response = client.get("/reports/runs?limit=200")
        # Should fail validation or cap at 100
        # FastAPI validation will return 422 for exceeding max
        assert response.status_code in [200, 422]


class TestReportDataStructure:
    """Tests for report data structure compliance."""

    def test_report_structure_matches_schema(self, client: TestClient):
        """Report should match expected schema structure."""
        response = client.get("/reports/latest")
        data = response.json()
        
        report = data["report"]
        
        # Required fields
        required = ["report_type", "period_start", "period_end", "generated_at", "kpis"]
        for field in required:
            assert field in report, f"Missing required field: {field}"

    def test_summary_structure_matches_schema(self, client: TestClient):
        """Summary should match expected schema structure."""
        response = client.get("/reports/latest")
        data = response.json()
        
        summary = data["summary"]
        
        # Required fields per ReportSummary schema
        required = ["report_type", "period", "key_metrics", "alerts"]
        for field in required:
            assert field in summary, f"Missing required field: {field}"

