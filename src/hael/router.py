"""
HAES HVAC - HAEL Command Router

Deterministic routing of commands to brains based on intent.
Also handles required field validation and idempotency key generation.
"""

import hashlib
from datetime import datetime

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


# =============================================================================
# Intent to Brain Mapping (deterministic)
# =============================================================================

INTENT_BRAIN_MAP: dict[Intent, Brain] = {
    # OPS-BRAIN
    Intent.SERVICE_REQUEST: Brain.OPS,
    Intent.SCHEDULE_APPOINTMENT: Brain.OPS,
    Intent.RESCHEDULE_APPOINTMENT: Brain.OPS,
    Intent.CANCEL_APPOINTMENT: Brain.OPS,
    Intent.STATUS_UPDATE_REQUEST: Brain.OPS,

    # REVENUE-BRAIN
    Intent.QUOTE_REQUEST: Brain.REVENUE,

    # CORE-BRAIN
    Intent.BILLING_INQUIRY: Brain.CORE,
    Intent.PAYMENT_TERMS_INQUIRY: Brain.CORE,
    Intent.INVOICE_REQUEST: Brain.CORE,
    Intent.INVENTORY_INQUIRY: Brain.CORE,
    Intent.PURCHASE_REQUEST: Brain.CORE,

    # PEOPLE-BRAIN
    Intent.HIRING_INQUIRY: Brain.PEOPLE,
    Intent.ONBOARDING_INQUIRY: Brain.PEOPLE,
    Intent.PAYROLL_INQUIRY: Brain.PEOPLE,

    # Unknown
    Intent.UNKNOWN: Brain.UNKNOWN,
}

# =============================================================================
# Required Fields per Intent (from RDD 9.3)
# =============================================================================

# For each intent, define required fields and strongly recommended fields
REQUIRED_FIELDS: dict[Intent, dict[str, list[str]]] = {
    Intent.SERVICE_REQUEST: {
        "required": ["identity", "location", "problem_description", "urgency_level"],
        "identity": ["phone", "email", "full_name"],  # At least one
        "location": ["address", "zip_code"],  # At least one
    },
    Intent.SCHEDULE_APPOINTMENT: {
        "required": ["identity", "location", "problem_description", "urgency_level"],
        "identity": ["phone", "email", "full_name"],
        "location": ["address", "zip_code"],
    },
    Intent.RESCHEDULE_APPOINTMENT: {
        "required": ["identity"],
        "identity": ["phone", "email"],
    },
    Intent.CANCEL_APPOINTMENT: {
        "required": ["identity"],
        "identity": ["phone", "email"],
    },
    Intent.STATUS_UPDATE_REQUEST: {
        "required": ["identity"],
        "identity": ["phone", "email"],
    },
    Intent.QUOTE_REQUEST: {
        "required": ["identity", "property_type", "timeline"],
        "identity": ["phone", "email", "full_name"],
        "recommended": ["square_footage", "system_age_years", "budget_range"],
    },
    Intent.BILLING_INQUIRY: {
        "required": ["identity"],
        "identity": ["phone", "email"],
    },
    Intent.PAYMENT_TERMS_INQUIRY: {
        "required": [],  # General inquiry, no identity required
    },
    Intent.INVOICE_REQUEST: {
        "required": ["identity"],
        "identity": ["phone", "email"],
    },
    Intent.INVENTORY_INQUIRY: {
        "required": [],  # General inquiry
    },
    Intent.PURCHASE_REQUEST: {
        "required": ["identity"],
        "identity": ["phone", "email"],
    },
    Intent.HIRING_INQUIRY: {
        "required": [],  # General inquiry
    },
    Intent.ONBOARDING_INQUIRY: {
        "required": ["identity"],
        "identity": ["email"],  # Need to identify the employee
    },
    Intent.PAYROLL_INQUIRY: {
        "required": ["identity"],
        "identity": ["email"],
    },
    Intent.UNKNOWN: {
        "required": [],
    },
}


def route_command(extraction: HaelExtractionResult) -> HaelRoutingResult:
    """
    Route an extraction result to the appropriate brain.

    Args:
        extraction: Result from the extractor

    Returns:
        Routing result with brain, requires_human flag, and missing fields
    """
    intent = extraction.intent
    entities = extraction.entities

    # Determine target brain
    brain = INTENT_BRAIN_MAP.get(intent, Brain.UNKNOWN)

    # Unknown intent always requires human
    if intent == Intent.UNKNOWN or brain == Brain.UNKNOWN:
        return HaelRoutingResult(
            brain=Brain.UNKNOWN,
            requires_human=True,
            missing_fields=["intent"],
            routing_reason="Unknown or unclassified intent",
        )

    # Check required fields
    missing_fields = _check_required_fields(intent, entities)

    # Determine if human intervention is needed
    requires_human = len(missing_fields) > 0 or extraction.confidence < 0.5

    routing_reason = _build_routing_reason(intent, brain, missing_fields, extraction.confidence)

    return HaelRoutingResult(
        brain=brain,
        requires_human=requires_human,
        missing_fields=missing_fields,
        routing_reason=routing_reason,
    )


def _check_required_fields(intent: Intent, entities: Entity) -> list[str]:
    """
    Check which required fields are missing.

    Returns:
        List of missing field names
    """
    requirements = REQUIRED_FIELDS.get(intent, {"required": []})
    missing = []

    for req_type in requirements.get("required", []):
        if req_type == "identity":
            # Check if at least one identity field is present
            identity_fields = requirements.get("identity", ["phone", "email", "full_name"])
            has_identity = any(
                getattr(entities, field, None) for field in identity_fields
            )
            if not has_identity:
                missing.append("identity (phone, email, or name)")

        elif req_type == "location":
            # Check if at least one location field is present
            location_fields = requirements.get("location", ["address", "zip_code"])
            has_location = any(
                getattr(entities, field, None) for field in location_fields
            )
            if not has_location:
                missing.append("location (address or zip_code)")

        elif req_type == "problem_description":
            if not entities.problem_description:
                missing.append("problem_description")

        elif req_type == "urgency_level":
            if entities.urgency_level == UrgencyLevel.UNKNOWN:
                missing.append("urgency_level")

        elif req_type == "property_type":
            if not entities.property_type:
                missing.append("property_type")

        elif req_type == "timeline":
            if not entities.timeline:
                missing.append("timeline")

        else:
            # Direct field check
            if not getattr(entities, req_type, None):
                missing.append(req_type)

    # Also check recommended fields for quote requests (flag but don't require human)
    # This is informational only - we don't add to missing_fields

    return missing


def _build_routing_reason(
    intent: Intent,
    brain: Brain,
    missing_fields: list[str],
    confidence: float,
) -> str:
    """Build a human-readable routing reason."""
    parts = [f"Intent '{intent.value}' routed to {brain.value.upper()}-BRAIN"]

    if missing_fields:
        parts.append(f"Missing fields: {', '.join(missing_fields)}")

    if confidence < 0.5:
        parts.append(f"Low confidence ({confidence:.2f})")

    return "; ".join(parts)


def generate_idempotency_key(
    channel: Channel,
    entities: Entity,
    intent: Intent,
    timestamp: datetime,
) -> str:
    """
    Generate a deterministic idempotency key.

    The key is based on:
    - Channel
    - Identity anchor (phone/email)
    - Intent
    - Date bucket (to allow same-day deduplication)

    Returns:
        SHA256 hash as the idempotency key
    """
    # Get identity anchor
    identity = entities.phone or entities.email or entities.full_name or "anonymous"

    # Date bucket (hourly granularity for deduplication)
    date_bucket = timestamp.strftime("%Y-%m-%d-%H")

    # Build key components
    key_parts = [
        channel.value,
        identity.lower().strip(),
        intent.value,
        date_bucket,
    ]

    # Hash the key
    key_string = "|".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]


def build_hael_command(
    request_id: str,
    channel: Channel,
    raw_text: str,
    extraction: HaelExtractionResult,
    routing: HaelRoutingResult,
    timestamp: datetime | None = None,
    metadata: dict | None = None,
) -> HaelCommand:
    """
    Build a complete HaelCommand from extraction and routing results.

    Args:
        request_id: Unique request identifier
        channel: Input channel
        raw_text: Original user input
        extraction: Extraction result
        routing: Routing result
        timestamp: Optional timestamp (defaults to now)
        metadata: Optional additional metadata

    Returns:
        Complete HaelCommand
    """
    timestamp = timestamp or datetime.utcnow()

    idempotency_key = generate_idempotency_key(
        channel=channel,
        entities=extraction.entities,
        intent=extraction.intent,
        timestamp=timestamp,
    )

    return HaelCommand(
        request_id=request_id,
        channel=channel,
        raw_text=raw_text,
        intent=extraction.intent,
        brain=routing.brain,
        entities=extraction.entities,
        confidence=extraction.confidence,
        requires_human=routing.requires_human,
        missing_fields=routing.missing_fields,
        idempotency_key=idempotency_key,
        created_at=timestamp,
        metadata=metadata or {},
    )

