"""
HAES HVAC - Webhook Verification

HMAC signature verification for incoming webhooks.
"""

import hashlib
import hmac
import logging
import time
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Maximum age of webhook signature (5 minutes)
MAX_SIGNATURE_AGE_SECONDS = 300


def verify_vapi_signature(
    body: bytes,
    signature: str,
    timestamp: str | None = None,
    secret: str | None = None,
) -> bool:
    """
    Verify Vapi webhook signature.

    Vapi signs webhooks with HMAC-SHA256.

    Args:
        body: Raw request body bytes
        signature: The signature header value
        timestamp: Optional timestamp header
        secret: The webhook secret (from settings if not provided)

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret:
        settings = get_settings()
        secret = settings.VAPI_WEBHOOK_SECRET

    if not secret:
        # If no secret configured, skip verification in development
        settings = get_settings()
        if not settings.is_production:
            logger.warning("No VAPI_WEBHOOK_SECRET configured - skipping verification in development")
            return True
        logger.error("No VAPI_WEBHOOK_SECRET configured in production!")
        return False

    # Check timestamp freshness if provided
    if timestamp:
        try:
            ts = int(timestamp)
            age = abs(time.time() - ts)
            if age > MAX_SIGNATURE_AGE_SECONDS:
                logger.warning(f"Webhook signature too old: {age} seconds")
                return False
        except (ValueError, TypeError):
            logger.warning(f"Invalid timestamp format: {timestamp}")
            # Continue with signature check

    # Generate expected signature
    # Vapi uses: HMAC-SHA256(timestamp + "." + body, secret)
    if timestamp:
        payload = f"{timestamp}.".encode() + body
    else:
        payload = body

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # Compare signatures (constant-time comparison)
    # Handle both "sha256=xxx" and plain "xxx" formats
    actual = signature.replace("sha256=", "") if signature.startswith("sha256=") else signature

    is_valid = hmac.compare_digest(expected.lower(), actual.lower())

    if not is_valid:
        logger.warning("Webhook signature verification failed")

    return is_valid


def verify_twilio_signature(
    url: str,
    params: dict,
    signature: str,
    auth_token: str | None = None,
) -> bool:
    """
    Verify Twilio webhook signature.

    Twilio uses a different signing method than Vapi.

    Args:
        url: The full URL that was called
        params: POST parameters from the request
        signature: The X-Twilio-Signature header
        auth_token: Twilio auth token (from settings if not provided)

    Returns:
        True if signature is valid, False otherwise
    """
    if not auth_token:
        settings = get_settings()
        auth_token = settings.TWILIO_AUTH_TOKEN

    if not auth_token:
        settings = get_settings()
        if not settings.is_production:
            logger.warning("No TWILIO_AUTH_TOKEN configured - skipping verification in development")
            return True
        return False

    # Twilio signature: base64(HMAC-SHA1(URL + sorted_params, auth_token))
    # Build the data string
    data = url
    for key in sorted(params.keys()):
        data += key + params[key]

    # Generate expected signature
    expected = hmac.new(
        auth_token.encode(),
        data.encode(),
        hashlib.sha1,
    ).digest()

    import base64
    expected_b64 = base64.b64encode(expected).decode()

    return hmac.compare_digest(expected_b64, signature)


class WebhookVerificationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to verify webhook signatures.

    Only applies to webhook endpoints.
    """

    WEBHOOK_PATHS = {
        "/webhooks/vapi": "vapi",
        "/vapi/server": "vapi",  # Vapi Server URL endpoint
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Verify webhook signature if applicable."""
        path = request.url.path

        if path in self.WEBHOOK_PATHS:
            provider = self.WEBHOOK_PATHS[path]

            if provider == "vapi":
                # Get signature from header
                signature = request.headers.get("X-Vapi-Signature", "")
                timestamp = request.headers.get("X-Vapi-Timestamp")

                if not signature:
                    # Check if verification is required in production
                    settings = get_settings()
                    if settings.is_production and settings.VAPI_WEBHOOK_SECRET:
                        logger.error("Missing webhook signature in production")
                        return JSONResponse(
                            status_code=401,
                            content={"error": "Missing webhook signature"},
                        )
                    # Allow in development
                    return await call_next(request)

                # Read body for verification
                body = await request.body()

                # Verify signature
                if not verify_vapi_signature(body, signature, timestamp):
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid webhook signature"},
                    )

        return await call_next(request)


async def require_webhook_signature(request: Request) -> None:
    """
    Dependency to require webhook signature verification.

    Use in specific routes that need signature verification.

    Example:
        @app.post("/webhook")
        async def webhook(
            request: Request,
            _: None = Depends(require_webhook_signature)
        ):
            ...
    """
    settings = get_settings()

    if not settings.is_production:
        # Skip in development unless secret is configured
        if not settings.VAPI_WEBHOOK_SECRET:
            return

    signature = request.headers.get("X-Vapi-Signature", "")
    timestamp = request.headers.get("X-Vapi-Timestamp")

    if not signature:
        if settings.is_production:
            raise HTTPException(status_code=401, detail="Missing signature")
        return

    body = await request.body()

    if not verify_vapi_signature(body, signature, timestamp):
        raise HTTPException(status_code=401, detail="Invalid signature")

