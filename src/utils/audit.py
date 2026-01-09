"""
HAES HVAC - Audit Logging Utilities

Helpers for writing to the audit_log table for traceability and KPI computation.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.db.models import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    session: Session,
    request_id: str | None = None,
    channel: str = "system",
    actor: str | None = None,
    intent: str | None = None,
    brain: str | None = None,
    command_json: dict[str, Any] | None = None,
    odoo_result_json: dict[str, Any] | None = None,
    status: str = "received",
    error_message: str | None = None,
) -> AuditLog:
    """
    Write an event to the audit_log table.
    
    Args:
        session: SQLAlchemy database session
        request_id: Unique request identifier
        channel: Input channel (voice, chat, system)
        actor: Caller/visitor identifier if available
        intent: HAEL intent classification
        brain: Target brain (ops, core, revenue, people)
        command_json: Full HAEL command as JSON (redacted)
        odoo_result_json: Odoo operation result as JSON (redacted)
        status: Event status (received, processed, error)
        error_message: Error message if status is error
        
    Returns:
        Created AuditLog record
    """
    record = AuditLog(
        request_id=request_id,
        channel=channel,
        actor=actor,
        intent=intent,
        brain=brain,
        command_json=command_json,
        odoo_result_json=odoo_result_json,
        status=status,
        error_message=error_message,
    )
    session.add(record)
    session.commit()
    
    logger.debug(
        f"Audit log: request_id={request_id}, channel={channel}, "
        f"intent={intent}, brain={brain}, status={status}"
    )
    
    return record


def log_vapi_tool_call(
    session: Session,
    request_id: str,
    call_id: str | None,
    tool_call_id: str | None,
    intent: str | None,
    brain: str | None,
    parameters: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    odoo_result: dict[str, Any] | None = None,
    status: str = "processed",
    error_message: str | None = None,
) -> AuditLog:
    """
    Log a Vapi tool call event.
    
    Args:
        session: Database session
        request_id: Internal request ID
        call_id: Vapi call ID
        tool_call_id: Vapi tool call ID
        intent: Detected intent
        brain: Target brain
        parameters: Tool call parameters (redacted)
        result: Tool call result (speak, action, data)
        odoo_result: Odoo operation result
        status: Event status
        error_message: Error if any
        
    Returns:
        Created AuditLog record
    """
    # Build command JSON with context
    command_json = {
        "call_id": call_id,
        "tool_call_id": tool_call_id,
        "parameters": _redact_sensitive(parameters) if parameters else None,
        "result": result,
    }
    
    # Redact sensitive data from Odoo result
    odoo_result_json = _redact_sensitive(odoo_result) if odoo_result else None
    
    return log_event(
        session=session,
        request_id=request_id,
        channel="voice",
        actor=call_id,  # Use call_id as actor identifier
        intent=intent,
        brain=brain,
        command_json=command_json,
        odoo_result_json=odoo_result_json,
        status=status,
        error_message=error_message,
    )


def log_vapi_webhook(
    session: Session,
    call_id: str | None,
    event_type: str,
    event_data: dict[str, Any] | None = None,
    summary: str | None = None,
    duration_seconds: int | None = None,
    ended_reason: str | None = None,
) -> AuditLog:
    """
    Log a Vapi webhook event (call lifecycle).
    
    Args:
        session: Database session
        call_id: Vapi call ID
        event_type: Event type (call_started, call_ended, etc.)
        event_data: Raw event data (redacted)
        summary: Call summary (for end-of-call)
        duration_seconds: Call duration
        ended_reason: Reason call ended
        
    Returns:
        Created AuditLog record
    """
    command_json = {
        "event_type": event_type,
        "call_id": call_id,
        "summary": summary[:500] if summary else None,  # Truncate long summaries
        "duration_seconds": duration_seconds,
        "ended_reason": ended_reason,
    }
    
    return log_event(
        session=session,
        request_id=call_id,  # Use call_id as request_id for webhooks
        channel="voice",
        actor=call_id,
        intent=f"webhook:{event_type}",
        brain=None,
        command_json=command_json,
        odoo_result_json=None,
        status="received",
        error_message=None,
    )


def log_chat_message(
    session: Session,
    request_id: str,
    session_id: str,
    intent: str | None,
    brain: str | None,
    user_text: str | None = None,
    result: dict[str, Any] | None = None,
    odoo_result: dict[str, Any] | None = None,
    status: str = "processed",
    error_message: str | None = None,
) -> AuditLog:
    """
    Log a chat message event.
    
    Args:
        session: Database session
        request_id: Internal request ID
        session_id: Chat session ID
        intent: Detected intent
        brain: Target brain
        user_text: User message text
        result: Response data
        odoo_result: Odoo operation result
        status: Event status
        error_message: Error if any
        
    Returns:
        Created AuditLog record
    """
    command_json = {
        "session_id": session_id,
        "user_text": user_text[:500] if user_text else None,  # Truncate
        "result": result,
    }
    
    return log_event(
        session=session,
        request_id=request_id,
        channel="chat",
        actor=session_id,
        intent=intent,
        brain=brain,
        command_json=command_json,
        odoo_result_json=_redact_sensitive(odoo_result) if odoo_result else None,
        status=status,
        error_message=error_message,
    )


def _redact_sensitive(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Redact sensitive fields from a dictionary.
    
    Removes or masks fields that might contain PII or secrets.
    """
    if data is None:
        return None
    
    # Fields to redact entirely
    REDACT_FIELDS = {
        "password", "api_key", "token", "secret", "authorization",
        "credit_card", "ssn", "social_security",
    }
    
    # Fields to truncate/mask
    MASK_FIELDS = {
        "phone": lambda v: f"***{str(v)[-4:]}" if v and len(str(v)) > 4 else "***",
        "email": lambda v: f"{str(v)[:2]}***@***" if v and "@" in str(v) else "***",
    }
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        if key_lower in REDACT_FIELDS:
            result[key] = "***REDACTED***"
        elif key_lower in MASK_FIELDS:
            result[key] = MASK_FIELDS[key_lower](value)
        elif isinstance(value, dict):
            result[key] = _redact_sensitive(value)
        elif isinstance(value, list):
            result[key] = [
                _redact_sensitive(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result
