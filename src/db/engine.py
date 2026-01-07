"""
HAES HVAC Database Engine

SQLAlchemy engine configuration for PostgreSQL.
"""

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine instance (cached).

    Returns:
        Configured SQLAlchemy Engine
    """
    settings = get_settings()

    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,  # Enable connection health checks
        echo=settings.ENVIRONMENT == "development" and settings.LOG_LEVEL == "DEBUG",
    )

    return engine


def check_database_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

