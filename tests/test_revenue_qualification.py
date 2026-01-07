"""
HAES HVAC - REVENUE Brain Qualification Tests

Tests for lead qualification rules.
"""

import pytest

from src.hael.schema import UrgencyLevel
from src.brains.revenue.qualification import qualify_lead, get_response_time_goal
from src.brains.revenue.schema import LeadQualification


class TestLeadQualification:
    """Tests for lead qualification rules."""

    def test_emergency_urgency_is_hot(self):
        """Emergency urgency should be hot."""
        qual, conf, reason = qualify_lead(
            problem_description="AC broken",
            timeline=None,
            urgency_level=UrgencyLevel.EMERGENCY,
        )
        assert qual == LeadQualification.HOT
        assert conf >= 0.9

    def test_ready_today_is_hot(self):
        """Ready to schedule today should be hot."""
        qual, conf, reason = qualify_lead(
            problem_description="Need AC fixed",
            timeline="today",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert qual == LeadQualification.HOT

    def test_price_shopping_is_cold(self):
        """Price shopping should be cold."""
        qual, conf, reason = qualify_lead(
            problem_description="Getting quotes",
            timeline="just looking",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert qual == LeadQualification.COLD

    def test_this_week_is_warm(self):
        """This week timeline should be warm."""
        qual, conf, reason = qualify_lead(
            problem_description="Need repair",
            timeline="this week",
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert qual == LeadQualification.WARM

    def test_default_is_warm_low_confidence(self):
        """Unknown context defaults to warm with low confidence."""
        qual, conf, reason = qualify_lead(
            problem_description="Hello",
            timeline=None,
            urgency_level=UrgencyLevel.UNKNOWN,
        )
        assert qual == LeadQualification.WARM
        assert conf <= 0.6


class TestResponseTimeGoals:
    """Tests for response time goals."""

    def test_hot_lead_15_minutes(self):
        """Hot leads should have 15-minute goal."""
        assert get_response_time_goal(LeadQualification.HOT) == 15

    def test_warm_lead_60_minutes(self):
        """Warm leads should have 1-hour goal."""
        assert get_response_time_goal(LeadQualification.WARM) == 60

    def test_cold_lead_240_minutes(self):
        """Cold leads should have 4-hour goal."""
        assert get_response_time_goal(LeadQualification.COLD) == 240

