"""
HAES HVAC Database Session Management

Session factory and dependency injection for database sessions.
"""

from collections.abc import Generator
from functools import lru_cache
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from src.db.engine import get_engine


@lru_cache
def get_session_factory() -> sessionmaker:
    """
    Get the SQLAlchemy session factory (cached).

    Returns:
        Configured sessionmaker instance
    """
    engine = get_engine()
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db_session() -> Generator[Session, Any, None]:
    """
    Dependency that provides a database session.

    Yields:
        SQLAlchemy Session instance

    Note:
        Session is automatically closed after the request.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def execute_raw_sql(session: Session, sql: str, params: dict | None = None) -> Any:
    """
    Execute raw SQL query.

    Args:
        session: Database session
        sql: SQL query string
        params: Optional query parameters

    Returns:
        Query result
    """
    result = session.execute(text(sql), params or {})
    return result

