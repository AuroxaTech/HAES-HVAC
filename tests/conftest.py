"""
HAES HVAC Test Configuration

Pytest fixtures and configuration for the test suite.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/haes_test")


@pytest.fixture(scope="session")
def app():
    """Get FastAPI application instance."""
    from src.main import app
    return app


@pytest.fixture(scope="session")
def client(app):
    """Get test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """
    Get a database session for testing.

    Note: Requires DATABASE_URL to be set and database to be running.
    """
    from src.db.session import get_session_factory

    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

