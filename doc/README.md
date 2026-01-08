# HAES HVAC Business Automation System

AI-powered HVAC business automation integrating with Odoo 18 Enterprise, Vapi.ai voice agents, and Twilio for comprehensive dispatch, scheduling, invoicing, and customer service.

## Architecture

This is a **modular monolith** built with FastAPI:

- **HAEL**: Command Engine that converts conversations into structured business commands
- **CORE-BRAIN**: Pricing, accounting, compliance, and reporting rules
- **OPS-BRAIN**: Dispatch, scheduling, and work order management
- **REVENUE-BRAIN**: Leads, quoting, and sales pipeline
- **PEOPLE-BRAIN**: HR, onboarding, training, and payroll

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

1. Clone and enter the repository:
   ```bash
   cd "HAES HVAC"
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values (never commit .env)
   ```

4. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```

5. Start the development server:
   ```bash
   uv run python main.py
   ```

   Or with hot reload:
   ```bash
   uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Running Tests

```bash
uv run pytest
```

### Verification Scripts

After starting the server, validate the setup:

```bash
# Check HTTP endpoints
uv run python scripts/verify_http.py --base-url http://localhost:8000

# Check database connectivity (requires DATABASE_URL)
uv run python scripts/verify_db.py
```

## API Endpoints

### Core
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service metadata |
| GET | `/health` | Health check with DB status |
| GET | `/monitoring/metrics` | Basic metrics |

### Voice (Vapi.ai)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/vapi/tools/hael_route` | Voice agent tool endpoint |
| POST | `/webhooks/vapi` | Call lifecycle webhooks |
| GET | `/webhooks/vapi/health` | Webhook health check |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/message` | Website chat message processing |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/reports/latest` | Get latest report by type |
| POST | `/reports/run-once` | Generate report on-demand |
| GET | `/reports/runs` | List stored report runs |

## Project Structure

```
HAES HVAC/
├── main.py                 # Entry point
├── pyproject.toml          # Dependencies
├── Dockerfile              # Container build
├── .env.example            # Environment template
├── src/
│   ├── main.py             # FastAPI app
│   ├── config/             # Settings
│   ├── db/                 # Database layer
│   ├── utils/              # Shared utilities
│   ├── monitoring/         # Metrics endpoints
│   ├── integrations/       # External services (Odoo, Vapi, Twilio)
│   ├── hael/               # Command engine
│   ├── brains/             # Business logic modules
│   │   ├── core/
│   │   ├── ops/
│   │   ├── revenue/
│   │   └── people/
│   ├── webhooks/           # Inbound webhooks
│   └── models/             # Shared models
├── scripts/                # Verification/utility scripts
└── tests/                  # Test suite
```

## Environment Variables

See `.env.example` for the complete list. Key variables:

- `DATABASE_URL`: PostgreSQL connection string
- `ENVIRONMENT`: development/production
- `ODOO_*`: Odoo 18 connection settings
- `VAPI_*`: Vapi.ai configuration
- `TWILIO_*`: Twilio configuration

**Security**: Never commit `.env` or any file containing secrets.

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions.

### Quick Deploy to Fly.io

```bash
# First-time setup
fly apps create haes-hvac
fly postgres create --name haes-hvac-db
fly postgres attach haes-hvac-db --app haes-hvac

# Set required secrets
fly secrets set ENVIRONMENT=production
fly secrets set ODOO_BASE_URL="..."
fly secrets set ODOO_DB="..."
fly secrets set ODOO_USERNAME="..."
fly secrets set ODOO_PASSWORD="..."

# Deploy
fly deploy
```

### Production Checklist

Run before deploying:
```bash
fly ssh console -C "python scripts/production_checklist.py"
```

## Security Features

- **Rate Limiting**: Per-IP request rate limiting (configurable)
- **Security Headers**: HSTS, X-Frame-Options, CSP, etc.
- **Webhook Verification**: HMAC signature verification for Vapi webhooks
- **Request Idempotency**: Database-backed deduplication
- **Audit Logging**: Comprehensive action audit trail

## License

Proprietary - HAES HVAC

