"""
HAES HVAC - Idempotency Utilities

Request deduplication using database-backed idempotency keys.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import IdempotencyKey

logger = logging.getLogger(__name__)

# Default expiration time for idempotency keys (24 hours)
DEFAULT_EXPIRATION_HOURS = 24


def generate_key_hash(scope: str, key_parts: list[str]) -> str:
    """
    Generate a deterministic hash from key parts.

    Args:
        scope: The scope/namespace for the key (e.g., "vapi", "chat")
        key_parts: List of strings to hash together

    Returns:
        32-character hex hash
    """
    combined = f"{scope}:{':'.join(str(p) for p in key_parts)}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


class IdempotencyChecker:
    """
    Handles idempotency checking and response caching.

    Usage:
        checker = IdempotencyChecker(session)
        
        # Check if already processed
        existing = checker.get_existing(scope, key)
        if existing:
            return existing["response"]
        
        # Mark as in progress
        checker.start(scope, key)
        
        # Process...
        result = do_work()
        
        # Mark complete
        checker.complete(scope, key, result)
    """

    def __init__(self, session: Session):
        self.session = session

    def get_existing(
        self,
        scope: str,
        key: str,
    ) -> dict | None:
        """
        Check if an idempotency key already exists and has a response.

        Args:
            scope: The key scope (e.g., "vapi_tool", "chat_message")
            key: The unique key within the scope

        Returns:
            The cached response dict if exists and completed, None otherwise
        """
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.scope == scope,
            IdempotencyKey.key == key,
        )
        record = self.session.execute(stmt).scalar_one_or_none()

        if not record:
            return None

        # Check if expired
        if record.expires_at and record.expires_at < datetime.now(timezone.utc):
            logger.debug(f"Idempotency key expired: {scope}:{key}")
            return None

        # Check if completed
        if record.status == "completed" and record.response_json:
            logger.info(f"Idempotency hit: returning cached response for {scope}:{key}")
            return record.response_json

        # If in_progress, we could wait or return error
        if record.status == "in_progress":
            logger.warning(f"Idempotency key in progress: {scope}:{key}")
            # Return a "retry later" indicator
            return {"_idempotency_status": "in_progress"}

        return None

    def start(
        self,
        scope: str,
        key: str,
        expiration_hours: int = DEFAULT_EXPIRATION_HOURS,
    ) -> IdempotencyKey:
        """
        Mark an idempotency key as in progress.

        Args:
            scope: The key scope
            key: The unique key
            expiration_hours: Hours until the key expires

        Returns:
            The created idempotency key record
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)

        record = IdempotencyKey(
            scope=scope,
            key=key,
            status="in_progress",
            expires_at=expires_at,
        )
        self.session.add(record)
        self.session.commit()
        logger.debug(f"Started idempotency key: {scope}:{key}")
        return record

    def complete(
        self,
        scope: str,
        key: str,
        response: dict[str, Any],
    ) -> None:
        """
        Mark an idempotency key as completed with the response.

        Args:
            scope: The key scope
            key: The unique key
            response: The response to cache
        """
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.scope == scope,
            IdempotencyKey.key == key,
        )
        record = self.session.execute(stmt).scalar_one_or_none()

        if record:
            record.status = "completed"
            record.response_json = response
            record.response_hash = hashlib.sha256(
                json.dumps(response, sort_keys=True).encode()
            ).hexdigest()[:64]
            self.session.commit()
            logger.debug(f"Completed idempotency key: {scope}:{key}")
        else:
            logger.warning(f"No idempotency key found to complete: {scope}:{key}")

    def fail(
        self,
        scope: str,
        key: str,
        error: str,
    ) -> None:
        """
        Mark an idempotency key as failed.

        Args:
            scope: The key scope
            key: The unique key
            error: The error message
        """
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.scope == scope,
            IdempotencyKey.key == key,
        )
        record = self.session.execute(stmt).scalar_one_or_none()

        if record:
            record.status = "failed"
            record.response_json = {"error": error}
            self.session.commit()
            logger.debug(f"Failed idempotency key: {scope}:{key}")


def check_idempotency(
    session: Session,
    scope: str,
    key_parts: list[str],
) -> tuple[str, dict | None]:
    """
    Convenience function to check idempotency.

    Args:
        session: Database session
        scope: The key scope
        key_parts: Parts to generate the key from

    Returns:
        Tuple of (generated_key, existing_response or None)
    """
    key = generate_key_hash(scope, key_parts)
    checker = IdempotencyChecker(session)
    existing = checker.get_existing(scope, key)
    return key, existing

