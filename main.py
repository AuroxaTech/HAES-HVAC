#!/usr/bin/env python3
"""
HAES HVAC - Entry point

Runs the FastAPI application via uvicorn.
"""

import uvicorn

from src.config.settings import get_settings


def main() -> None:
    """Run the HAES HVAC API server."""
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()

