"""
HAES HVAC - Idempotency Tests

Tests for idempotency key generation and checking.
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.utils.idempotency import (
    IdempotencyChecker,
    generate_key_hash,
    check_idempotency,
)


class TestKeyHashGeneration:
    """Tests for idempotency key hash generation."""

    def test_same_inputs_same_hash(self):
        """Same inputs should produce the same hash."""
        hash1 = generate_key_hash("scope", ["part1", "part2"])
        hash2 = generate_key_hash("scope", ["part1", "part2"])
        assert hash1 == hash2

    def test_different_scope_different_hash(self):
        """Different scopes should produce different hashes."""
        hash1 = generate_key_hash("scope1", ["part1"])
        hash2 = generate_key_hash("scope2", ["part1"])
        assert hash1 != hash2

    def test_different_parts_different_hash(self):
        """Different parts should produce different hashes."""
        hash1 = generate_key_hash("scope", ["part1"])
        hash2 = generate_key_hash("scope", ["part2"])
        assert hash1 != hash2

    def test_hash_is_32_chars(self):
        """Hash should be 32 characters."""
        hash_val = generate_key_hash("scope", ["part"])
        assert len(hash_val) == 32

    def test_hash_is_hex(self):
        """Hash should be valid hexadecimal."""
        hash_val = generate_key_hash("scope", ["part"])
        int(hash_val, 16)  # Should not raise

    def test_order_matters(self):
        """Order of parts should affect the hash."""
        hash1 = generate_key_hash("scope", ["a", "b"])
        hash2 = generate_key_hash("scope", ["b", "a"])
        assert hash1 != hash2


class TestIdempotencyChecker:
    """Tests for IdempotencyChecker class."""

    @pytest.fixture
    def mock_session(self, mocker):
        """Create a mock database session."""
        return mocker.MagicMock()

    def test_get_existing_returns_none_for_new_key(self, mock_session):
        """Should return None for a key that doesn't exist."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        checker = IdempotencyChecker(mock_session)
        result = checker.get_existing("scope", "key")
        
        assert result is None

    def test_get_existing_returns_response_for_completed_key(self, mock_session, mocker):
        """Should return cached response for completed key."""
        mock_record = mocker.MagicMock()
        mock_record.status = "completed"
        mock_record.response_json = {"result": "success"}
        mock_record.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        checker = IdempotencyChecker(mock_session)
        result = checker.get_existing("scope", "key")
        
        assert result == {"result": "success"}

    def test_get_existing_returns_in_progress_status(self, mock_session, mocker):
        """Should return in_progress status for ongoing request."""
        mock_record = mocker.MagicMock()
        mock_record.status = "in_progress"
        mock_record.response_json = None
        mock_record.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        checker = IdempotencyChecker(mock_session)
        result = checker.get_existing("scope", "key")
        
        assert result == {"_idempotency_status": "in_progress"}

    def test_get_existing_returns_none_for_expired_key(self, mock_session, mocker):
        """Should return None for expired key."""
        mock_record = mocker.MagicMock()
        mock_record.status = "completed"
        mock_record.response_json = {"result": "success"}
        mock_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        checker = IdempotencyChecker(mock_session)
        result = checker.get_existing("scope", "key")
        
        assert result is None

    def test_start_creates_record(self, mock_session):
        """Start should create a new record."""
        checker = IdempotencyChecker(mock_session)
        
        record = checker.start("scope", "key")
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert record.scope == "scope"
        assert record.key == "key"
        assert record.status == "in_progress"

    def test_complete_updates_record(self, mock_session, mocker):
        """Complete should update record with response."""
        mock_record = mocker.MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        checker = IdempotencyChecker(mock_session)
        checker.complete("scope", "key", {"result": "done"})
        
        assert mock_record.status == "completed"
        assert mock_record.response_json == {"result": "done"}
        mock_session.commit.assert_called()

    def test_fail_updates_record(self, mock_session, mocker):
        """Fail should update record with error."""
        mock_record = mocker.MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        checker = IdempotencyChecker(mock_session)
        checker.fail("scope", "key", "Something went wrong")
        
        assert mock_record.status == "failed"
        assert mock_record.response_json == {"error": "Something went wrong"}
        mock_session.commit.assert_called()

