---
name: HAES modular monolith
overview: Build HAES as a single FastAPI service with modular packages (HAEL + 4 brains) following the architecture pattern of the referenced Sally Love repo, integrating with Odoo 18 and deploying to Fly.io with Postgres for idempotency/audit/queueing.
todos:
  - id: module1-foundation
    content: "Module 1: Scaffold HAES FastAPI repo (Sally Love pattern), configure settings/logging, Postgres connectivity, and basic health endpoints."
    status: completed
  - id: module1-context-json
    content: "Module 1: Create `.cursor/context.json` for project context (no secrets) and define an update rule: refresh it after every completed module and any major architectural change."
    status: completed
    dependencies:
      - module1-foundation
  - id: module1-security-redact
    content: "Module 1: Redact secrets from docs and ensure all credentials are environment-based (.env/.password manager)."
    status: completed
    dependencies:
      - module1-foundation
  - id: module1-db
    content: "Module 1: Add Postgres schema/migrations for idempotency keys, audit logs, and background jobs."
    status: completed
    dependencies:
      - module1-foundation
  - id: module2-odoo-integration
    content: "Module 2: Implement `OdooClient` for Odoo 18 (auth + common CRUD/search_read helpers) and a verification script."
    status: completed
    dependencies:
      - module1-foundation
      - module1-security-redact
  - id: module3-hael
    content: "Module 3: Implement HAEL command schema + extraction pipeline + deterministic router (intent→brain) from RDD section 9; add fixtures, scripts, and tests; wire audit/idempotency hooks; update `.cursor/context.json`."
    status: completed
    dependencies:
      - module2-odoo-integration
      - module1-db
  - id: module4-ops
    content: "Module 4: OPS-BRAIN (dispatch/scheduling) consumes HAEL commands for service/schedule/reschedule/cancel/status; applies RDD scheduling rules deterministically; creates/updates Odoo records using Module 2 discovered models; adds scripts/tests; updates `.cursor/context.json`."
    status: completed
    dependencies:
      - module3-hael
  - id: module5-core
    content: "Module 5: CORE-BRAIN (pricing/accounting/compliance/reporting rules) consumes HAEL billing intents; implements deterministic pricing + approvals + invoice policy; integrates with Odoo accounting models discovered in Module 2; adds scripts/tests/fixtures; updates `.cursor/context.json`."
    status: completed
    dependencies:
      - module3-hael
  - id: module6-revenue
    content: "Module 6: REVENUE-BRAIN (leads/quoting/sales follow-up) consumes HAEL `quote_request`; implements deterministic hot/warm/cold qualification + routing + pipeline stage updates from RDD Section 5; integrates with Odoo CRM/Sales models discovered in Module 2; adds scripts/tests/fixtures; updates `.cursor/context.json`."
    status: completed
    dependencies:
      - module3-hael
  - id: module7-people
    content: "Module 7: PEOPLE-BRAIN (HR/onboarding/training/payroll rules) consumes HAEL hiring/onboarding/payroll intents; implements deterministic onboarding/training tracking + payroll/commission rule engine from RDD Section 6; integrates with Odoo HR/Payroll/Project models discovered in Module 2; adds scripts/tests/fixtures; updates `.cursor/context.json`."
    status: completed
    dependencies:
      - module3-hael
  - id: module8-voice-chat
    content: "Module 8: Voice + Chat transport layer. Implement Vapi tool endpoint(s) + Vapi webhooks + website chat API that all invoke HAEL and then the correct brain; add idempotency/correlation; add scripts/tests/fixtures; update `.cursor/context.json`."
    status: completed
    dependencies:
      - module4-ops
      - module5-core
      - module6-revenue
      - module7-people
  - id: module9-kpi
    content: "Module 9: KPI + reporting engine. Compute daily/weekly/monthly (and future quarterly/annual) KPIs from Odoo + internal audit logs; store report artifacts; run schedules via Postgres-backed job runner; deliver via email/SMS/Odoo-note adapters; add scripts/tests/fixtures; update `.cursor/context.json`."
    status: completed
    dependencies:
      - module8-voice-chat
  - id: module10-deploy
    content: "Module 10: Fly.io deployment with Postgres, env configuration, health checks, and operational runbook."
    status: completed
    dependencies:
      - module9-kpi
  - id: module11-qa
    content: "Module 11: Tests (unit + integration), idempotency/retry tests, rate limiting, webhook verification, and production hardening."
    status: completed
    dependencies:
      - module10-deploy
---

# HAES HVAC Development Plan (Module-by-Module, Modular Monolith)

## Reference pattern to follow

- **Codebase pattern/structure**: [`InnovaSalesLab-Dev/sally_love_real_estate`](https://github.com/InnovaSalesLab-Dev/sally_love_real_estate)
- **Requirements**: [`/Users/mac/Developer/HAES HVAC/Requirements.md`](/Users/mac/Developer/HAES%20HVAC/requirements.md)
- **Discovery (RDD)**: [`/Users/mac/Developer/HAES HVAC/HAES - Requirement Discovery Document.md`](/Users/mac/Developer/HAES%20HVAC/HAES%20-%20Requirement%20Discovery%20Document.md)

## Objectives and goals (what “done” means)

1. **Unified modular backend (monolith)**: One FastAPI service, internally modularized into **HAEL + CORE/OPS/REVENUE/PEOPLE**.
2. **Odoo-first automation**: Every accepted command results in correct Odoo reads/writes with consistent data mappings.
3. **Reliable execution**: Idempotency, auditability, retries, and background jobs backed by **Postgres**.
4. **Voice and chat intake**: Vapi voice agent + website chat both flow through the same HAEL command layer.
5. **Automation workflows** (launch criteria from `requirements.md` + RDD):

- Calls book automatically without human intervention (where rules allow)
- Invoices auto-send after service completion (per policy)
- Payroll can run per schedule rules (with approvals)
- Parts can auto-order at reorder points (with approvals)
- KPIs report automatically

6. **Production deployment**: Fly.io deploy with sane ops defaults (health checks, logs, secrets, monitoring).
7. **Project context file (Cursor)**: Maintain `.cursor/context.json` as the single source of truth for current architecture/modules/endpoints/DB schema/env-var names. Update it **after every module** and any major change. **Never store secrets** in it.

## Target system architecture

```mermaid
flowchart TD
  VoiceCaller --> Vapi
  WebsiteVisitor --> ChatWidget

  Vapi --> Api[HAES_API_FastAPI]
  ChatWidget --> Api

  Api --> Hael[HAEL_CommandEngine]
  Hael --> CoreBrain[CoreBrain]
  Hael --> OpsBrain[OpsBrain]
  Hael --> RevenueBrain[RevenueBrain]
  Hael --> PeopleBrain[PeopleBrain]

  CoreBrain --> Odoo[Odoo_API]
  OpsBrain --> Odoo
  RevenueBrain --> Odoo
  PeopleBrain --> Odoo

  Api --> Db[(Postgres)]
  Api --> Jobs[BackgroundJobs]
  Jobs --> Odoo
```



## Module-by-module execution order

We will build sequentially. Each module ends with **clear acceptance criteria** and a “freeze” point before moving on.

- **Module 1 (Foundation)**: Project scaffold + config + Postgres + logging + health.
- **Module 2 (Odoo Integration)**: `OdooClient` + verified read/write primitives + mappings baseline.
- **Module 3 (HAEL)**: Command schemas + deterministic routing + idempotency hooks.
- **Module 4 (OPS-BRAIN)**: Dispatch/scheduling/work orders.
- **Module 5 (CORE-BRAIN)**: Pricing/approvals/invoicing rules/compliance snippets.
- **Module 6 (REVENUE-BRAIN)**: Leads/qualification/pipeline/follow-ups.
- **Module 7 (PEOPLE-BRAIN)**: HR onboarding/training/payroll rules scaffolding.
- **Module 8 (Voice + Chat)**: Vapi endpoints/webhooks + chat endpoint, both wired to HAEL.
- **Module 9 (KPI + Reporting)**: KPI aggregation and automated report delivery.
- **Module 10 (Fly.io Deployment)**: Deploy + runbook + env/secrets.
- **Module 11 (QA + Hardening)**: Tests + rate limiting + webhook security + reliability tests.

---

## Detailed development plan (start with Module 1)

## Module 1: Foundation (repo scaffold + config + Postgres + ops)

### Module objective

Stand up the HAES service skeleton using the Sally Love repo pattern so subsequent modules can be added safely and consistently.

### Scope (explicit deliverables)

By the end of Module 1, the repo will contain **only** the infrastructure needed to support later modules. No Odoo business logic, no HAEL routing logic, and no brain-specific logic beyond folder scaffolding.

- **Project layout**: Create a repo layout that mirrors the referenced Sally Love structure.
- **Runtime**: FastAPI service boots locally with `uv` and via Docker.
- **Configuration**: `pydantic-settings`-based settings object that loads env vars.
- **Database**: Postgres connectivity + migrations for three foundational tables (idempotency, audit, jobs).
- **HTTP surface area** (exact endpoints):
- `GET /` → service metadata (name, environment, version)
- `GET /health` → health + DB connectivity check
- `GET /monitoring/metrics` → placeholder JSON for basic counters

### Security constraints (non-negotiable)

- **No secrets in repo**: we will not create or commit a real `.env` file.
- `.env.example` exists and contains **variable names only** (blank values).
- `.gitignore` includes `.env`.
- Even if credentials exist inside the RDD, **the app will only read credentials from environment variables**.

### Detailed implementation plan (step-by-step, zero ambiguity)

#### 1) Create the exact repo tree (directories and files)

Create the following structure under `/Users/mac/Developer/HAES HVAC/`:

```text
HAES HVAC/
  README.md
  pyproject.toml
  main.py
  Dockerfile
  .dockerignore
  .gitignore
  .env.example
  src/
    __init__.py
    main.py
    config/
      __init__.py
      settings.py
    utils/
      __init__.py
      logger.py
      errors.py
      request_id.py
    db/
      __init__.py
      engine.py
      session.py
      models.py
      migrations/
        README.md
        env.py
        versions/
          (initial migration file)
    monitoring/
      __init__.py
      router.py
      metrics.py
    integrations/
      __init__.py
      (empty placeholders; real clients come in Module 2+)
    hael/
      __init__.py
      (empty placeholders; comes in Module 3)
    brains/
      __init__.py
      core/
        __init__.py
      ops/
        __init__.py
      revenue/
        __init__.py
      people/
        __init__.py
    webhooks/
      __init__.py
      (empty placeholders; comes in Module 8)
    models/
      __init__.py
      (empty placeholders; filled in Module 3+)
  scripts/
    verify_db.py
  tests/
    __init__.py
    test_health.py
```

Notes:

- `main.py` at repo root mirrors the Sally Love pattern: it simply runs `uvicorn` pointed at `src.main:app`.
- `src/main.py` holds the FastAPI `app`, routers, middleware, and exception handlers.

#### 1.5) Create `.cursor/context.json` (project context contract)

Create `.cursor/context.json` under the workspace root `.cursor/` directory. This file must include **only non-sensitive context** (no passwords, no API keys, no tokens).Minimum fields (required):

- `project`: `name`, `repo_root`, `description`
- `architecture`: `type` (monolith), `modules` (HAEL/core/ops/revenue/people), `data_flow_summary`
- `modules_status`: list of `{ module, status, last_updated }`
- `endpoints`: list of `{ method, path, purpose }` for implemented endpoints
- `db_schema`: tables + key columns
- `env_vars`: list of required env var **names only**
- `integrations`: `{ odoo, vapi, twilio, flyio, postgres }` with status/notes
- `assumptions_and_open_questions`: array of strings

Update rule (mandatory):

- Update `.cursor/context.json` at the end of **every module** and after any major change (new endpoints, schema changes, integration decisions).
- Never store credential values in the JSON (only variable names).

#### 2) Define exact dependencies (and why each exists)

In `pyproject.toml`, include only what Module 1 needs:

- **Runtime**:
- `fastapi` (API framework)
- `uvicorn[standard]` (ASGI server)
- `pydantic` + `pydantic-settings` (settings)
- `python-dotenv` (local dev convenience only; reads `.env` if present but `.env` is gitignored)
- **Database**:
- `sqlalchemy` (ORM + engine)
- `psycopg` (Postgres driver; or `psycopg2-binary` if we decide to keep it simpler)
- `alembic` (migrations)
- **Dev/Test**:
- `pytest`
- `httpx` (test client)

We will not add Vapi/Twilio/Odoo SDK dependencies in Module 1; those start in Module 2+.

#### 3) Configuration (exact env vars; no values in repo)

In `src/config/settings.py`, define these settings (names only; values come from environment):

- **Runtime**:
- `ENVIRONMENT` (development|production)
- `HOST` (default `0.0.0.0`)
- `PORT` (default `8000`)
- `LOG_LEVEL` (default `INFO`)
- **Database**:
- `DATABASE_URL` (e.g., `postgresql+psycopg://user:pass@host:5432/dbname`)
- `DB_POOL_SIZE` (optional)
- `DB_MAX_OVERFLOW` (optional)
- `DB_POOL_TIMEOUT` (optional)
- **Integrations placeholders** (declared now, implemented later):
- `ODOO_BASE_URL`
- `ODOO_DB`
- `ODOO_USERNAME`
- `ODOO_PASSWORD` (or `ODOO_API_KEY`, depending on final auth method in Module 2)
- `VAPI_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `WEBHOOK_BASE_URL`

In `.env.example`, list the same keys with empty values. Example format:

```text
ENVIRONMENT=
PORT=
DATABASE_URL=
ODOO_BASE_URL=
...
```



#### 4) Logging & error envelope (exact behavior)

Implement:

- **Request ID middleware**: assigns `X-Request-Id` (generate if missing), include in logs and responses.
- **Structured logging**: log a single line per request (method, path, status, duration_ms, request_id).
- **Error envelope**: all errors return JSON:
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Human readable message",
    "request_id": "..."
  }
}
```


In Module 1 we only need:

- `APIError` base exception (custom)
- global exception handler for `APIError`
- fallback handler for `Exception`

#### 5) Database layer & migrations (exact schema)

Use Alembic migrations. Create **exact tables**:

1. `idempotency_keys`

- `id` (PK, UUID or integer)
- `scope` (text) — e.g. `vapi_call`, `chat_message`, etc.
- `key` (text, unique within scope)
- `status` (text) — `in_progress|completed|failed`
- `response_hash` (text, nullable)
- `response_json` (jsonb, nullable)
- `created_at` (timestamp)
- `expires_at` (timestamp, nullable)

2. `audit_log`

- `id` (PK)
- `created_at`
- `request_id`
- `channel` (text) — `voice|chat|system`
- `actor` (text, nullable) — caller/visitor identifier if available
- `intent` (text, nullable) — filled starting Module 3
- `brain` (text, nullable) — filled starting Module 3
- `command_json` (jsonb, nullable)
- `odoo_result_json` (jsonb, nullable) — filled starting Module 2/3
- `status` (text) — `received|processed|error`
- `error_message` (text, nullable)

3. `jobs`

- `id` (PK)
- `created_at`
- `run_at`
- `type` (text)
- `payload_json` (jsonb)
- `status` (text) — `queued|running|succeeded|failed`
- `attempts` (int)
- `last_error` (text, nullable)

Indexes:

- unique index on (`scope`,`key`) for `idempotency_keys`
- index on `audit_log.created_at`
- index on `jobs.status` and `jobs.run_at`

#### 6) FastAPI app wiring (exact routers, no business logic)

In `src/main.py`:

- create `app = FastAPI(title=..., version=...)`
- include `monitoring.router` at `/monitoring`
- implement `GET /` and `GET /health`
- add middleware: request-id + logging
- `GET /health` checks:
- app is up
- DB connectivity (simple `SELECT 1`)

In `src/monitoring/router.py`:

- `GET /monitoring/metrics` returns minimal counters:
- uptime_seconds
- requests_total (in-memory counter is fine for Module 1)

#### 7) Verification scripts and tests (exact commands + expected outcome)

Add `scripts/verify_db.py` to:

- connect using `DATABASE_URL`
- run `SELECT 1`
- insert a row into `audit_log` and read it back

Add `scripts/verify_http.py` to:

- call `GET /` and `GET /health` against a provided base URL
- assert HTTP 200 responses
- print a short PASS/FAIL summary to stdout

Add `tests/test_health.py`:

- uses FastAPI test client
- asserts:
- `GET /` returns JSON with `service` + `version`
- `GET /health` returns `{"status":"ok"}` (and includes db status field)

Add `tests/test_db_smoke.py`:

- skips if `DATABASE_URL` is not set
- otherwise asserts DB connectivity and that required tables exist (`idempotency_keys`, `audit_log`, `jobs`)

#### 8) Local run instructions (exact)

In `README.md`, include:

- `uv sync`
- set env vars (point to Postgres)
- run server via:
- `uv run python main.py`
- or `uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
- run tests:
- `uv run pytest`

#### 9) Docker baseline (exact)

Create `Dockerfile` that:

- installs dependencies (uv or pip, choose one and document)
- sets `PORT=8000`
- runs `uvicorn src.main:app --host 0.0.0.0 --port ${PORT}`

### Acceptance criteria (Module 1 is “done” when)

- Repo tree exactly matches the structure listed above.
- `uv sync` completes successfully.
- With a working `DATABASE_URL`, these checks pass:
- `GET /health` returns HTTP 200 and indicates DB ok
- `scripts/verify_db.py` can insert+read from `audit_log`
- `scripts/verify_http.py --base-url http://localhost:8000` prints PASS
- `pytest` passes:
    - `tests/test_health.py`
    - `tests/test_db_smoke.py` (when DB is configured)
- No secrets are committed:
- `.env` is gitignored
- `.env.example` exists with blank values only

### “Module done” validation checklist (copy/paste runnable)

When Module 1 implementation is complete, validate it with these steps:1) Install dependencies

- `uv sync`

2) Run migrations (the chosen migration command must be documented in README)

- Expected: migrations apply cleanly (no errors)

3) Run the server

- `uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`

4) Validate HTTP endpoints

- `uv run python scripts/verify_http.py --base-url http://localhost:8000`
- Expected: PASS (root + health)

5) Validate DB read/write + required tables

- `uv run python scripts/verify_db.py`
- Expected: PASS (SELECT 1 + audit_log insert/read)

6) Run test suite

- `uv run pytest`
- Expected: all tests green

7) Update project context

- Update `.cursor/context.json` to reflect:
- Module 1 status = done
- final repo tree decisions
- final DB schema (tables + columns)
- final endpoints
- any open questions discovered
- Expected: file contains **no secrets** and matches the codebase.

### Outputs (what will exist after Module 1)

- A bootable HAES FastAPI service skeleton following the Sally Love repo pattern.
- Postgres schema and migrations for idempotency/audit/jobs.
- Minimal health/monitoring endpoints and smoke tests.

---

## Module outlines (we execute these one-by-one after Module 1)

## Module 2: Odoo Integration (OdooClient + mappings)

### Module objective

Implement a **single, well-tested Odoo integration layer** that the rest of the system will use. This module must establish a repeatable way to:

- authenticate to Odoo
- call Odoo RPC methods reliably
- convert Odoo errors into consistent Python exceptions
- discover (not assume) which Odoo models/fields we can use later

### Non-goals (explicit)

- No HAEL routing (Module 3)
- No brain business logic (Modules 4–7)
- No Vapi/Twilio integration (Module 8)
- No KPI calculations (Module 9)

### Inputs (from RDD)

- Odoo is **Odoo 18 Enterprise**.
- Client provided an Odoo base URL and user credentials in the RDD.

Security reminder:

- Even if credentials are written in the RDD, **we do not read credentials from the RDD** and **we do not commit secrets** anywhere in the repo.
- The service reads credentials only from environment variables.

### Odoo API approach (exact)

We will use **Odoo JSON-RPC over HTTPS** using `httpx`, via these endpoints:

- `POST /web/session/authenticate`
- `POST /web/dataset/call_kw`

We will not guess model names/fields. We will discover availability via `ir.model` and `fields_get`.

### Required environment variables (Module 2)

Module 2 requires these env var names to be set (values not committed):

- `ODOO_BASE_URL` (example: `https://hvacrfinest.odoo.odoo.com`)
- `ODOO_DB` (database name; must be provided explicitly)
- `ODOO_USERNAME` (login/email)
- `ODOO_PASSWORD` (or API key used as password; see below)
- `ODOO_TIMEOUT_SECONDS` (default `30`)

Optional env vars:

- `ODOO_AUTH_MODE` = `password` | `api_key` (default: `api_key`)
- `ODOO_VERIFY_SSL` = `true|false` (default: `true`)

Notes:

- In Odoo, an API key is typically used as the “password” value for authentication; our client treats it the same way and does not log it.

### Deliverables (exact files to create/update)

- `src/integrations/odoo.py` (new): `OdooClient` implementation (async).
- `src/integrations/__init__.py` (update): export `OdooClient`.
- `src/utils/errors.py` (update): add Odoo-specific exception classes.
- `scripts/verify_odoo_connection.py` (new): real connectivity verification.
- `scripts/discover_odoo_capabilities.py` (new): model/field discovery report.
- `tests/test_odoo_client_unit.py` (new): unit tests with mocked HTTP.
- `tests/test_odoo_integration_smoke.py` (new): optional real Odoo smoke test (skipped by default).
- `.cursor/context.json` (update at module completion): mark module2 status and record discovered capabilities (no secrets).

### OdooClient contract (exact methods)

Implement `class OdooClient` with these methods (names and behavior are part of Module 2 acceptance):1) `__init__(base_url, db, username, password, timeout_seconds, verify_ssl)`

- stores config
- creates an `httpx.AsyncClient`
- does not perform network calls

2) `async authenticate() -> int`

- calls `/web/session/authenticate`
- returns `uid` as int on success
- stores session cookies inside the `httpx` client for subsequent calls
- raises:
- `OdooAuthError` (bad db/user/password/api_key)
- `OdooTransportError` (DNS/TLS/timeout)

3) `async call_kw(model: str, method: str, args: list, kwargs: dict) -> Any`

- calls `/web/dataset/call_kw`
- raises `OdooRPCError` on any JSON-RPC error, preserving:
- odoo error name/code/message
- model/method
- request_id (if available)

4) Convenience wrappers (implemented in terms of `call_kw`):

- `search(model, domain, offset=0, limit=0, order=None) -> list[int]`
- `read(model, ids, fields=None) -> list[dict]`
- `search_read(model, domain, fields=None, offset=0, limit=0, order=None) -> list[dict]`
- `create(model, values: dict) -> int`
- `write(model, ids, values: dict) -> bool`
- `unlink(model, ids) -> bool`
- `fields_get(model, attributes=None) -> dict`

5) `async close()`

- closes the `httpx.AsyncClient`

### Redaction/logging rules (Module 2)

- Never log `ODOO_PASSWORD` / API key.
- Never log cookies/session ids.
- When logging request payloads, redact keys: `password`, `api_key`, `token`, `Authorization`.
- Odoo request/response metadata can be logged:
- endpoint, model, method, duration_ms, status

### Discovery scripts (exact behavior)

#### `scripts/verify_odoo_connection.py`

This script must:

- load env vars
- create `OdooClient`
- call `authenticate()` and print:
- `odoo_base_url`, `db`, `uid` (no password)
- run one safe read to prove permissions, e.g.:
- `res.users` read of current uid (fields: `name`, `login`)
- exit code:
- `0` on success
- non-zero on failure with a clear error message

#### `scripts/discover_odoo_capabilities.py`

This script must:

- authenticate
- determine whether each “candidate model” is accessible by attempting a minimal `fields_get`:
- `res.partner` (contacts)
- `crm.lead` (leads/opportunities)
- `project.task` (field service tasks if used)
- `sale.order` (quotes/orders)
- `account.move` (invoices)
- `purchase.order` (POs)
- `product.product` / `product.template` (products)
- `stock.quant` (inventory)
- `hr.employee` (employees)
- `hr.payslip` (payroll, if installed)

Output requirements:

- print a table-like summary to stdout:
- model name → accessible yes/no → key fields present (if accessible)
- write a JSON report to `.cursor/odoo_discovery.json` (no secrets) containing:
- timestamp
- Odoo base URL (ok), db name (ok), uid (ok)
- per-model: accessible bool, selected fields list

### Tests (exact)

#### Unit tests: `tests/test_odoo_client_unit.py`

Must test with mocked HTTP responses:

- authenticate success returns uid
- authenticate failure raises `OdooAuthError`
- call_kw error raises `OdooRPCError` and includes model/method
- redaction logic does not emit password in logs (basic check)

#### Integration smoke test: `tests/test_odoo_integration_smoke.py`

- skipped unless `RUN_ODOO_INTEGRATION_TESTS=1` is set
- requires env vars for Odoo
- runs:
- authenticate
- `res.users` read on current uid
- asserts non-empty response

### Acceptance criteria (Module 2 is “done” when)

- `scripts/verify_odoo_connection.py` succeeds against the client Odoo instance.
- `scripts/discover_odoo_capabilities.py` produces:
- stdout summary
- `.cursor/odoo_discovery.json` report
- Unit tests pass: `uv run pytest -k odoo`
- No secrets are committed:
- `.cursor/odoo_discovery.json` contains no passwords/tokens
- `.cursor/context.json` contains only env var names (not values)

### “Module done” validation checklist (copy/paste runnable)

1) Set env vars (do not commit them)

- `export ODOO_BASE_URL=...`
- `export ODOO_DB=...`
- `export ODOO_USERNAME=...`
- `export ODOO_PASSWORD=...`

2) Verify connectivity

- `uv run python scripts/verify_odoo_connection.py`
- Expected: PASS summary with uid and user login (no secrets printed)

3) Discover capabilities

- `uv run python scripts/discover_odoo_capabilities.py`
- Expected:
- prints accessible models
- writes `.cursor/odoo_discovery.json`

4) Run unit tests

- `uv run pytest -k odoo`
- Expected: all green

5) Update project context

- Update `.cursor/context.json`:
- mark Module 2 status = done
- record discovered model availability (from `.cursor/odoo_discovery.json`)
- record which auth mode we used (`api_key` vs `password`)
- keep only env var names, never values

## Module 3: HAEL Command Engine (schemas + router)

### Module objective

Implement the **Command Engine (HAEL)** described in [`Requirements.md`](/Users/mac/Developer/HAES%20HVAC/requirements.md) and RDD **Section 9** as a deterministic, testable pipeline that:

- converts inbound voice/chat “raw input” into a **validated command object**
- routes that command to exactly one brain (**CORE/OPS/REVENUE/PEOPLE**)
- fails closed (requires human) when uncertain or missing required data

### Non-goals (explicit)

- No Odoo writes for business workflows (Brains start in Modules 4–7)
- No Vapi/Twilio wiring (Module 8)
- No KPI computation (Module 9)

### Inputs we are allowed to use (source of truth)

- `Requirements.md`: “Command Engine (HAEL) converts conversations into structured business commands.”
- RDD Section 9:
- **9.2 Command Routing Rules** (intent → brain)
- **9.3 Data Extraction Requirements** (required fields per request type)
- Output of Module 2 discovery:
- `.cursor/odoo_discovery.json` (what models/fields are actually available)

### HAEL design principle (to prevent hallucination)

HAEL must produce a command that is:

- **schema-valid** (Pydantic)
- **deterministic** for the same input (no random behavior)
- **audited** (write an `audit_log` record)
- **idempotent** (derive and store an idempotency key for repeated inbound messages)

### Deliverables (exact files to create/update)

- `src/hael/` (new/filled):
- `src/hael/schema.py` (new): Pydantic models for the HAEL command envelope + intents/entities.
- `src/hael/extractors/` (new):
    - `src/hael/extractors/base.py` (new): extractor interface
    - `src/hael/extractors/rule_based.py` (new): deterministic extractor (Module 3 default)
- `src/hael/router.py` (new): deterministic intent→brain router and “requires human” logic
- `src/hael/__init__.py` (update): exports
- `src/models/` (update): re-export HAEL models if we want them shared across modules
- `src/utils/errors.py` (update): `HaelExtractionError`, `HaelValidationError`
- `src/db/models.py` (update if needed): ensure `audit_log` supports `intent`, `brain`, `command_json`, `status`
- `scripts/verify_hael_samples.py` (new): run HAEL on fixtures and print PASS/FAIL
- `tests/fixtures/hael_samples.json` (new): deterministic sample inputs/expected outputs
- `tests/test_hael_router.py` (new): unit tests for routing decisions
- `tests/test_hael_extractor_rule_based.py` (new): unit tests for extractor behavior
- `.cursor/context.json` (update at module completion): record HAEL contract (intents/actions/required fields), no secrets

### HAEL command schema (exact)

In `src/hael/schema.py`, define:1) `Channel` enum:

- `voice`
- `chat`
- `system`

2) `Brain` enum:

- `core`
- `ops`
- `revenue`
- `people`
- `unknown`

3) `Intent` enum (initial set; can expand later, but must be stable for tests):

- `service_request`
- `schedule_appointment`
- `reschedule_appointment`
- `cancel_appointment`
- `status_update_request`
- `quote_request`
- `billing_inquiry`
- `payment_terms_inquiry`
- `invoice_request`
- `inventory_inquiry`
- `purchase_request`
- `hiring_inquiry`
- `onboarding_inquiry`
- `payroll_inquiry`
- `unknown`

4) `Entity` model (normalized extracted data; all fields optional, validated):

- `full_name`
- `phone`
- `email`
- `address`
- `zip_code`
- `problem_description`
- `system_type`
- `urgency_level` (enum: `emergency|high|medium|low|unknown`)
- `preferred_time_windows` (array of strings)
- `property_type`
- `square_footage`
- `system_age_years`
- `budget_range`
- `timeline`

5) `HaelCommand` model:

- `request_id` (string; required)
- `channel` (Channel; required)
- `raw_text` (string; required)
- `intent` (Intent; required)
- `brain` (Brain; required)
- `entities` (Entity; required but can be empty)
- `confidence` (float 0–1; required)
- `requires_human` (bool; required)
- `missing_fields` (array of strings; required; empty if none)
- `idempotency_key` (string; required)
- `created_at` (datetime; required)

### Deterministic routing rules (exact mapping)

In `src/hael/router.py`, define the initial mapping:

- **OPS-BRAIN**
- `service_request`
- `schedule_appointment`
- `reschedule_appointment`
- `cancel_appointment`
- `status_update_request`
- **REVENUE-BRAIN**
- `quote_request`
- **CORE-BRAIN**
- `billing_inquiry`
- `payment_terms_inquiry`
- `invoice_request`
- `inventory_inquiry`
- `purchase_request`
- **PEOPLE-BRAIN**
- `hiring_inquiry`
- `onboarding_inquiry`
- `payroll_inquiry`
- **UNKNOWN**
- `unknown`

Fallback rule:

- If intent is `unknown`, set `brain=unknown`, `requires_human=true`.

### Required-field rules (from RDD 9.3; enforced)

Encode the required fields list so HAEL can decide `requires_human` deterministically:

- For `service_request` / scheduling intents, required:
- `full_name` OR `phone` (at least one identity anchor)
- `address` OR `zip_code`
- `problem_description`
- `urgency_level`
- For `quote_request`, required:
- `full_name` OR `phone`
- `property_type`
- `square_footage` (if available; otherwise mark missing)
- `timeline`

Rule:

- If required fields are missing, set `requires_human=true` and populate `missing_fields`.

### Extraction pipeline (Module 3 default = rule-based)

In `src/hael/extractors/rule_based.py`, implement deterministic extraction:

- intent detection via keyword rules (documented in code comments)
- phone/email extraction via regex
- urgency inference via keywords + RDD emergency thresholds (e.g., “no heat”, “gas leak”, “no ac”) → `urgency_level`
- everything else left as missing unless explicitly present in text

Important:

- If extractor cannot confidently decide, set `intent=unknown`, `confidence<=0.4`, `requires_human=true`.

### Audit + idempotency integration (uses Module 1 DB)

When HAEL processes an input:1) write `audit_log` row with status `received`, store `raw_text`, `channel`, `request_id`2) derive `idempotency_key` deterministically:

- `sha256(channel + normalized_phone/email + intent + canonical_entities_subset + date_bucket)`

3) upsert into `idempotency_keys` with status `in_progress`/`completed` later4) update `audit_log` with `intent`, `brain`, `command_json`, `status=processed` OR `status=error`

### Tests and fixtures (exact)

`tests/fixtures/hael_samples.json` must contain at least these scenarios:

- A service request with phone + address + problem text → OPS + requires_human=false
- A quote request missing square footage → REVENUE + requires_human=true + missing_fields includes `square_footage`
- A billing question (“When is my payment due?”) → CORE + requires_human=false
- A payroll question → PEOPLE + requires_human=true (until Module 7 adds data)
- An unknown/unrelated message → intent unknown + requires_human=true

`scripts/verify_hael_samples.py` must:

- load fixtures
- run rule-based extractor + router
- compare outputs to expected intent/brain/requires_human/missing_fields
- print PASS/FAIL and exit non-zero on failure

### Acceptance criteria (Module 3 is “done” when)

- `uv run python scripts/verify_hael_samples.py` prints PASS and exits 0.
- `uv run pytest -k hael` passes.
- HAEL output is deterministic for the same input (fixtures).
- `.cursor/context.json` updated with:
- supported `Intent` list
- intent→brain mapping
- required-field rules
- module3 status = done

## Module 4: OPS-BRAIN (dispatch + scheduling)

### Module objective

Implement **OPS-BRAIN** as the system’s operational execution layer for:

- dispatch intake
- scheduling / rescheduling / cancellation
- “what’s my status” requests

OPS-BRAIN consumes the **HAEL command output** from Module 3 and performs **Odoo mutations** using the **actual available Odoo models** confirmed in Module 2 (`.cursor/odoo_discovery.json`). It must apply the scheduling and emergency rules captured in the RDD deterministically (no guessing).

### Non-goals (explicit)

- No pricing, invoicing, approvals (CORE-BRAIN, Module 5)
- No lead pipeline/marketing (REVENUE-BRAIN, Module 6)
- No hiring/payroll (PEOPLE-BRAIN, Module 7)
- No voice/chat transport endpoints (Module 8)

### Inputs (source of truth)

- `Requirements.md`: OPS-BRAIN covers dispatch, scheduling, fleet routing, inventory.
- RDD Section 4:
- **Service types + durations**
- **Emergency definitions** (explicit thresholds)
- **Technician roster & scheduling rules**
- **Minimum time between appointments = 30 minutes**
- **Travel time calculation: live GPS + 15% buffer** (we implement buffer logic; GPS integration is not in scope unless provided)
- **Dispatch priority logic**
- **Fleet and routing priorities** (captured as rules; no GPS vendor integration in Module 4)
- Module 3 outputs: `HaelCommand` with `intent`, `entities`, `requires_human`, `missing_fields`
- Module 2 outputs: `.cursor/odoo_discovery.json` (which Odoo models/fields are available)

### OPS-BRAIN “fail closed” rule (to prevent hallucination)

OPS-BRAIN must not schedule or create work orders if:

- HAEL says `requires_human=true`, OR
- required scheduling inputs are missing (defined below), OR
- the Odoo target model(s) for scheduling are not confirmed available by discovery

In those cases, OPS-BRAIN returns a structured response with:

- `status = needs_human`
- `missing_fields` and/or `missing_capabilities`

### Odoo model strategy (must be discovery-driven)

Module 4 will not hardcode a single scheduling model until we confirm availability:Candidate Odoo models (checked via Module 2 discovery scripts):

- **Field Service**: `project.task` (common), possibly `fsm.order` depending on module
- **Calendar events**: `calendar.event`
- **CRM linkage**: `res.partner` for customer/contact

Module 4 must implement an internal mapping file:

- `src/brains/ops/odoo_models.py` that reads `.cursor/odoo_discovery.json` results (or a config derived from it) and chooses:
- `WORK_ORDER_MODEL`
- `SCHEDULE_MODEL`
- `CUSTOMER_MODEL` (expected `res.partner`)

If none of the candidate models are available, Module 4 cannot “complete” and must block with a clear error.

### Deliverables (exact files to create/update)

Create/Update the following:

- `src/brains/ops/` (new/filled):
- `src/brains/ops/schema.py` (new): OPS request/response models (Pydantic)
- `src/brains/ops/service_catalog.py` (new): service types + typical durations + priorities (from RDD)
- `src/brains/ops/emergency_rules.py` (new): emergency qualification rules (from RDD thresholds)
- `src/brains/ops/tech_roster.py` (new): technician roster + service areas + schedules (from RDD; as static config for now)
- `src/brains/ops/scheduling_rules.py` (new): 30-min buffer, slot sizing, dispatch priority ordering
- `src/brains/ops/odoo_models.py` (new): discovery-driven model selection + field mapping helpers
- `src/brains/ops/handlers.py` (new): entrypoint `handle_ops_command(command: HaelCommand) -> OpsResult`
- `src/brains/ops/odoo_actions.py` (new): create/update/cancel/reschedule operations in Odoo via `OdooClient`
- `src/brains/ops/__init__.py` (update): exports
- `src/utils/errors.py` (update): `OpsBrainError`, `OpsBrainNeedsHuman`
- `scripts/verify_ops_flow.py` (new): deterministic validation harness for OPS flows (no Vapi)
- `tests/fixtures/ops_samples.json` (new): sample commands + expected outcomes
- `tests/test_ops_rules.py` (new): unit tests for emergency/scheduling rules
- `tests/test_ops_odoo_mocked.py` (new): unit tests with mocked `OdooClient` verifying correct model/method calls
- Optional: `tests/test_ops_odoo_smoke.py` (new): real Odoo smoke test, skipped unless enabled
- `.cursor/context.json` (update at module completion)

### OPS-BRAIN command interface (exact)

`handle_ops_command()` must accept a validated `HaelCommand` and support these intents:

- `service_request`
- `schedule_appointment`
- `reschedule_appointment`
- `cancel_appointment`
- `status_update_request`

If `intent` is anything else, OPS returns `status=unsupported_intent`.

### Scheduling inputs required (deterministic)

For OPS intents, required fields are derived from HAEL entities:

- For `service_request` and `schedule_appointment`:
- identity anchor: `phone` OR `email` OR `full_name` (at least one)
- location anchor: `address` OR `zip_code` (at least one)
- `problem_description`
- `urgency_level`
- For `reschedule_appointment` / `cancel_appointment` / `status_update_request`:
- identity anchor: `phone` OR `email`
- plus at least one of:
    - a known appointment identifier (not available until we create it; so we’ll use best-effort lookup by contact + recent open jobs)
    - address/zip + recency window (e.g., last 14 days) — implemented as deterministic lookup rules

If required inputs are missing, return `needs_human` with explicit `missing_fields`.

### Emergency qualification (exact rules from RDD)

In `emergency_rules.py`, implement these as deterministic checks:

- If caller indicates **no heat** and (outside temp below **55°F**) → emergency
- If caller indicates **no AC** and (outside temp above **85°F**) → emergency
- Always emergency:
- gas leak / carbon monoxide
- electrical burning smell / main breaker tripping
- refrigerant leak visible/audible
- flooding/water damage caused by HVAC
- medical/refrigeration/server room failures
- multi-unit outages

Important:

- External temperature source is not provided yet. Until we integrate a weather API, we implement:
- **temperature threshold checks only when the user explicitly states the temperature** or provides context like “it’s 90 degrees” (extractable by HAEL later)
- otherwise emergency is determined by the other “always emergency” rules + phrasing signals (“gas leak”, “CO”, “burning smell”, “water leaking”).

### Service types and durations (from RDD)

In `service_catalog.py`, encode the RDD table as a static dictionary:

- service_type → (duration_range_minutes, priority)

Used to:

- set default time window requirements
- choose “slot length” (from RDD skill-based blocks)

### Technician roster (from RDD)

In `tech_roster.py`, encode the provided roster:

- name, phone, email, skill level, certifications, service areas, schedule

For Module 4 we will **not** implement true geospatial routing. We only:

- pick tech by explicit routing rules (RDD lead routing is Revenue; Ops uses proximity/skill/workload—proximity not available yet)
- implement a deterministic fallback:
- if service area text matches a tech’s service area → choose that tech
- else choose the first available senior tech
- else `needs_human`

### Odoo operations (must be minimal + safe)

OPS-BRAIN must implement Odoo actions in `odoo_actions.py`:1) Ensure a customer/contact exists:

- search or create `res.partner` by phone/email

2) Create or update a “work order / job” record using the discovered work model:

- store problem description
- store urgency classification
- store address/zip (if model supports)

3) If a schedulable model exists (e.g., `calendar.event`), create an event or schedule fields on the work order.4) For reschedule/cancel:

- find the latest open job for the contact in a deterministic time window
- update status fields (or cancel event)

All writes must be audited in `audit_log` with:

- `intent`, `brain=ops`, `command_json`, `odoo_result_json` (redacted)

### Scripts (exact)

`scripts/verify_ops_flow.py` must:

- load fixtures from `tests/fixtures/ops_samples.json`
- for each fixture:
- feed a `HaelCommand` JSON into `handle_ops_command`
- validate:
    - returned `status`
    - `needs_human` behavior
    - missing fields list
- optionally (when `RUN_ODOO_INTEGRATION_TESTS=1`):
    - perform real Odoo writes into a test record namespace (must be documented)

### Tests (exact)

1) `tests/test_ops_rules.py`:

- emergency rules classification given explicit phrases
- scheduling buffer rule (minimum 30 minutes between)

2) `tests/test_ops_odoo_mocked.py`:

- uses a mocked `OdooClient`
- asserts that for a valid service request:
- we search/create `res.partner`
- we create a work order record in the selected model

3) `tests/test_ops_odoo_smoke.py` (optional, skipped by default):

- runs only when `RUN_ODOO_INTEGRATION_TESTS=1`
- requires Odoo env vars
- creates a minimal test work order and then cleans it up (if possible)

### Acceptance criteria (Module 4 is “done” when)

- `uv run python scripts/verify_ops_flow.py` prints PASS and exits 0 (mock mode).
- `uv run pytest -k ops` passes.
- For fixtures, OPS returns deterministic results with clear `needs_human` outcomes.
- Odoo model selection is discovery-driven (no hardcoded model assumptions that contradict `.cursor/odoo_discovery.json`).
- `.cursor/context.json` updated with:
- supported OPS intents
- ops rules summary (buffers/emergency thresholds)
- chosen Odoo models for work orders and scheduling (by name)
- module4 status = done

### “Module done” validation checklist (copy/paste runnable)

1) Run unit tests

- `uv run pytest -k ops`
- Expected: all green

2) Validate OPS fixtures

- `uv run python scripts/verify_ops_flow.py`
- Expected: PASS summary

3) (Optional) Run Odoo smoke test (only if enabled and safe)

- `export RUN_ODOO_INTEGRATION_TESTS=1`
- `uv run pytest -k ops_odoo_smoke`
- Expected: green (and no stray records left behind)

4) Update project context

- Update `.cursor/context.json` with Module 4 outputs (no secrets)

## Module 5: CORE-BRAIN (pricing + approvals + invoicing)

### Module objective

Implement **CORE-BRAIN** as the financial/compliance “source of truth” that:

- answers billing/payment-term questions deterministically
- makes deterministic **pricing decisions** based on the RDD pricing tables (no guessing)
- evaluates **approval requirements** for quotes/POs/refunds/discounts
- defines a deterministic **invoice policy** (when to generate/send, and what requires human approval)
- provides required **compliance snippets** (license/disclosures/warranty terms) as structured outputs

This module must be safe: when inputs are missing or policies are ambiguous, CORE-BRAIN must **fail closed** (`needs_human`) while still returning the best structured “what we need next” response.

### Non-goals (explicit)

- No dispatch/scheduling (OPS-BRAIN, Module 4)
- No lead generation or quote building UI (REVENUE-BRAIN, Module 6)
- No hiring/payroll (PEOPLE-BRAIN, Module 7)
- No voice/chat transport endpoints (Module 8)
- No KPI aggregation jobs (Module 9) — CORE-BRAIN only defines KPI/report config objects

### Inputs (source of truth)

- `Requirements.md`: CORE-BRAIN covers pricing/accounting/compliance/reporting.
- RDD Section 3 (CORE-BRAIN configuration):
- service call pricing tables (Default-PM, Retail, Com, Com-Lessen, Hotels/Multifamily)
- install pricing ranges (provided examples)
- maintenance plan pricing
- payment terms & late fee rule
- revenue recognition rule (upon payment)
- compliance disclosure (Texas TDLR) + license number + warranty terms
- approval thresholds (quotes/POs/refunds/discounts + write-offs)
- report definitions + recipients/delivery methods
- Module 2 discovery output: `.cursor/odoo_discovery.json` (confirm access to accounting models before relying on them)
- Module 3 output: `HaelCommand` schema + routing
- Module 1 DB: `audit_log`, `idempotency_keys`, `jobs`

### CORE-BRAIN “fail closed” rules (to prevent hallucination)

CORE-BRAIN must return `needs_human` (and not attempt an Odoo write) if:

- HAEL says `requires_human=true`, OR
- the requested action requires an identifier we don’t have (e.g., invoice id) and deterministic lookup fails, OR
- the necessary Odoo accounting model is not confirmed available by Module 2 discovery.

### Odoo model strategy (must be discovery-driven)

Candidate models CORE-BRAIN may use (only if discovery confirms):

- `account.move` (invoices)
- `account.payment.term` (payment terms)
- `account.tax` (tax config)
- `sale.order` (quotes/orders) — for approvals and invoice generation hooks
- `purchase.order` (POs) — for approval thresholds and PO creation hooks (actual PO creation may be Module 4/9 later)
- `res.partner` (customer classification for pricing tiers)

If discovery shows `account.move` is not accessible, CORE-BRAIN must:

- still answer pricing/approval/compliance questions
- but set `missing_capabilities=["account.move"]` for invoice-related intents

### Deliverables (exact files to create/update)

Create/Update the following:

- `src/brains/core/` (new/filled):
- `src/brains/core/schema.py` (new): Pydantic models for core requests/results/decisions
- `src/brains/core/pricing_catalog.py` (new): literal pricing tables from RDD (no calculations hidden)
- `src/brains/core/pricing_engine.py` (new): deterministic pricing decision functions
- `src/brains/core/payment_terms.py` (new): deterministic payment terms logic (segment-based) + late fee policy
- `src/brains/core/approval_rules.py` (new): deterministic approval thresholds from RDD
- `src/brains/core/compliance.py` (new): required disclosures + warranty snippet provider
- `src/brains/core/odoo_models.py` (new): discovery-driven model/field selection helpers for accounting objects
- `src/brains/core/odoo_actions.py` (new): safe Odoo reads/writes for invoices/terms/taxes (reads first; writes gated)
- `src/brains/core/handlers.py` (new): entrypoint `handle_core_command(command: HaelCommand) -> CoreResult`
- `src/brains/core/reporting_catalog.py` (new): report definitions (daily/weekly/monthly lists) + recipients config (no sending)
- `src/brains/core/__init__.py` (update): exports
- `src/utils/errors.py` (update): `CoreBrainError`, `CoreBrainNeedsHuman`, `CoreBrainCapabilityMissing`
- Scripts:
- `scripts/verify_core_pricing.py` (new): run pricing fixtures and print PASS/FAIL
- `scripts/verify_core_approvals.py` (new): run approval fixtures and print PASS/FAIL
- `scripts/verify_core_compliance.py` (new): print required disclosures/warranty snippets
- `scripts/discover_odoo_accounting.py` (new): confirms access to `account.move`, `account.payment.term`, `account.tax` and prints a capability summary (no secrets)
- Tests/fixtures:
- `tests/fixtures/core_samples.json` (new): deterministic sample commands/inputs and expected decisions
- `tests/test_core_pricing.py` (new)
- `tests/test_core_approvals.py` (new)
- `tests/test_core_payment_terms.py` (new)
- `tests/test_core_odoo_mocked.py` (new): mocked `OdooClient` call assertions
- Optional: `tests/test_core_odoo_smoke.py` (new): real Odoo reads only; skipped by default
- `.cursor/context.json` (update at module completion): record pricing tiers, approvals, invoice policy, compliance snippets (no secrets)

### CORE-BRAIN command interface (exact)

`handle_core_command()` accepts a validated `HaelCommand` and supports these intents (as defined in Module 3):

- `billing_inquiry`
- `payment_terms_inquiry`
- `invoice_request`
- `purchase_request`
- `inventory_inquiry`

If `intent` is anything else, CORE returns `status=unsupported_intent`.

### Pricing rules (explicit, no hidden math)

CORE-BRAIN pricing is based on RDD Section 3 **Service Call Pricing** tiers:

- `Default-PM` (Property Management / National Accounts / Portals)
- `Retail` (Residential homeowners)
- `Com` (Commercial)
- `Com-Lessen` (National Commercial / Warranty / Flat-Rate Portal Accounts)
- `Com-Hotels_Multifamily`

Each tier defines these literal fees:

- diagnostic fee
- trip charge
- emergency/after-hours premium
- weekend/holiday premium

Tier selection (deterministic):1) If the customer’s Odoo `res.partner` record has a tag/category mapping to a known tier → use that tier.2) Else if a calling context provides a tier hint (future HAEL field) → use it.3) Else return `needs_human=true` with `missing_fields=["pricing_tier"] `and include a suggested default of `Retail` (as a non-binding suggestion).Premium selection (deterministic):

- weekend/holiday premium applies if `created_at` falls on weekend OR on a configured holiday list (from RDD holidays).
- emergency premium applies only if:
- HAEL `urgency_level=emergency`, OR
- the OPS-BRAIN emergency classification says emergency (future integration), OR
- caller explicitly states a gas leak/CO/electrical hazard keywords (from OPS rules)

If the system cannot determine whether it’s after-hours (business hours are not fully specified), CORE-BRAIN must not apply “after-hours” premium automatically.

### Payment terms & late fee rules (deterministic)

From RDD Section 3:

- standard: “due on invoice”
- commercial: “15 days”
- property management: “30 days”
- late payment fee: “1 percent”

CORE-BRAIN must implement:

- `get_payment_terms(segment)` that returns:
- `due_days` (0/15/30)
- `late_fee_percent_per_period` (1.0)
- `accepted_payment_methods` (cash/card/zelle per RDD)

If the customer segment is unknown, return `needs_human` with `missing_fields=["customer_segment"]`.

### Approval workflows (deterministic thresholds)

Encode the RDD thresholds exactly:

- Quote approvals:
- under 20000 → auto
- 20000 to 1000000 → Linda
- over 1000000 → Junior
- PO approvals:
- under 99 → auto
- 101 to 500 → Linda
- over 501 → Junior
- capital equipment over 350 → Junior
- Refund/Credit approvals:
- under 0 → Technician/CSR
- 1 to 99 → Anna
- over 100 → Linda
- Discount approvals:
- up to 5% → auto
- 6% to 10% → Linda
- over 10.1% → Junior

CORE-BRAIN must output an `ApprovalDecision` object:

- `approval_required` (bool)
- `approver` (role/name as configured)
- `reason`
- `threshold_rule_id`

### Invoice policy (deterministic, policy-only)

From RDD Section 3:

- invoice trigger: “when tech is complete job and workorder is paided”
- revenue recognized upon payment

Module 5 will implement **policy and decisioning**:

- `should_generate_invoice(work_order_state, payment_state)` returns:
- `generate_now` bool
- `requires_human` bool (e.g., missing state fields or contradictory info)
- `reason`

Actual wiring from OPS work orders → invoice generation is done later (end-to-end flows), but Module 5 defines and tests the policy now.

### Compliance snippets (deterministic)

From RDD Section 3:

- warranty terms:
- 30-day labor on repairs (replaced)
- 1-year labor for equipment replacement
- Texas TDLR disclosure string + license number

CORE-BRAIN exposes `get_required_disclosures()` returning structured fields:

- `license_number`
- `regulatory_disclosure_text`
- `warranty_terms_text`

### Reporting config (definitions only)

CORE-BRAIN defines report templates (no sending in Module 5):

- daily metrics list (from RDD daily execution KPIs)
- weekly/monthly/quarterly/annual lists (as written in RDD)
- report recipients config (currently “Junior & Linda” per RDD; stored as names/roles)
- delivery methods: email, Odoo dashboard, SMS summary

This is consumed by Module 9 (KPI engine + delivery).

### Scripts (exact)

`scripts/verify_core_pricing.py` must:

- load `tests/fixtures/core_samples.json`
- evaluate pricing decisions for each fixture
- compare to expected tier/fees/premiums/needs_human
- print PASS/FAIL and exit non-zero on failure

`scripts/verify_core_approvals.py` must:

- run fixtures across quote/po/refund/discount thresholds
- print PASS/FAIL and exit non-zero on failure

`scripts/discover_odoo_accounting.py` must:

- authenticate via Module 2 Odoo env vars
- check read access to:
- `account.move` (search_read limit 1)
- `account.payment.term` (search_read limit 1)
- `account.tax` (search_read limit 1)
- print capability summary and exit non-zero if required models are inaccessible

### Tests (exact)

1) `tests/test_core_pricing.py`

- ensures literal pricing tables match RDD values
- ensures tier selection fails closed when unknown

2) `tests/test_core_approvals.py`

- asserts exact thresholds route to the correct approver

3) `tests/test_core_payment_terms.py`

- asserts segment-based due days + late fee percent

4) `tests/test_core_odoo_mocked.py`

- mocked Odoo calls for:
- reading payment terms/taxes (read-only)
- invoice lookup by partner (read-only)

5) `tests/test_core_odoo_smoke.py` (optional)

- skipped unless `RUN_ODOO_INTEGRATION_TESTS=1`
- runs read-only checks against `account.move` and `account.payment.term`

### Acceptance criteria (Module 5 is “done” when)

- `uv run python scripts/verify_core_pricing.py` prints PASS and exits 0.
- `uv run python scripts/verify_core_approvals.py` prints PASS and exits 0.
- `uv run python scripts/verify_core_compliance.py` prints expected disclosure fields.
- `uv run pytest -k core` passes.
- If `RUN_ODOO_INTEGRATION_TESTS=1`, `scripts/discover_odoo_accounting.py` passes (read-only).
- `.cursor/context.json` updated with:
- pricing tiers + fee values
- approvals thresholds
- invoice policy summary
- compliance disclosure fields
- module5 status = done

### “Module done” validation checklist (copy/paste runnable)

1) Run unit tests

- `uv run pytest -k core`
- Expected: all green

2) Validate pricing decisions

- `uv run python scripts/verify_core_pricing.py`
- Expected: PASS

3) Validate approvals

- `uv run python scripts/verify_core_approvals.py`
- Expected: PASS

4) Validate compliance output

- `uv run python scripts/verify_core_compliance.py`
- Expected: prints license/disclosure/warranty (no secrets)

5) (Optional) Validate Odoo accounting access (read-only)

- `export RUN_ODOO_INTEGRATION_TESTS=1`
- `uv run python scripts/discover_odoo_accounting.py`
- Expected: PASS capability summary

6) Update project context

- Update `.cursor/context.json` (no secrets)

## Module 6: REVENUE-BRAIN (leads + pipeline + follow-ups)

### Module objective

Implement **REVENUE-BRAIN** as the sales/marketing execution layer that:

- captures quote/leads from inbound conversations deterministically
- assigns a deterministic **qualification level** (hot/warm/cold) using RDD definitions
- applies deterministic **lead routing rules** (who it is assigned to)
- writes/updates the appropriate Odoo CRM/Sales records using Module 2’s discovery results
- creates deterministic follow-up “next actions” (tasks/activities) based on the RDD follow-up sequences

REVENUE-BRAIN must be safe: it must **fail closed** (`needs_human`) when required fields are missing or when Odoo capabilities are not available.

### Non-goals (explicit)

- No dispatch/scheduling/work order creation (OPS-BRAIN, Module 4)
- No pricing/approvals/invoice policy (CORE-BRAIN, Module 5)
- No hiring/payroll (PEOPLE-BRAIN, Module 7)
- No Vapi/Twilio transport wiring (Module 8)
- No KPI aggregation/report delivery (Module 9)

### Inputs (source of truth)

- `Requirements.md`: REVENUE-BRAIN covers marketing/leads/quoting/sales closing.
- RDD Section 5:
- lead sources and tracking preferences
- hot/warm/cold definitions
- lead routing rules (residential/commercial/high-value)
- response-time goals
- quoting/proposal notes (templates currently missing)
- pipeline stages list (used as canonical stage taxonomy)
- follow-up sequences (2-day reminder, 7-day nurture, 90-day reactivation)
- conversion trigger: “work order created”
- Module 3: `HaelCommand` with `intent=quote_request` and extracted entities (property details etc.)
- Module 2: `.cursor/odoo_discovery.json` (confirm `crm.lead`, `sale.order`, `mail.activity`, etc. are available before relying on them)
- Module 1 DB: `audit_log`, `idempotency_keys`, `jobs`

### REVENUE-BRAIN “fail closed” rules (to prevent hallucination)

Return `needs_human` and do **not** perform Odoo writes if:

- HAEL says `requires_human=true`, OR
- required quote fields are missing (defined below), OR
- required Odoo models are unavailable per `.cursor/odoo_discovery.json`.

### Odoo model strategy (must be discovery-driven)

Candidate models (use only if discovery confirms accessibility):

- `crm.lead` (lead/opportunity)
- `res.partner` (contact)
- `sale.order` (quotes/proposals, if used)
- `mail.activity` (follow-up tasks/activities)
- `utm.*` models for lead source attribution (optional; only if present)

If `crm.lead` is not accessible, Module 6 cannot proceed with Odoo lead creation and must block with:

- `missing_capabilities=["crm.lead"]`

### Deliverables (exact files to create/update)

Create/Update:

- `src/brains/revenue/` (new/filled):
- `src/brains/revenue/schema.py` (new): Pydantic models for revenue decisions/results
- `src/brains/revenue/qualification.py` (new): deterministic hot/warm/cold classifier from RDD
- `src/brains/revenue/routing.py` (new): deterministic assignment rules (residential/commercial/high-value)
- `src/brains/revenue/pipeline.py` (new): canonical pipeline stage names + transition helpers
- `src/brains/revenue/followups.py` (new): deterministic follow-up plan generator (2-day/7-day/90-day)
- `src/brains/revenue/lead_sources.py` (new): lead source normalization (website organic now; others later)
- `src/brains/revenue/odoo_models.py` (new): discovery-driven model/field mapping for CRM/Sales/Activities
- `src/brains/revenue/odoo_actions.py` (new): Odoo reads/writes for leads, contacts, activities (writes gated)
- `src/brains/revenue/handlers.py` (new): entrypoint `handle_revenue_command(command: HaelCommand) -> RevenueResult`
- `src/brains/revenue/__init__.py` (update): exports
- `src/utils/errors.py` (update): `RevenueBrainError`, `RevenueBrainNeedsHuman`, `RevenueBrainCapabilityMissing`
- Scripts:
- `scripts/discover_odoo_crm_sales.py` (new): confirms access to `crm.lead`, `sale.order`, `mail.activity`; prints capability summary
- `scripts/verify_revenue_qualification.py` (new): validates hot/warm/cold classification with fixtures
- `scripts/verify_revenue_routing.py` (new): validates assignment rules with fixtures
- `scripts/verify_revenue_pipeline.py` (new): validates stage taxonomy + transition outputs
- Tests/fixtures:
- `tests/fixtures/revenue_samples.json` (new): sample `HaelCommand` inputs and expected outputs
- `tests/test_revenue_qualification.py` (new)
- `tests/test_revenue_routing.py` (new)
- `tests/test_revenue_followups.py` (new)
- `tests/test_revenue_odoo_mocked.py` (new): mocked `OdooClient` call assertions
- Optional: `tests/test_revenue_odoo_smoke.py` (new): real Odoo writes in a test-safe way; skipped by default
- `.cursor/context.json` (update at module completion): record revenue brain contract + rules (no secrets)

### REVENUE-BRAIN command interface (exact)

`handle_revenue_command()` accepts a validated `HaelCommand` and supports:

- `quote_request`

If intent is anything else, return `status=unsupported_intent`.

### Required-field rules (based on RDD 9.3 “For Quote Requests”)

For a `quote_request`, REVENUE-BRAIN requires:

- identity anchor: `phone` OR `email` OR `full_name`
- `property_type`
- `timeline`

Strongly recommended (but can be missing → then `needs_human=true`):

- `square_footage`
- `system_age_years`
- `budget_range`

If required fields are missing, return:

- `needs_human=true`
- `missing_fields=[...]`

### Lead qualification (hot/warm/cold) — deterministic rules from RDD

Implement in `qualification.py`:

- **Hot** if any of the following:
- emergency-qualified language (no heat/no cooling/emergency)
- “ready to schedule today”
- install/repair within 72 hours
- decision maker + budget approved (if explicitly stated)
- **Warm** if:
- discomfort but system working
- scheduling within 3–14 days
- **Cold** if:
- price shopping only
- no urgency
- 15+ days out

If text does not match deterministically, default to:

- `warm` with `confidence<=0.6` and `needs_human=true`

### Routing rules — deterministic from RDD

In `routing.py` implement:

- Residential leads → assign to **Bounthon** and **Aubry**
- Commercial leads → assign to **Junior** and **Bounthon**
- High-value leads (over $10k) → assign to **Junior**

Deterministic inference:

- If property_type explicitly indicates commercial → commercial route
- If budget_range indicates > 10k → high-value route
- Else residential route

If required inference fields are missing, return `needs_human=true` with `missing_fields`.

### Pipeline stages — canonical list (as written in RDD)

In `pipeline.py`, define the stage taxonomy exactly (strings):

- Pending Schedule
- Job Scheduled
- On The Way
- On-Site
- On Hold | Must Reschedule
- Paused | Return Same Day
- Pending Quote Approval
- Quote Approved | Waiting for Parts
- Quote Approved | Hold
- Completed
- Warranty | Review and Paid
- Invoices Not Paid
- Closed

Revenue module uses stages only to:

- set initial stage for a quote request → `Pending Quote Approval`
- update stage when quote is accepted (future integration) → `Quote Approved | Waiting for Parts`

### Follow-up sequences — deterministic plan objects (from RDD)

In `followups.py`, generate “next actions” objects (not SMS/email sending yet):

- For “quote sent”:
- immediate “thank you” task/activity
- reminder at +2 days if no response
- 7-day nurture sequence if “maybe”
- 90-day reactivation sequence if “lost”

Module 6 will implement these as:

- Odoo `mail.activity` creates (if available), OR
- DB `jobs` records queued for Module 9/8 to deliver later

### Odoo operations (minimal and safe)

In `odoo_actions.py` implement:1) Ensure contact exists (`res.partner`) by phone/email2) Create or update a CRM lead (`crm.lead`) with:

- contact linkage
- summary of quote request (problem/system/property info)
- qualification level (hot/warm/cold) stored in a deterministic field or tag (depending on discovery)
- initial pipeline stage name (as stored in CRM stage model; mapping must be discovery-driven)

3) Create follow-up activities (`mail.activity`) if availableAll Odoo writes must be audited in `audit_log` with:

- `intent=quote_request`, `brain=revenue`, `command_json`, `odoo_result_json` (redacted)

### Scripts (exact)

`scripts/verify_revenue_qualification.py`:

- loads `tests/fixtures/revenue_samples.json`
- computes qualification and compares to expected
- prints PASS/FAIL and exits non-zero on failure

`scripts/verify_revenue_routing.py`:

- validates deterministic assignment decisions from fixtures

`scripts/discover_odoo_crm_sales.py`:

- authenticates and checks read access to:
- `crm.lead`
- `sale.order` (optional)
- `mail.activity`
- prints capability summary; exits non-zero if `crm.lead` is missing

### Tests (exact)

1) `tests/test_revenue_qualification.py`

- validates hot/warm/cold rules with deterministic inputs

2) `tests/test_revenue_routing.py`

- validates residential/commercial/high-value routing

3) `tests/test_revenue_followups.py`

- validates follow-up plan generation (task counts and schedule offsets)

4) `tests/test_revenue_odoo_mocked.py`

- mocked `OdooClient` asserts:
- `res.partner` search/create
- `crm.lead` create/update
- `mail.activity` create (if enabled by discovery)

### Acceptance criteria (Module 6 is “done” when)

- `uv run python scripts/verify_revenue_qualification.py` prints PASS and exits 0.
- `uv run python scripts/verify_revenue_routing.py` prints PASS and exits 0.
- `uv run pytest -k revenue` passes.
- If `RUN_ODOO_INTEGRATION_TESTS=1`, `scripts/discover_odoo_crm_sales.py` passes (read-only capabilities check).
- `.cursor/context.json` updated with:
- supported intents (quote_request)
- qualification rules summary
- routing rules summary
- pipeline stage taxonomy
- follow-up schedule summary
- module6 status = done

### “Module done” validation checklist (copy/paste runnable)

1) Run unit tests

- `uv run pytest -k revenue`
- Expected: all green

2) Validate qualification/routing scripts

- `uv run python scripts/verify_revenue_qualification.py`
- `uv run python scripts/verify_revenue_routing.py`
- Expected: PASS

3) (Optional) Validate Odoo CRM/Sales capability

- `export RUN_ODOO_INTEGRATION_TESTS=1`
- `uv run python scripts/discover_odoo_crm_sales.py`
- Expected: PASS capability summary

4) Update project context

- Update `.cursor/context.json` (no secrets)

## Module 7: PEOPLE-BRAIN (HR + payroll scaffolding)

### Module objective

Implement **PEOPLE-BRAIN** as the HR/onboarding/training/payroll rules engine that:

- answers hiring/onboarding/payroll questions deterministically
- turns the RDD onboarding checklist into **trackable tasks** (without inventing steps)
- captures training program structure (14-day onboarding + 30/60/90 ramp) as trackable items
- encodes payroll/commission rules deterministically (calculations + approvals), without “running payroll” unless inputs and Odoo capabilities are confirmed

### Non-goals (explicit)

- No dispatch/scheduling/work orders (OPS-BRAIN, Module 4)
- No pricing/invoicing/financial approvals (CORE-BRAIN, Module 5)
- No lead pipeline/marketing (REVENUE-BRAIN, Module 6)
- No Vapi/Twilio transport wiring (Module 8)
- No KPI aggregation/report delivery (Module 9) — PEOPLE-BRAIN only defines KPI inputs for payroll/training if needed

### Inputs (source of truth)

- `Requirements.md`: PEOPLE-BRAIN covers hiring, onboarding, training, payroll, KPIs.
- RDD Section 6:
- recruitment pipeline stages + background checks
- required documents: I-9, background check, drug screening, MVR, license verification, EPA cert, TDLR
- hiring approvals: Junior + Linda + Bounthon (joint approval)
- onboarding checklist categories (HR/identity, agreements, payroll activation, system access)
- training program topics + 14-day onboarding + 30/60/90 ramp
- training tracked in Odoo = Yes; certification expiration alerts = Yes
- pay period: bi-weekly
- commission: 15% repairs, 5% installs; hybrid/day rates for bigger projects
- commission paid on: invoice and collection (both checked)
- time tracking integration: not specified (blank)
- Module 3: `HaelCommand` (intents: `hiring_inquiry`, `onboarding_inquiry`, `payroll_inquiry`)
- Module 2: `.cursor/odoo_discovery.json` (confirm which HR/Payroll/Project models exist and are accessible)
- Module 1 DB: audit/idempotency/jobs

### PEOPLE-BRAIN “fail closed” rules (to prevent hallucination)

PEOPLE-BRAIN returns `needs_human` and does not attempt Odoo writes if:

- HAEL says `requires_human=true`, OR
- required inputs are missing for the requested action (defined below), OR
- the target Odoo model for persistence is not confirmed accessible by Module 2 discovery.

### Odoo model strategy (must be discovery-driven)

Candidate models (use only if Module 2 discovery confirms):

- HR:
- `hr.employee` (employees)
- `hr.applicant` (recruitment applicants) if recruitment app is installed
- `hr.skill` / `hr.employee.skill` (skills/certs) if available
- `hr.resume.line` (certification/history) if available
- Payroll:
- `hr.payslip` and supporting payroll models (if payroll module is installed and accessible)
- Training/onboarding tracking (safe fallback if HR models are limited):
- `project.task` (Project module is installed per RDD) to represent checklist items

Discovery-driven selection rule:

- Prefer native HR models for employee/applicant records.
- Prefer `project.task` for onboarding/training checklists if HR “training tracking” models are unavailable or unclear.
- If neither HR models nor `project.task` are available, block with `missing_capabilities`.

### Deliverables (exact files to create/update)

Create/Update:

- `src/brains/people/` (new/filled):
- `src/brains/people/schema.py` (new): Pydantic models for people decisions/results
- `src/brains/people/onboarding_catalog.py` (new): literal onboarding checklist items from RDD
- `src/brains/people/training_catalog.py` (new): literal training topics + 14-day + 30/60/90 structure from RDD
- `src/brains/people/hiring_policy.py` (new): deterministic hiring approval policy (roles + required checks)
- `src/brains/people/payroll_rules.py` (new): deterministic pay period + commission rules engine (no time tracking assumptions)
- `src/brains/people/odoo_models.py` (new): discovery-driven model/field selection for HR/Payroll/Project
- `src/brains/people/odoo_actions.py` (new): safe Odoo read/write helpers (writes gated)
- `src/brains/people/handlers.py` (new): entrypoint `handle_people_command(command: HaelCommand) -> PeopleResult`
- `src/brains/people/__init__.py` (update): exports
- `src/utils/errors.py` (update): `PeopleBrainError`, `PeopleBrainNeedsHuman`, `PeopleBrainCapabilityMissing`
- Scripts:
- `scripts/discover_odoo_hr_payroll.py` (new): checks model access for `hr.employee`, `hr.applicant`, `hr.payslip`, and `project.task`; prints capability summary
- `scripts/verify_people_onboarding.py` (new): validates onboarding checklist mapping and expected task count
- `scripts/verify_people_training.py` (new): validates training program mapping (14-day + 30/60/90)
- `scripts/verify_people_payroll_rules.py` (new): validates commission calculations with fixtures
- Tests/fixtures:
- `tests/fixtures/people_samples.json` (new): sample HAEL commands + expected PeopleResult outputs
- `tests/test_people_onboarding_catalog.py` (new)
- `tests/test_people_training_catalog.py` (new)
- `tests/test_people_payroll_rules.py` (new)
- `tests/test_people_odoo_mocked.py` (new): mocked `OdooClient` call assertions
- Optional: `tests/test_people_odoo_smoke.py` (new): read-only smoke checks; skipped by default
- `.cursor/context.json` (update at module completion): record people brain contract + rules (no secrets)

### PEOPLE-BRAIN command interface (exact)

`handle_people_command()` accepts a validated `HaelCommand` and supports:

- `hiring_inquiry`
- `onboarding_inquiry`
- `payroll_inquiry`

If intent is anything else, return `status=unsupported_intent`.

### Hiring rules (deterministic outputs)

For `hiring_inquiry`, PEOPLE-BRAIN returns a structured response that includes:

- `required_documents` (exact list from RDD)
- `background_check_requirements` (exact list from RDD)
- `approval_required=true` and `approvers=[Junior, Linda, Bounthon]`
- `next_steps` (deterministic, based on RDD stages: phone screen → technical interview → ride-along → final leadership → checks)

No Odoo writes are required for this inquiry-only flow unless the caller provides applicant identity details; if identity is missing, return `needs_human=true`.

### Onboarding checklist tracking (deterministic)

Onboarding checklist items (must match RDD categories exactly):1) HR & Identity Verification2) Employment Agreements (Odoo Sign – must be signed)3) Payroll & Banking Activation4) Minimum System AccessPersistence strategy:

- If `project.task` is available, represent each checklist line item as a `project.task` assigned to the employee (or HR admin) under a dedicated “Onboarding” project.
- If HR-specific checklist models exist and are confirmed, use them (but only after discovery confirms).

On `onboarding_inquiry`, PEOPLE-BRAIN can:

- create a checklist (if employee identity is known and Odoo capability exists)
- or return `needs_human` with missing fields (employee identifier/email)

### Training program tracking (deterministic)

Training program from RDD must be represented as:

- a 14-day onboarding plan (tasks/items)
- a 30/60/90 ramp plan (milestones)
- recurring Friday training meeting reminder (as a planned job/task, not an SMS/email send)

Certification requirements must be tracked as data fields if possible (EPA 608, TDLR, OSHA 10 recommended).If “certification expiration alerts” models are not available, store alert intents as Postgres `jobs` records for Module 9 delivery.

### Payroll rule engine (deterministic, no time tracking assumptions)

Inputs PEOPLE-BRAIN can accept for payroll calculations (from command/entities or explicit payload):

- `employee_id` or employee identity anchor
- a list of completed repair invoices and install invoices (amounts + dates)
- optional “day rate” overrides for bigger projects (explicitly provided)

Rules from RDD:

- pay period: bi-weekly
- commission:
- repairs: 15% of sales
- installs: 5% of sales
- commission “paid on”: invoice and collection are both checked; interpretation must be deterministic:
- default behavior: commission eligible only when invoice exists; commission payable only when marked collected
- if collection status is not available, return `needs_human=true` for payability while still computing “eligible commission”

Time tracking integration is unspecified; therefore Module 7 will not compute hourly wages or overtime from clocks.

### Odoo operations (minimal and safe)

If HR models are available:

- ensure `hr.employee` exists / lookup employee by work email
- read-only payroll inquiry can:
- list last payslips (if `hr.payslip` accessible)
- compute commission report (from `account.move`/invoice data if accessible and linked)

If HR models are unavailable but `project.task` exists:

- onboarding/training tasks created in project module as the tracking system of record.

All writes must be audited in `audit_log` with:

- `intent`, `brain=people`, `command_json`, `odoo_result_json` (redacted)

### Scripts (exact)

`scripts/discover_odoo_hr_payroll.py` must:

- authenticate via Module 2 env vars
- check read access to:
- `hr.employee`
- `hr.applicant` (optional)
- `hr.payslip` (optional)
- `project.task` (fallback)
- print capability summary
- exit non-zero only if **both** HR tracking and fallback tracking are unavailable (i.e., cannot track anything)

`scripts/verify_people_onboarding.py` must:

- ensure onboarding catalog contains the exact RDD items (non-empty)
- print total checklist items and categories
- PASS/FAIL

`scripts/verify_people_training.py` must:

- ensure training catalog includes:
- 14-day onboarding marker
- 30/60/90 ramp marker
- the training topics list (non-empty)
- PASS/FAIL

`scripts/verify_people_payroll_rules.py` must:

- load `tests/fixtures/people_samples.json`
- compute commission for sample invoices
- compare to expected commission values
- PASS/FAIL

### Tests (exact)

1) `tests/test_people_onboarding_catalog.py`

- asserts onboarding checklist matches the RDD items (count + key strings)

2) `tests/test_people_training_catalog.py`

- asserts training catalog contains the required anchors (14-day + 30/60/90 + topics)

3) `tests/test_people_payroll_rules.py`

- validates commission calculations for repairs vs installs
- validates “eligible vs payable” behavior based on invoice/collection flags

4) `tests/test_people_odoo_mocked.py`

- mocked `OdooClient` asserts:
- `hr.employee` lookup by email (if configured)
- `project.task` creation for onboarding items (fallback path)

### Acceptance criteria (Module 7 is “done” when)

- `uv run python scripts/verify_people_onboarding.py` prints PASS and exits 0.
- `uv run python scripts/verify_people_training.py` prints PASS and exits 0.
- `uv run python scripts/verify_people_payroll_rules.py` prints PASS and exits 0.
- `uv run pytest -k people` passes.
- If `RUN_ODOO_INTEGRATION_TESTS=1`, `scripts/discover_odoo_hr_payroll.py` prints capability summary (read-only).
- `.cursor/context.json` updated with:
- supported intents (hiring/onboarding/payroll)
- onboarding checklist summary
- training program summary
- payroll commission rules summary
- chosen Odoo tracking model strategy (HR models vs `project.task` fallback)
- module7 status = done

### “Module done” validation checklist (copy/paste runnable)

1) Run unit tests

- `uv run pytest -k people`
- Expected: all green

2) Validate onboarding/training/payroll scripts

- `uv run python scripts/verify_people_onboarding.py`
- `uv run python scripts/verify_people_training.py`
- `uv run python scripts/verify_people_payroll_rules.py`
- Expected: PASS

3) (Optional) Validate Odoo HR/Payroll capability (read-only)

- `export RUN_ODOO_INTEGRATION_TESTS=1`
- `uv run python scripts/discover_odoo_hr_payroll.py`
- Expected: PASS capability summary

4) Update project context

- Update `.cursor/context.json` (no secrets)

## Module 8: Voice + Chat integration

### Module objective

Implement the **transport layer** that connects external channels to our internal command system:

- **Voice**: Vapi calls our API tool endpoint(s) and sends call lifecycle webhooks
- **Chat**: website chat posts messages to our API

Module 8 must ensure:

- both channels go through the **same HAEL pipeline** (Module 3)
- HAEL routes to the correct brain (Modules 4–7)
- actions are **idempotent** and **audited**
- responses are returned in a format the channel can use (Vapi tool response vs chat response)

### Non-goals (explicit)

- No new business logic rules (those live in Modules 4–7)
- No KPI aggregation/report delivery (Module 9)
- No Fly deployment wiring (Module 10)

### Inputs (source of truth)

- `Requirements.md`: “Voice IVR Bot” and “Website Chat Bot”.
- RDD Section 7: Voice agent configuration requirements (Vapi + Twilio strategy).
- Module 3: HAEL command schema, extractor, and router.
- Modules 4–7: brain handlers and “needs_human” behavior.
- Module 1 DB: idempotency/audit/jobs.

### Security constraints (non-negotiable)

- Do not store or log Vapi/Twilio secrets.
- Webhook endpoints must support signature verification **if** a shared secret is configured (optional by env).
- Every inbound request must carry/receive a `request_id` and be written to `audit_log`.

### Channel contracts (what Module 8 implements)

#### Voice (Vapi)

We will implement:1) **One primary Vapi tool endpoint** that Vapi can call from the assistant:

- `POST /vapi/tools/hael_route`

2) **One Vapi webhook endpoint** for call lifecycle + transcript events:

- `POST /webhooks/vapi`

Design choice (to prevent prompt/tool sprawl):

- Vapi uses **a single tool** (`hael_route`) that passes raw user text or transcript snippet; our backend does routing and invokes the right brain.

#### Chat (Website)

We will implement:

- `POST /chat/message` for website chat messages that calls the same HAEL route and returns a response for the widget.

### Required environment variables (Module 8)

Voice:

- `VAPI_API_KEY` (only needed if we call Vapi APIs; optional in Module 8)
- `VAPI_WEBHOOK_SECRET` (optional; used to verify incoming webhooks if supported)

Chat:

- `CHAT_SHARED_SECRET` (optional; for basic auth between site and API)

Twilio (placeholder; not required to fully function in Module 8):

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

### Deliverables (exact files to create/update)

Create/Update:

- `src/webhooks/`:
- `src/webhooks/vapi.py` (new): Vapi webhook router + handlers
- `src/webhooks/__init__.py` (update): export router
- `src/api/` (new; or place in `src/main.py` if keeping minimal):
- `src/api/vapi_tools.py` (new): `/vapi/tools/*` endpoints
- `src/api/chat.py` (new): `/chat/*` endpoints
- `src/api/__init__.py` (new)
- `src/integrations/`:
- `src/integrations/vapi_client.py` (new, optional): Vapi REST client (only if needed)
- `src/integrations/twilio_client.py` (new, optional placeholder): Twilio wrapper (warm transfer/SMS later)
- `src/utils/`:
- `src/utils/webhook_security.py` (new/update): verify webhook signature if secret exists (pluggable)
- `src/utils/redaction.py` (new): redact sensitive fields from logs/audit payloads
- `scripts/`:
- `scripts/verify_vapi_tool_route.py` (new): posts fixture payloads to `/vapi/tools/hael_route` and asserts output
- `scripts/verify_chat_route.py` (new): posts fixture payloads to `/chat/message` and asserts output
- `scripts/verify_vapi_webhook.py` (new): posts fixture webhook payload to `/webhooks/vapi` and asserts audit writes
- `tests/fixtures/`:
- `tests/fixtures/vapi_tool_payloads.json` (new)
- `tests/fixtures/vapi_webhook_payloads.json` (new)
- `tests/fixtures/chat_payloads.json` (new)
- `tests/`:
- `tests/test_vapi_tools.py` (new)
- `tests/test_vapi_webhooks.py` (new)
- `tests/test_chat_api.py` (new)
- `.cursor/context.json` (update at module completion): add channel endpoints + tool names + webhook notes (no secrets)

### API endpoint specs (exact)

#### 1) `POST /vapi/tools/hael_route`

Purpose:

- Vapi calls this tool to process the latest user request.

Request schema (we define our own stable schema and map from Vapi’s tool-call shape):

- `request_id` (string, required)
- `call_id` (string, required) — from Vapi
- `tool_call_id` (string, required) — from Vapi
- `user_text` (string, required) — what caller just said (or transcript snippet)
- `conversation_context` (optional string) — last assistant message / summary
- `channel` fixed to `voice`

Processing (deterministic):1) Build an idempotency key: `vapi:{call_id}:{tool_call_id}`2) If idempotency key already completed → return stored response_json3) Run HAEL extractor/router on `user_text` → `HaelCommand`4) Invoke the routed brain handler:

- `ops.handle_ops_command` for OPS intents
- `core.handle_core_command` for CORE intents
- `revenue.handle_revenue_command` for quote_request
- `people.handle_people_command` for HR/payroll intents

5) Convert brain result into a Vapi-friendly tool response:

- `speak` (string): what assistant should say next
- `action` (string): `completed|needs_human|unsupported|error`
- `data` (json): structured result (safe, redacted)

6) Persist final tool response in `idempotency_keys.response_json` and mark completed.7) Write an `audit_log` record referencing:

- request_id, call_id, tool_call_id
- intent, brain
- command_json (redacted)
- odoo_result_json (redacted)

Response schema:

- `speak` (string)
- `action` (string)
- `data` (object)

#### 2) `POST /webhooks/vapi`

Purpose:

- capture call lifecycle events + transcript summaries
- used for audit trails and later KPI work

Request handling:

- verify signature if `VAPI_WEBHOOK_SECRET` configured
- parse payload and extract:
- `call_id`
- `event_type` (call_started/call_ended/transcript/tool_called etc.)
- transcript text (if present)
- write to `audit_log` with `channel=voice` and status `received`
- do **not** trigger brain actions here (tool endpoint does actions)

Response:

- `{ "status": "ok" }`

#### 3) `POST /chat/message`

Purpose:

- website chat sends a user message; we route and respond deterministically.

Request schema:

- `request_id` (string, required)
- `session_id` (string, required)
- `user_text` (string, required)
- `channel` fixed to `chat`

Idempotency key:

- `chat:{session_id}:{sha256(user_text)}` or a client-provided message id if available

Processing:

- same pipeline as Vapi tool route:
- HAEL → brain → structured response

Response schema:

- `reply_text` (string)
- `action` (string)
- `data` (object)

### “needs_human” handling (consistent across channels)

If the brain returns `needs_human`:

- Voice tool response sets `action="needs_human"` and `speak` instructs caller what to provide next (based on `missing_fields`).
- Chat response sets `action="needs_human"` and includes `missing_fields` in `data`.

### Tests and validation scripts (exact)

Fixtures must include at least:

- Voice: a `quote_request` payload routes to REVENUE-BRAIN (needs_human depending on missing fields)
- Voice: a `service_request` payload routes to OPS-BRAIN
- Voice: a `billing_inquiry` routes to CORE-BRAIN
- Voice: an unknown message returns `action=needs_human` or `unsupported`
- Chat: same cases as above but via `/chat/message`
- Webhook: call_ended with transcript writes audit_log record

Scripts:

- `scripts/verify_vapi_tool_route.py`:
- posts fixture payloads to `/vapi/tools/hael_route`
- asserts deterministic `action` and routed brain per expected fixture result
- prints PASS/FAIL and exits non-zero on failure
- `scripts/verify_chat_route.py`:
- posts fixtures to `/chat/message`
- asserts `reply_text` is present and `action` matches expected
- `scripts/verify_vapi_webhook.py`:
- posts webhook fixtures to `/webhooks/vapi`
- asserts HTTP 200 and that an audit_log row is created (requires DB)

### Acceptance criteria (Module 8 is “done” when)

- `uv run pytest -k vapi` and `uv run pytest -k chat` pass.
- `uv run python scripts/verify_vapi_tool_route.py` prints PASS and exits 0.
- `uv run python scripts/verify_chat_route.py` prints PASS and exits 0.
- With DB configured, `uv run python scripts/verify_vapi_webhook.py` prints PASS and exits 0.
- Idempotency works for duplicate tool calls (same call_id/tool_call_id returns same response).
- `.cursor/context.json` updated with:
- channel endpoints list
- Vapi tool name(s)
- webhook path(s) and verification behavior
- module8 status = done

### “Module done” validation checklist (copy/paste runnable)

1) Run unit tests

- `uv run pytest -k vapi`
- `uv run pytest -k chat`
- Expected: all green

2) Validate tool routing

- `uv run python scripts/verify_vapi_tool_route.py`
- Expected: PASS

3) Validate chat routing

- `uv run python scripts/verify_chat_route.py`
- Expected: PASS

4) Validate webhook ingestion (requires DB)

- `uv run python scripts/verify_vapi_webhook.py`
- Expected: PASS

5) Update project context

- Update `.cursor/context.json` (no secrets)

## Module 9: KPI + reporting

### Module objective

Implement the **KPI + Reporting engine** that turns operational/financial activity into scheduled, shareable reports:

- compute KPIs on schedules (daily/weekly/monthly initially; quarterly/annual defined but can be “report definitions only” if data is missing)
- generate structured report artifacts (JSON first; optional PDF later)
- deliver reports via configured channels:
- email (if SMTP provider configured)
- SMS summaries (Twilio, if configured)
- Odoo “notes/chatter” (if model access supports it)
- provide internal preview endpoints so we can validate output without relying on external delivery

This module must build on previous modules:

- **Data sources**: Odoo (Module 2) + our audit/idempotency/job tables (Module 1) + brain outputs (Modules 4–7) + channel events (Module 8).
- **Definitions**: Report definitions and recipients from RDD Section 3.4 and CORE-BRAIN reporting catalog (Module 5).

### Non-goals (explicit)

- No new OPS/CORE/REVENUE/PEOPLE business logic rules (Modules 4–7 own those)
- No Fly.io deployment mechanics (Module 10)
- No “perfect BI dashboard UI” (API-first outputs; optional UI later)

### Inputs (source of truth)

- `Requirements.md`: “KPI Dashboard: Real-time business performance tracking”, reporting + alerts.
- RDD Section 3.4: KPI definitions (daily/weekly/monthly/quarterly/annual) + recipients and delivery methods (email, Odoo dashboard, SMS summary).
- Module 5 (CORE): reporting catalog (lists of metrics + recipients intent).
- Module 1 DB: `audit_log` (events), `jobs` (scheduling), `idempotency_keys` (dedupe).

### Delivery methods (MVP behavior)

To avoid blocking on external provider setup:

- Reports are always persisted to Postgres (report artifacts table added in Module 9).
- Email/SMS/Odoo posting are **adapters**:
- if configured, send
- if not configured, mark delivery as `skipped_not_configured` and keep report available via preview endpoints

### Required environment variables (Module 9)

Scheduling:

- `REPORT_TIMEZONE` (default `America/Chicago` unless you specify otherwise)

Email (optional):

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`

SMS (optional; uses Twilio vars from Module 8):

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

Recipients (required to deliver externally; otherwise preview-only):

- `REPORT_RECIPIENTS_JSON` (JSON string with named recipients and channels; no secrets)
- Example shape (names/emails/phones): `{ "daily": { "email": [...], "sms": [...] }, "weekly": ... }`

### Database additions (Module 9)

Add a new table to persist outputs:1) `report_runs`

- `id` (PK)
- `created_at`
- `report_type` (text: `daily|weekly|monthly|quarterly|annual`)
- `period_start` (timestamp/date)
- `period_end` (timestamp/date)
- `status` (text: `generated|delivered|partial|failed`)
- `report_json` (jsonb)
- `summary_text` (text; SMS-friendly)
- `correlation_id` (request_id or job_id)

2) `report_deliveries`

- `id` (PK)
- `created_at`
- `report_run_id` (FK)
- `channel` (text: `email|sms|odoo`)
- `recipient` (text)
- `status` (text: `sent|failed|skipped_not_configured`)
- `provider_message_id` (text nullable)
- `error_message` (text nullable)

Indexes:

- `report_runs(report_type, period_start)`
- `report_deliveries(report_run_id, channel)`

### Job runner strategy (deterministic, Postgres-backed)

Use the existing `jobs` table from Module 1 and implement a single in-process worker that:

- polls for due jobs every N seconds (e.g., 10s)
- claims jobs using `SELECT ... FOR UPDATE SKIP LOCKED`
- marks job status `running` → `succeeded|failed`
- writes `last_error` on failures

Important:

- The worker must use a DB-based lock so only one instance processes jobs at a time when deployed (e.g., advisory lock).

### KPI computation strategy (explicit, no guessing)

KPIs are computed from two sources:1) **Odoo-derived metrics** (preferred when available; discovery-driven):

- invoices/payments (accounting)
- leads/opportunities (CRM)
- work orders/jobs (field service/project)
- inventory/POs (inventory/purchase)

2) **Internal system metrics** from `audit_log`:

- calls received/handled (voice webhook + vapi tool usage)
- bookings attempted/succeeded (brain results audited)
- errors and `needs_human` rate

If a KPI requires a source we don’t have, it must be:

- returned as `null` with `missing_source` reason, not fabricated.

### KPI definitions (what we implement first)

MVP set for Module 9 (chosen because we can compute them with typical Odoo + our audit log):Daily (from RDD “Daily Execution KPIs”, minimal subset):

- revenue_collected_today (Odoo payments if available; else null)
- revenue_billed_today (Odoo invoices if available; else null)
- outstanding_ar_balance (Odoo AR if available; else null)
- calls_received (audit_log channel=voice count)
- appointments_booked (from OPS audit outcomes)
- jobs_completed (Odoo if available; else from audit outcomes)
- errors_today (audit_log status=error count)

Weekly/Monthly:

- lead_count (Odoo crm.lead)
- close_rate (if Odoo has won/lost stages; else null)
- avg_ticket_size (if invoices available; else null)
- payroll_percent_of_revenue (if payroll model available; else null)

We will still store the full RDD KPI catalog in code (as “defined-but-not-computable-yet” entries) to avoid losing scope.

### Report generation (exact outputs)

For each report run, persist:

- `report_json`:
- `generated_at`
- `period_start`, `period_end`, `timezone`
- `kpis`: map of KPI name → `{ value, unit, source, missing_reason }`
- `notes`: list (e.g., data gaps)
- `summary_text`:
- a short, SMS-safe summary (<= 600 chars) with key metrics and any alerts

### Alerts (deterministic triggers, MVP)

Implement a small set of alert triggers from RDD “AI early warning system” as simple thresholds, but only when inputs exist:

- cash_runway_below_days (requires cash + burn; likely deferred)
- backlog_exceeds_capacity (requires backlog + capacity; likely deferred)
- errors_spike (available from audit_log)

Alerts are included in report_json and optionally sent via SMS.

### Deliverables (exact files to create/update)

Create/Update:

- `src/reporting/` (new):
- `src/reporting/schema.py` (new): Pydantic models for KPI definitions, KPI values, report run outputs
- `src/reporting/kpi_catalog.py` (new): full KPI catalog from RDD (definitions only) + which are computable
- `src/reporting/compute.py` (new): KPI compute functions (Odoo + audit_log)
- `src/reporting/generate.py` (new): report assembly (json + summary_text)
- `src/reporting/delivery/` (new):
    - `email_smtp.py` (new): SMTP sender adapter (optional)
    - `sms_twilio.py` (new): Twilio SMS adapter (optional)
    - `odoo_note.py` (new): Odoo posting adapter (optional, discovery-driven)
- `src/reporting/scheduler.py` (new): job scheduling helpers (create jobs for daily/weekly/monthly)
- `src/reporting/worker.py` (new): in-process job worker loop + DB locking
- `src/db/models.py` (update): add SQLAlchemy models for `report_runs` and `report_deliveries`
- `src/api/reports.py` (new): report preview endpoints
- `src/api/__init__.py` (update): include reports router
- Scripts:
- `scripts/run_report_once.py` (new): generate a report for a given period and print/store it
- `scripts/verify_reporting_fixtures.py` (new): run KPI computations on fixtures and assert expected outputs
- Tests/fixtures:
- `tests/fixtures/reporting_samples.json` (new): controlled input events and expected KPI outputs
- `tests/test_reporting_compute.py` (new)
- `tests/test_reporting_generate.py` (new)
- `tests/test_reporting_worker.py` (new): job claiming logic (DB required; can use sqlite in-memory for unit, postgres for integration)
- `.cursor/context.json` (update at module completion): list KPIs implemented, schedules, endpoints, and delivery adapters (no secrets)

### API endpoints (exact, for validation)

Add these read-only endpoints:

- `GET /reports/latest?type=daily|weekly|monthly`
- returns the most recent `report_run` (json)
- `GET /reports/runs?type=...&limit=...`
- lists stored report runs
- `POST /reports/run-once`
- triggers a report generation immediately for a specified type/period (admin-only; guarded by env secret if needed)

### Scheduling (what gets scheduled)

Create jobs (in Postgres `jobs` table) for:

- daily report at a configured time (e.g., 6pm local)
- weekly report (e.g., Friday 6pm)
- monthly report (e.g., last day 6pm)

All schedule times must respect `REPORT_TIMEZONE`.

### Acceptance criteria (Module 9 is “done” when)

- Reports are generated and persisted:
- `uv run python scripts/run_report_once.py --type daily --date 2026-01-02` (example) succeeds
- Unit tests pass:
- `uv run pytest -k reporting`
- Worker can claim and run a due job deterministically (local):
- create a job → worker executes → report_run created
- No KPI is fabricated:
- any missing data sources produce `null` with a `missing_reason`
- `.cursor/context.json` updated with:
- implemented KPIs list
- schedules (daily/weekly/monthly)
- report endpoints
- delivery adapters and configuration keys
- module9 status = done

### “Module done” validation checklist (copy/paste runnable)

1) Run unit tests

- `uv run pytest -k reporting`
- Expected: all green

2) Generate one report locally

- `uv run python scripts/run_report_once.py --type daily --date 2026-01-02`
- Expected: report_run persisted + printed summary

3) Validate fixtures

- `uv run python scripts/verify_reporting_fixtures.py`
- Expected: PASS