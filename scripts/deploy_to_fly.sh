#!/bin/bash
# HAES HVAC - Fly.io Deployment Script
# Run this after adding payment method to Fly.io account

set -e

echo "=========================================="
echo "HAES HVAC - Fly.io Deployment"
echo "=========================================="

# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

echo ""
echo "[1/6] Creating Fly.io app..."
fly apps create haes-hvac --org personal || echo "App may already exist"

echo ""
echo "[2/6] Creating PostgreSQL database..."
fly postgres create --name haes-db --region dfw --vm-size shared-cpu-1x --volume-size 10 || echo "Database may already exist"

echo ""
echo "[3/6] Attaching database to app..."
fly postgres attach haes-db --app haes-hvac || echo "Database may already be attached"

echo ""
echo "[4/6] Setting Odoo secrets..."
fly secrets set \
    ODOO_BASE_URL="${ODOO_BASE_URL}" \
    ODOO_DB="${ODOO_DB}" \
    ODOO_USERNAME="${ODOO_USERNAME}" \
    ODOO_PASSWORD="${ODOO_PASSWORD}" \
    ODOO_TIMEOUT_SECONDS="${ODOO_TIMEOUT_SECONDS:-30}" \
    ODOO_AUTH_MODE="${ODOO_AUTH_MODE:-password}" \
    ODOO_VERIFY_SSL="${ODOO_VERIFY_SSL:-true}" \
    --app haes-hvac

echo ""
echo "[5/6] Setting Vapi secrets..."
fly secrets set \
    VAPI_API_KEY="${VAPI_API_KEY}" \
    VAPI_WEBHOOK_SECRET="${VAPI_WEBHOOK_SECRET:-}" \
    --app haes-hvac

echo ""
echo "[6/6] Setting Twilio secrets..."
fly secrets set \
    TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID}" \
    TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN}" \
    TWILIO_PHONE_NUMBER="${TWILIO_PHONE_NUMBER}" \
    --app haes-hvac

echo ""
echo "[7/6] Setting application secrets..."
fly secrets set \
    ENVIRONMENT="production" \
    PORT="8080" \
    LOG_LEVEL="INFO" \
    REPORT_TIMEZONE="${REPORT_TIMEZONE:-America/Chicago}" \
    CHAT_SHARED_SECRET="${CHAT_SHARED_SECRET:-haes-chat-secret-change-in-production}" \
    WEBHOOK_BASE_URL="https://haes-hvac.fly.dev" \
    --app haes-hvac

echo ""
echo "=========================================="
echo "Deployment Configuration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review secrets: fly secrets list --app haes-hvac"
echo "2. Deploy: fly deploy"
echo "3. Run migrations: fly ssh console -C 'python -m alembic upgrade head'"
echo "4. Check health: fly open /health"
echo ""
