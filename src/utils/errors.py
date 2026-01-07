"""
HAES HVAC Error Handling

Custom exceptions and error codes for consistent API error responses.
"""

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"

    # Integration errors
    ODOO_ERROR = "ODOO_ERROR"
    ODOO_AUTH_ERROR = "ODOO_AUTH_ERROR"
    ODOO_RPC_ERROR = "ODOO_RPC_ERROR"
    ODOO_TRANSPORT_ERROR = "ODOO_TRANSPORT_ERROR"

    VAPI_ERROR = "VAPI_ERROR"
    TWILIO_ERROR = "TWILIO_ERROR"

    # HAEL errors
    HAEL_EXTRACTION_ERROR = "HAEL_EXTRACTION_ERROR"
    HAEL_VALIDATION_ERROR = "HAEL_VALIDATION_ERROR"
    HAEL_ROUTING_ERROR = "HAEL_ROUTING_ERROR"

    # Brain errors
    OPS_BRAIN_ERROR = "OPS_BRAIN_ERROR"
    OPS_BRAIN_NEEDS_HUMAN = "OPS_BRAIN_NEEDS_HUMAN"

    CORE_BRAIN_ERROR = "CORE_BRAIN_ERROR"
    CORE_BRAIN_NEEDS_HUMAN = "CORE_BRAIN_NEEDS_HUMAN"
    CORE_BRAIN_CAPABILITY_MISSING = "CORE_BRAIN_CAPABILITY_MISSING"

    REVENUE_BRAIN_ERROR = "REVENUE_BRAIN_ERROR"
    REVENUE_BRAIN_NEEDS_HUMAN = "REVENUE_BRAIN_NEEDS_HUMAN"
    REVENUE_BRAIN_CAPABILITY_MISSING = "REVENUE_BRAIN_CAPABILITY_MISSING"

    PEOPLE_BRAIN_ERROR = "PEOPLE_BRAIN_ERROR"
    PEOPLE_BRAIN_NEEDS_HUMAN = "PEOPLE_BRAIN_NEEDS_HUMAN"
    PEOPLE_BRAIN_CAPABILITY_MISSING = "PEOPLE_BRAIN_CAPABILITY_MISSING"


class APIError(Exception):
    """
    Base API exception with structured error response.

    All API errors should inherit from this class to ensure
    consistent error response format.
    """

    def __init__(
        self,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize API error.

        Args:
            code: Error code enum value
            message: Human-readable error message
            status_code: HTTP status code
            details: Optional additional error details
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        """
        Convert error to dictionary for JSON response.

        Args:
            request_id: Optional request ID to include

        Returns:
            Error dictionary matching the API error envelope format
        """
        error_dict: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
        }
        if request_id:
            error_dict["request_id"] = request_id
        if self.details:
            error_dict["details"] = self.details
        return {"error": error_dict}


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(APIError):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=500,
        )


class DatabaseConnectionError(APIError):
    """Database connection error."""

    def __init__(self, message: str = "Database connection failed") -> None:
        super().__init__(
            code=ErrorCode.DATABASE_CONNECTION_ERROR,
            message=message,
            status_code=503,
        )


# =============================================================================
# Odoo Integration Errors
# =============================================================================


class OdooError(APIError):
    """Base Odoo integration error."""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.ODOO_ERROR,
        message: str = "Odoo operation failed",
        status_code: int = 502,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code, details=details)


class OdooAuthError(OdooError):
    """Odoo authentication error."""

    def __init__(self, message: str = "Odoo authentication failed") -> None:
        super().__init__(
            code=ErrorCode.ODOO_AUTH_ERROR,
            message=message,
            status_code=401,
        )


class OdooRPCError(OdooError):
    """Odoo RPC call error."""

    def __init__(
        self,
        message: str = "Odoo RPC call failed",
        model: str | None = None,
        method: str | None = None,
        odoo_error: dict[str, Any] | None = None,
    ) -> None:
        details = {}
        if model:
            details["model"] = model
        if method:
            details["method"] = method
        if odoo_error:
            details["odoo_error"] = odoo_error
        super().__init__(
            code=ErrorCode.ODOO_RPC_ERROR,
            message=message,
            status_code=502,
            details=details,
        )


class OdooTransportError(OdooError):
    """Odoo transport/network error."""

    def __init__(self, message: str = "Odoo connection failed") -> None:
        super().__init__(
            code=ErrorCode.ODOO_TRANSPORT_ERROR,
            message=message,
            status_code=502,
        )


# =============================================================================
# HAEL Errors
# =============================================================================


class HaelExtractionError(APIError):
    """HAEL command extraction error."""

    def __init__(self, message: str = "Failed to extract command from input") -> None:
        super().__init__(
            code=ErrorCode.HAEL_EXTRACTION_ERROR,
            message=message,
            status_code=400,
        )


class HaelValidationError(APIError):
    """HAEL command validation error."""

    def __init__(
        self, message: str = "Command validation failed", missing_fields: list[str] | None = None
    ) -> None:
        details = {}
        if missing_fields:
            details["missing_fields"] = missing_fields
        super().__init__(
            code=ErrorCode.HAEL_VALIDATION_ERROR,
            message=message,
            status_code=400,
            details=details,
        )


# =============================================================================
# Brain Errors
# =============================================================================


class OpsBrainError(APIError):
    """OPS Brain operation error."""

    def __init__(self, message: str = "OPS Brain operation failed") -> None:
        super().__init__(
            code=ErrorCode.OPS_BRAIN_ERROR,
            message=message,
            status_code=500,
        )


class OpsBrainNeedsHuman(APIError):
    """OPS Brain requires human intervention."""

    def __init__(
        self,
        message: str = "Human intervention required",
        missing_fields: list[str] | None = None,
        missing_capabilities: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_fields:
            details["missing_fields"] = missing_fields
        if missing_capabilities:
            details["missing_capabilities"] = missing_capabilities
        super().__init__(
            code=ErrorCode.OPS_BRAIN_NEEDS_HUMAN,
            message=message,
            status_code=422,
            details=details,
        )


class CoreBrainError(APIError):
    """CORE Brain operation error."""

    def __init__(self, message: str = "CORE Brain operation failed") -> None:
        super().__init__(
            code=ErrorCode.CORE_BRAIN_ERROR,
            message=message,
            status_code=500,
        )


class CoreBrainNeedsHuman(APIError):
    """CORE Brain requires human intervention."""

    def __init__(
        self,
        message: str = "Human intervention required",
        missing_fields: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_fields:
            details["missing_fields"] = missing_fields
        super().__init__(
            code=ErrorCode.CORE_BRAIN_NEEDS_HUMAN,
            message=message,
            status_code=422,
            details=details,
        )


class CoreBrainCapabilityMissing(APIError):
    """CORE Brain missing required Odoo capability."""

    def __init__(
        self,
        message: str = "Required Odoo capability not available",
        missing_capabilities: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_capabilities:
            details["missing_capabilities"] = missing_capabilities
        super().__init__(
            code=ErrorCode.CORE_BRAIN_CAPABILITY_MISSING,
            message=message,
            status_code=501,
            details=details,
        )


class RevenueBrainError(APIError):
    """REVENUE Brain operation error."""

    def __init__(self, message: str = "REVENUE Brain operation failed") -> None:
        super().__init__(
            code=ErrorCode.REVENUE_BRAIN_ERROR,
            message=message,
            status_code=500,
        )


class RevenueBrainNeedsHuman(APIError):
    """REVENUE Brain requires human intervention."""

    def __init__(
        self,
        message: str = "Human intervention required",
        missing_fields: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_fields:
            details["missing_fields"] = missing_fields
        super().__init__(
            code=ErrorCode.REVENUE_BRAIN_NEEDS_HUMAN,
            message=message,
            status_code=422,
            details=details,
        )


class RevenueBrainCapabilityMissing(APIError):
    """REVENUE Brain missing required Odoo capability."""

    def __init__(
        self,
        message: str = "Required Odoo capability not available",
        missing_capabilities: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_capabilities:
            details["missing_capabilities"] = missing_capabilities
        super().__init__(
            code=ErrorCode.REVENUE_BRAIN_CAPABILITY_MISSING,
            message=message,
            status_code=501,
            details=details,
        )


class PeopleBrainError(APIError):
    """PEOPLE Brain operation error."""

    def __init__(self, message: str = "PEOPLE Brain operation failed") -> None:
        super().__init__(
            code=ErrorCode.PEOPLE_BRAIN_ERROR,
            message=message,
            status_code=500,
        )


class PeopleBrainNeedsHuman(APIError):
    """PEOPLE Brain requires human intervention."""

    def __init__(
        self,
        message: str = "Human intervention required",
        missing_fields: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_fields:
            details["missing_fields"] = missing_fields
        super().__init__(
            code=ErrorCode.PEOPLE_BRAIN_NEEDS_HUMAN,
            message=message,
            status_code=422,
            details=details,
        )


class PeopleBrainCapabilityMissing(APIError):
    """PEOPLE Brain missing required Odoo capability."""

    def __init__(
        self,
        message: str = "Required Odoo capability not available",
        missing_capabilities: list[str] | None = None,
    ) -> None:
        details = {}
        if missing_capabilities:
            details["missing_capabilities"] = missing_capabilities
        super().__init__(
            code=ErrorCode.PEOPLE_BRAIN_CAPABILITY_MISSING,
            message=message,
            status_code=501,
            details=details,
        )

