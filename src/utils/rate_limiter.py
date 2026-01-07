"""
HAES HVAC - Rate Limiting

Simple in-memory rate limiter with sliding window.
For production, consider Redis-backed rate limiting.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_window: int = 100
    window_seconds: int = 60
    enabled: bool = True


class RateLimiter:
    """
    Simple sliding window rate limiter.

    Tracks requests per key (usually IP address) and enforces
    a maximum number of requests per time window.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """
        Check if a request is allowed for the given key.

        Args:
            key: The rate limit key (e.g., IP address)

        Returns:
            Tuple of (allowed, remaining, retry_after_seconds)
        """
        if not self.config.enabled:
            return True, self.config.requests_per_window, 0

        now = time.time()
        window_start = now - self.config.window_seconds

        with self._lock:
            # Clean old requests
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > window_start
            ]

            current_count = len(self._requests[key])
            remaining = max(0, self.config.requests_per_window - current_count)

            if current_count >= self.config.requests_per_window:
                # Find when the oldest request will expire
                oldest = min(self._requests[key]) if self._requests[key] else now
                retry_after = int(oldest + self.config.window_seconds - now) + 1
                return False, 0, retry_after

            # Add this request
            self._requests[key].append(now)
            return True, remaining - 1, 0

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        with self._lock:
            self._requests.pop(key, None)

    def clear_all(self) -> None:
        """Clear all rate limit data."""
        with self._lock:
            self._requests.clear()


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def configure_rate_limiter(config: RateLimitConfig) -> RateLimiter:
    """Configure and return the global rate limiter."""
    global _rate_limiter
    _rate_limiter = RateLimiter(config)
    return _rate_limiter


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request.

    Handles X-Forwarded-For header for reverse proxy setups.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    
    if request.client:
        return request.client.host
    
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Applies rate limiting based on client IP address.
    Excludes health check endpoints.
    """

    # Paths that should bypass rate limiting
    EXCLUDED_PATHS = {"/", "/health", "/monitoring/metrics", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, config: RateLimitConfig | None = None):
        super().__init__(app)
        self.limiter = configure_rate_limiter(config or RateLimitConfig())

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with rate limiting."""
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Get client identifier
        client_ip = get_client_ip(request)

        # Check rate limit
        allowed, remaining, retry_after = self.limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": retry_after,
                    }
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Limit": str(self.limiter.config.requests_per_window),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.config.requests_per_window)

        return response

