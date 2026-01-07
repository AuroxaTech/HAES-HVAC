"""
HAES HVAC - HAEL Command Engine

The Command Engine converts conversations into structured business commands
and routes them to the appropriate brain (CORE/OPS/REVENUE/PEOPLE).
"""

from src.hael.schema import (
    Brain,
    Channel,
    Entity,
    HaelCommand,
    HaelExtractionResult,
    HaelRoutingResult,
    Intent,
    UrgencyLevel,
)
from src.hael.router import (
    build_hael_command,
    generate_idempotency_key,
    route_command,
)
from src.hael.extractors import BaseExtractor, RuleBasedExtractor

__all__ = [
    # Schema
    "Brain",
    "Channel",
    "Entity",
    "HaelCommand",
    "HaelExtractionResult",
    "HaelRoutingResult",
    "Intent",
    "UrgencyLevel",
    # Router
    "build_hael_command",
    "generate_idempotency_key",
    "route_command",
    # Extractors
    "BaseExtractor",
    "RuleBasedExtractor",
]

