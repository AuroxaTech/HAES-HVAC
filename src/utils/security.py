"""
HAES HVAC - Security Utilities

Security headers and production hardening.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Strict-Transport-Security: Enforce HTTPS
    - Content-Security-Policy: Restrict resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Restrict browser features
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        settings = get_settings()

        # Always add these headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS only in production with HTTPS
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        # Relaxed for API responses but strict for any HTML
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )

        # Permissions Policy (disable unnecessary browser features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        return response


def validate_environment_secrets() -> list[str]:
    """
    Validate that required secrets are configured.

    Returns a list of missing/invalid secrets.
    Should be called at startup.
    """
    settings = get_settings()
    warnings = []

    # In production, all secrets should be set
    if settings.is_production:
        if not settings.VAPI_WEBHOOK_SECRET:
            warnings.append("VAPI_WEBHOOK_SECRET not configured - webhook verification disabled")

        if not settings.TWILIO_AUTH_TOKEN:
            warnings.append("TWILIO_AUTH_TOKEN not configured - SMS delivery disabled")

        if not settings.DATABASE_URL or "localhost" in settings.DATABASE_URL:
            warnings.append("DATABASE_URL appears to be local - ensure production database is configured")

        if settings.DATABASE_URL and "password" not in settings.DATABASE_URL.lower():
            warnings.append("DATABASE_URL may be missing authentication credentials")

    return warnings


def log_security_warnings() -> None:
    """Log any security configuration warnings at startup."""
    warnings = validate_environment_secrets()
    for warning in warnings:
        logger.warning(f"[SECURITY] {warning}")


def mask_sensitive_data(data: dict, keys_to_mask: set[str] | None = None) -> dict:
    """
    Mask sensitive values in a dictionary for logging.

    Args:
        data: Dictionary that may contain sensitive values
        keys_to_mask: Set of keys to mask (defaults to common sensitive keys)

    Returns:
        Dictionary with sensitive values masked
    """
    if keys_to_mask is None:
        keys_to_mask = {
            "password", "secret", "token", "api_key", "apikey",
            "auth", "authorization", "credential", "key",
            "ssn", "social_security", "credit_card", "card_number",
        }

    def should_mask(key: str) -> bool:
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in keys_to_mask)

    def mask_value(value: str) -> str:
        if len(value) <= 4:
            return "****"
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"

    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = mask_sensitive_data(value, keys_to_mask)
        elif isinstance(value, str) and should_mask(key):
            result[key] = mask_value(value)
        else:
            result[key] = value

    return result

