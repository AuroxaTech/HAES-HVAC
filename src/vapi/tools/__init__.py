"""
HAES HVAC - Vapi Tools

Direct Vapi tool handlers that bypass HAEL routing.
Each tool directly calls brain handlers with parsed parameters.
"""

from typing import Any, Callable

# Tool registry: maps tool names to handler functions
TOOL_REGISTRY: dict[str, Callable] = {}


def register_tool(tool_name: str, handler: Callable) -> None:
    """Register a tool handler."""
    TOOL_REGISTRY[tool_name] = handler


def get_tool_handler(tool_name: str) -> Callable | None:
    """Get a tool handler by name."""
    return TOOL_REGISTRY.get(tool_name)


def list_tools() -> list[str]:
    """List all registered tool names."""
    return list(TOOL_REGISTRY.keys())
