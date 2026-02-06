"""
HAES HVAC - Main FastAPI Application

AI-powered HVAC Business Automation System integrating with
Odoo 18 Enterprise, Vapi.ai, 8x8 (customer inbound), and Twilio (SMS).
"""

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.settings import get_settings
from src.db.engine import get_engine
from src.monitoring.metrics import increment_errors, increment_requests
from src.monitoring.router import router as monitoring_router
from src.utils.errors import APIError
from src.utils.logger import get_logger, log_request, setup_logging
from src.utils.request_id import generate_request_id, get_request_id, set_request_id
from src.utils.rate_limiter import RateLimitMiddleware, RateLimitConfig
from src.utils.security import SecurityHeadersMiddleware, log_security_warnings
from src.utils.webhook_verify import WebhookVerificationMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting HAES HVAC API in {settings.ENVIRONMENT} mode")
    
    # Log security warnings
    log_security_warnings()

    yield

    # Shutdown
    logger.info("Shutting down HAES HVAC API")


# Create FastAPI application
settings = get_settings()
app = FastAPI(
    title="HAES HVAC API",
    description="AI-powered HVAC Business Automation System",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add webhook verification middleware (Vapi signatures)
app.add_middleware(WebhookVerificationMiddleware)

# Add rate limiting middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig(
            requests_per_window=settings.RATE_LIMIT_REQUESTS_PER_WINDOW,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            enabled=settings.RATE_LIMIT_ENABLED,
        ),
    )


# =============================================================================
# Middleware
# =============================================================================


@app.middleware("http")
async def request_middleware(request: Request, call_next) -> Response:
    """
    Request middleware for:
    - Request ID assignment/propagation
    - Request logging
    - Metrics collection
    """
    # Get or generate request ID
    request_id = request.headers.get("X-Request-Id") or generate_request_id()
    set_request_id(request_id)

    # Track timing
    start_time = time.time()

    # Process request
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Add request ID to response
        response.headers["X-Request-Id"] = request_id

        # Log request
        log_request(
            logger,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Increment metrics
        increment_requests()

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        increment_errors()
        log_request(
            logger,
            request.method,
            request.url.path,
            500,
            duration_ms,
            error=str(e),
        )
        raise


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors."""
    request_id = get_request_id()
    increment_errors()
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(request_id),
        headers={"X-Request-Id": request_id} if request_id else {},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = get_request_id()
    increment_errors()
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
        headers={"X-Request-Id": request_id} if request_id else {},
    )


# =============================================================================
# Core Routes
# =============================================================================


@app.get("/", tags=["core"])
async def root() -> dict[str, Any]:
    """
    Service metadata endpoint.

    Returns:
        Service name, version, and environment info
    """
    return {
        "service": "HAES HVAC API",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "description": "AI-powered HVAC Business Automation System",
    }


@app.get("/health", tags=["core"])
async def health() -> dict[str, Any]:
    """
    Health check endpoint.

    Checks:
    - Application status
    - Database connectivity

    Returns:
        Health status with component details
    """
    # Check database connectivity
    db_status = "ok"
    db_error = None
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = str(e)
        logger.error(f"Database health check failed: {e}")

    # Determine overall status
    overall_status = "ok" if db_status == "ok" else "degraded"

    response: dict[str, Any] = {
        "status": overall_status,
        "components": {
            "database": {
                "status": db_status,
            }
        },
    }

    if db_error:
        response["components"]["database"]["error"] = db_error

    return response


# =============================================================================
# Include Routers
# =============================================================================

app.include_router(monitoring_router)

# Module 8: Voice + Chat
from src.api import vapi_tools_router, vapi_server_router, chat_router
from src.webhooks import vapi_webhooks_router

app.include_router(vapi_tools_router)
app.include_router(vapi_server_router)  # Vapi Server URL endpoint
app.include_router(chat_router)
app.include_router(vapi_webhooks_router)

# Module 9: Reports
from src.api.reports import router as reports_router
app.include_router(reports_router)

