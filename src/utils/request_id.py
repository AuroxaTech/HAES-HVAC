"""
HAES HVAC Request ID Management

Context variable for tracking request IDs across async operations.
"""

import uuid
from contextvars import ContextVar

# Context variable to store the current request ID
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """
    Get the current request ID from context.

    Returns:
        Current request ID or None if not set
    """
    return _request_id_ctx.get()


def set_request_id(request_id: str | None) -> None:
    """
    Set the current request ID in context.

    Args:
        request_id: Request ID to set
    """
    _request_id_ctx.set(request_id)


def generate_request_id() -> str:
    """
    Generate a new unique request ID.

    Returns:
        New UUID-based request ID
    """
    return str(uuid.uuid4())


class request_id_ctx:
    """
    Context manager for request ID scope.

    Usage:
        with request_id_ctx("my-request-id"):
            # request_id is available in this scope
            do_something()
    """

    def __init__(self, request_id: str | None = None) -> None:
        """
        Initialize context manager.

        Args:
            request_id: Request ID to use, or generate new one if None
        """
        self.request_id = request_id or generate_request_id()
        self.token = None

    def __enter__(self) -> str:
        """Enter context and set request ID."""
        self.token = _request_id_ctx.set(self.request_id)
        return self.request_id

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore previous request ID."""
        if self.token is not None:
            _request_id_ctx.reset(self.token)

