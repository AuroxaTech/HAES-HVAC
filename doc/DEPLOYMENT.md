# HAES HVAC Deployment Guide

## Fly.io Deployment

### Prerequisites

1. **Add Payment Method**: Fly.io requires a payment method to create apps and databases.
   - Go to: https://fly.io/dashboard/hvacr-finest/billing
   - Add a credit card or purchase credits
   - This is required before proceeding

2. Install the Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
3. Authenticate: `fly auth login`
4. Ensure `.env` file is configured with all credentials

### Quick Deployment (Automated)

After adding payment method, run the automated deployment script:

```bash
./scripts/deploy_to_fly.sh
```

This script will:
- Create the Fly.io app
- Create and attach PostgreSQL database
- Set all secrets from your `.env` file
- Configure the application

Then deploy:
```bash
fly deploy
```

### Manual Setup

If you prefer manual setup:

1. Create the app:
   ```bash
   fly apps create haes-hvac --org personal
   ```

2. Create Postgres database:
   ```bash
   fly postgres create --name haes-db --region dfw --vm-size shared-cpu-1x --volume-size 10
   fly postgres attach haes-db --app haes-hvac
   ```

3. Set secrets (never commit these!):
   ```bash
   # Database (auto-set by postgres attach)
   # fly secrets set DATABASE_URL="postgresql://..."
   
   # Odoo
   fly secrets set ODOO_BASE_URL="<your-odoo-base-url>" --app haes-hvac
   fly secrets set ODOO_DB="<your-odoo-db-name>" --app haes-hvac
   fly secrets set ODOO_USERNAME="<your-odoo-login-email>" --app haes-hvac
   fly secrets set ODOO_PASSWORD="<your-odoo-password-or-api-key>" --app haes-hvac
   
   # Vapi
   fly secrets set VAPI_API_KEY="<your-vapi-api-key>" --app haes-hvac
   
   # Twilio
   fly secrets set TWILIO_ACCOUNT_SID="<your-twilio-account-sid>" --app haes-hvac
   fly secrets set TWILIO_AUTH_TOKEN="<your-twilio-auth-token>" --app haes-hvac
   fly secrets set TWILIO_PHONE_NUMBER="<your-twilio-phone-number>" --app haes-hvac
   
   # Email (SMTP) - Optional
   fly secrets set SMTP_HOST="smtp.gmail.com" --app haes-hvac
   fly secrets set SMTP_PORT="587" --app haes-hvac
   fly secrets set SMTP_USERNAME="junior@hvacrfinest.com" --app haes-hvac
   fly secrets set SMTP_PASSWORD="<app-password>" --app haes-hvac
   fly secrets set SMTP_FROM_EMAIL="junior@hvacrfinest.com" --app haes-hvac
   fly secrets set SMTP_USE_TLS="true" --app haes-hvac
   fly secrets set SMTP_DRY_RUN="false" --app haes-hvac
   fly secrets set SMTP_TEST_TO_EMAIL="hamsimirza1@gmail.com" --app haes-hvac
   ```

4. Deploy:
   ```bash
   fly deploy
   ```

### Database Migrations

Run migrations after deployment:
```bash
fly ssh console -C "python -m alembic upgrade head"
```

Or use a release command in fly.toml:
```toml
[deploy]
  release_command = "python -m alembic upgrade head"
```

### Monitoring

- View logs: `fly logs`
- Check status: `fly status`
- SSH into app: `fly ssh console`
- View metrics: `fly dashboard`

### Health Checks

The app exposes these health endpoints:

- `GET /health` - Overall health with DB status
- `GET /monitoring/metrics` - Basic metrics
- `GET /vapi/server/health` - Vapi Server URL health check

## Vapi Integration

### Overview

The application uses **Vapi Server URL** integration for voice calls. All Vapi tool calls and transfer requests flow through:

```
POST /vapi/server
```

This endpoint handles:
- **tool-calls**: Execute the `hael_route` tool via HAES pipeline
- **transfer-destination-request**: Return transfer destination based on business hours
- **end-of-call-report**: Log call summaries
- **status-update**: Log status changes

### Vapi Dashboard Configuration

1. **Update Assistant "Riley"**:
   - Go to Vapi Dashboard > Assistants > Riley
   - Set **Server URL**: `https://haes-hvac.fly.dev/vapi/server`
   - Set **Server URL Secret**: Same as `VAPI_WEBHOOK_SECRET` in Fly.io
   - Enable **Server Messages**: `tool-calls`, `transfer-destination-request`, `end-of-call-report`, `status-update`

2. **Create/Update Tool "hael_route"**:
   - Go to Vapi Dashboard > Tools
   - Create function tool with name: `hael_route`
   - Parameters:
     - `user_text` (string, required): Customer's request
     - `conversation_context` (string, optional): Gathered info summary
   - Server URL: `https://haes-hvac.fly.dev/vapi/server`
   - Attach tool to assistant Riley

3. **System Prompt**:
   - Use the prompt from: `doc/vapi/system_prompt.md`

4. **Knowledge Base** (optional):
   - Upload docs from: `doc/vapi/kb/customer_faq.md`, `doc/vapi/kb/policies.md`

### Transfer Policy

- **During business hours (8 AM - 5 PM CST, Mon-Fri)**: Transfer to `972-372-4458`
- **After hours**: Collect callback info, no transfer

### Signature Verification

In production, all requests to `/vapi/server` require a valid signature:
- Header: `X-Vapi-Signature`
- Optional: `X-Vapi-Timestamp`

Set `VAPI_WEBHOOK_SECRET` in Fly.io to match Vapi's `serverUrlSecret`.

### Testing Vapi Integration

```bash
# Run verification script locally
python scripts/verify_vapi_server_url.py

# Run against production (unsigned - will 401)
python scripts/verify_vapi_server_url.py --prod

# Run against production with signature
VAPI_WEBHOOK_SECRET=your_secret python scripts/verify_vapi_server_url.py --prod --signed
```

### Scaling

Scale horizontally:
```bash
fly scale count 2
```

Scale vertically:
```bash
fly scale vm shared-cpu-1x --memory 1024
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | Postgres connection string |
| ENVIRONMENT | Yes | production |
| PORT | Yes | 8080 |
| ODOO_BASE_URL | Yes | Odoo instance URL |
| ODOO_DB | Yes | Odoo database name |
| ODOO_USERNAME | Yes | Odoo login |
| ODOO_PASSWORD | Yes | Odoo API key |
| VAPI_API_KEY | No | Vapi API key |
| VAPI_WEBHOOK_SECRET | No | Webhook verification |
| TWILIO_ACCOUNT_SID | No | Twilio SID |
| TWILIO_AUTH_TOKEN | No | Twilio token |
| TWILIO_PHONE_NUMBER | No | Twilio number |
| SMTP_HOST | No | SMTP server host (e.g., smtp.gmail.com) |
| SMTP_PORT | No | SMTP port (default: 587) |
| SMTP_USERNAME | No | SMTP username |
| SMTP_PASSWORD | No | SMTP password/app password |
| SMTP_FROM_EMAIL | No | From email address |
| SMTP_USE_TLS | No | Use TLS (default: true) |
| SMTP_DRY_RUN | No | Dry-run mode (default: false) |
| SMTP_TEST_TO_EMAIL | No | Test recipient email |
| REPORT_TIMEZONE | No | Default: America/Chicago |

### Troubleshooting

**App won't start:**
```bash
fly logs --app haes-hvac
fly ssh console -C "python -c 'from src.main import app; print(app)'"
```

**Database connection issues:**
```bash
fly postgres connect --app haes-hvac-db
fly ssh console -C "python scripts/verify_db.py"
```

**Check secrets are set:**
```bash
fly secrets list
```

**Test email from production:**
```bash
# Test email sending from production
fly ssh console -C "cd /app && SMTP_DRY_RUN=false SMTP_TEST_TO_EMAIL=hamsimirza1@gmail.com python scripts/test_email_send.py"
```

**Test email configuration (dry-run):**
```bash
# Check email configuration without sending
fly ssh console -C "cd /app && python scripts/test_email_send.py"
```

### Rollback

Rollback to previous deployment:
```bash
fly releases list
fly deploy --image <previous-image>
```

### Production Checklist

Run the automated production checklist before deploying:
```bash
fly ssh console -C "python scripts/production_checklist.py"
```

#### Required Configuration
- [ ] All secrets set via `fly secrets`
- [ ] `ENVIRONMENT=production`
- [ ] Database migrations applied
- [ ] Health check passing: `curl https://your-app.fly.dev/health`

#### Security Configuration
- [ ] `VAPI_WEBHOOK_SECRET` set for webhook verification
- [ ] `RATE_LIMIT_ENABLED=true` (enabled by default)
- [ ] No `.env` file in production (use environment variables only)
- [ ] SSL/HTTPS enabled (automatic with Fly)

#### Integration Configuration  
- [ ] Odoo credentials configured and tested
- [ ] Vapi API key configured
- [ ] Twilio credentials configured (for SMS)
- [ ] SMTP credentials configured (for email notifications)
- [ ] Email sending tested from production

#### Monitoring & Operations
- [ ] Logging level appropriate (`INFO` or `WARNING`)
- [ ] Error monitoring set up (consider Sentry)
- [ ] Database backup strategy configured
- [ ] Alerting configured for health check failures

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | Yes | development | Set to `production` |
| `DATABASE_URL` | Yes | - | Postgres connection string |
| `PORT` | Yes | 8080 | Service port |
| `LOG_LEVEL` | No | INFO | DEBUG, INFO, WARNING, ERROR |
| `ODOO_BASE_URL` | Yes | - | Odoo instance URL |
| `ODOO_DB` | Yes | - | Odoo database name |
| `ODOO_USERNAME` | Yes | - | Odoo login |
| `ODOO_PASSWORD` | Yes | - | Odoo API key |
| `VAPI_API_KEY` | No | - | Vapi API key |
| `VAPI_WEBHOOK_SECRET` | Recommended | - | Webhook signature verification |
| `TWILIO_ACCOUNT_SID` | No | - | Twilio SID for SMS |
| `TWILIO_AUTH_TOKEN` | No | - | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | No | - | Twilio phone number |
| `SMTP_HOST` | No | - | SMTP server host |
| `SMTP_PORT` | No | 587 | SMTP port |
| `SMTP_USERNAME` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password/app password |
| `SMTP_FROM_EMAIL` | No | - | From email address |
| `SMTP_USE_TLS` | No | true | Use TLS for SMTP |
| `SMTP_DRY_RUN` | No | false | Dry-run mode (log only) |
| `SMTP_TEST_TO_EMAIL` | No | - | Test recipient email |
| `RATE_LIMIT_ENABLED` | No | true | Enable rate limiting |
| `RATE_LIMIT_REQUESTS_PER_WINDOW` | No | 100 | Requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | No | 60 | Window duration in seconds |
| `REPORT_TIMEZONE` | No | America/Chicago | Timezone for reports |

### Security Features

The application includes several security hardening features:

1. **Security Headers**: All responses include security headers:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security` (production only)
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy` (restricts browser features)

2. **Rate Limiting**: Protects against abuse:
   - Configurable requests per time window
   - Per-IP rate limiting
   - Excludes health check endpoints

3. **Webhook Verification**: HMAC signature verification for Vapi webhooks:
   - Set `VAPI_WEBHOOK_SECRET` to enable
   - Rejects invalid/expired signatures in production

4. **Request Idempotency**: Prevents duplicate processing:
   - Database-backed idempotency keys
   - Automatic deduplication of repeated requests

