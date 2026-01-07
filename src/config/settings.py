"""
HAES HVAC Settings

Pydantic-settings based configuration loaded from environment variables.
All secrets come from environment only - never from code or config files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # =========================================================================
    # Runtime Configuration
    # =========================================================================
    ENVIRONMENT: Literal["development", "production"] = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # =========================================================================
    # Database (PostgreSQL)
    # =========================================================================
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/haes",
        description="PostgreSQL connection string",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Pool timeout in seconds")

    # =========================================================================
    # Odoo 18 Integration
    # =========================================================================
    ODOO_BASE_URL: str = Field(default="", description="Odoo instance URL")
    ODOO_DB: str = Field(default="", description="Odoo database name")
    ODOO_USERNAME: str = Field(default="", description="Odoo username/email")
    ODOO_PASSWORD: str = Field(default="", description="Odoo password or API key")
    ODOO_TIMEOUT_SECONDS: int = Field(default=30, description="Odoo request timeout")
    ODOO_AUTH_MODE: Literal["password", "api_key"] = Field(
        default="api_key", description="Authentication mode"
    )
    ODOO_VERIFY_SSL: bool = Field(default=True, description="Verify SSL certificates")

    # =========================================================================
    # Vapi.ai Voice Integration
    # =========================================================================
    VAPI_API_KEY: str = Field(default="", description="Vapi API key")
    VAPI_WEBHOOK_SECRET: str = Field(default="", description="Vapi webhook verification secret")

    # =========================================================================
    # Twilio SMS/Voice
    # =========================================================================
    TWILIO_ACCOUNT_SID: str = Field(default="", description="Twilio Account SID")
    TWILIO_AUTH_TOKEN: str = Field(default="", description="Twilio Auth Token")
    TWILIO_PHONE_NUMBER: str = Field(default="", description="Twilio phone number")

    # =========================================================================
    # Chat Integration
    # =========================================================================
    CHAT_SHARED_SECRET: str = Field(default="", description="Chat widget shared secret")

    # =========================================================================
    # Webhook Configuration
    # =========================================================================
    WEBHOOK_BASE_URL: str = Field(default="", description="Base URL for webhooks")

    # =========================================================================
    # Reporting Configuration
    # =========================================================================
    REPORT_TIMEZONE: str = Field(default="America/Chicago", description="Report timezone")
    REPORT_RECIPIENTS_JSON: str = Field(default="{}", description="Report recipients config")

    # =========================================================================
    # Email (SMTP) - Optional
    # =========================================================================
    SMTP_HOST: str = Field(default="", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USERNAME: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")
    SMTP_FROM_EMAIL: str = Field(default="", description="From email address")

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS_PER_WINDOW: int = Field(
        default=100, description="Max requests per window"
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    @property
    def database_url_sync(self) -> str:
        """Get sync database URL (for Alembic migrations)."""
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

