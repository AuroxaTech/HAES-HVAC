"""
Database URL helpers.

We standardize Postgres URLs to use psycopg v3 (SQLAlchemy driver name: `psycopg`)
to avoid ambiguity and to keep Docker dependencies aligned with `pyproject.toml`.
"""

from __future__ import annotations


def normalize_postgres_url(url: str) -> str:
    """
    Normalize a Postgres SQLAlchemy URL to use psycopg v3.

    - `postgres://...` -> `postgresql+psycopg://...`
    - `postgresql://...` -> `postgresql+psycopg://...`
    - `postgresql+psycopg2://...` -> `postgresql+psycopg://...`
    - already `postgresql+psycopg://...` -> unchanged
    """

    u = (url or "").strip()
    if not u:
        return u

    if u.startswith("postgresql+psycopg://"):
        return u

    if u.startswith("postgresql+psycopg2://"):
        return u.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)

    if u.startswith("postgresql://"):
        return u.replace("postgresql://", "postgresql+psycopg://", 1)

    if u.startswith("postgres://"):
        # Heroku-style shorthand
        return u.replace("postgres://", "postgresql+psycopg://", 1)

    return u

