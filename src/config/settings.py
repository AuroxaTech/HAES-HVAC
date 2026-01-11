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
    
    # Odoo notification user IDs (for activity assignment)
    ODOO_DISPATCH_USER_ID: int = Field(default=0, description="Odoo user ID for Dispatch")
    ODOO_LINDA_USER_ID: int = Field(default=0, description="Odoo user ID for Linda")
    ODOO_TECH_USER_IDS_JSON: str = Field(
        default='{}',
        description="JSON mapping of tech_id to Odoo user_id, e.g. {\"junior\": 123, \"bounthon\": 456}"
    )
    
    # Staff email addresses for emergency notifications
    DISPATCH_EMAIL: str = Field(default="", description="Email address for Dispatch notifications")
    LINDA_EMAIL: str = Field(default="", description="Email address for Linda notifications")
    TECH_EMAILS_JSON: str = Field(
        default='{}',
        description="JSON mapping of tech_id to email, e.g. {\"junior\": \"junior@example.com\", \"bounthon\": \"bounthon@example.com\"}"
    )

    # =========================================================================
    # Vapi.ai Voice Integration
    # =========================================================================
    VAPI_API_KEY: str = Field(default="", description="Vapi private API key")
    VAPI_PUBLIC_KEY: str = Field(default="", description="Vapi public API key")
    VAPI_WEBHOOK_SECRET: str = Field(default="", description="Vapi webhook verification secret")
    VAPI_ASSISTANT_ID: str = Field(default="", description="Vapi assistant ID")
    VAPI_TWILIO_PHONE_ID: str = Field(default="", description="Vapi Twilio phone ID")

    # =========================================================================
    # Twilio SMS/Voice
    # =========================================================================
    TWILIO_ACCOUNT_SID: str = Field(default="", description="Twilio Account SID")
    TWILIO_AUTH_TOKEN: str = Field(default="", description="Twilio Auth Token")
    TWILIO_PHONE_NUMBER: str = Field(default="", description="Twilio phone number")
    TWILIO_DRY_RUN: bool = Field(default=False, description="If true, log SMS instead of sending")
    TWILIO_TEST_TO_NUMBER: str = Field(
        default="", description="Override recipient number for testing (staging only)"
    )

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
    SMTP_USE_TLS: bool = Field(default=True, description="Use TLS for SMTP connection")
    SMTP_DRY_RUN: bool = Field(default=False, description="If true, log emails instead of sending")
    SMTP_TEST_TO_EMAIL: str = Field(
        default="", description="Override recipient email for testing (staging only)"
    )

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

    # =========================================================================
    # Feature Flags
    # =========================================================================
    FEATURE_EMERGENCY_SMS: bool = Field(
        default=True, description="Enable customer SMS confirmation for emergencies"
    )
    FEATURE_ODOO_ACTIVITIES: bool = Field(
        default=True, description="Enable Odoo mail.activity creation for emergencies"
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

