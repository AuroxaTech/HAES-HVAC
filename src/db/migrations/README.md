# HAES HVAC Database Migrations

This directory contains Alembic database migrations for the HAES HVAC system.

## Running Migrations

Apply all pending migrations:
```bash
uv run alembic upgrade head
```

Create a new migration:
```bash
uv run alembic revision --autogenerate -m "description"
```

Rollback one migration:
```bash
uv run alembic downgrade -1
```

Show current revision:
```bash
uv run alembic current
```

Show migration history:
```bash
uv run alembic history
```

## Tables

The foundational tables created by migrations:

1. **idempotency_keys** - Request deduplication
2. **audit_log** - Action audit trail
3. **jobs** - Background job queue
4. **report_runs** - Report artifacts (Module 9)
5. **report_deliveries** - Report delivery tracking (Module 9)

