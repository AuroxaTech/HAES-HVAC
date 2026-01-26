"""
HAES HVAC - Base Tool Handler

Common utilities for all Vapi tool handlers:
- Request validation
- Parameter parsing and normalization
- Error handling
- Response formatting
- Idempotency key generation
- Audit logging
"""

import asyncio
import logging
from typing import Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.utils.idempotency import IdempotencyChecker, generate_key_hash
from src.utils.audit import log_vapi_tool_call
from src.utils.request_id import generate_request_id
from src.db.session import get_session_factory
from src.integrations.odoo import create_odoo_client_from_settings

logger = logging.getLogger(__name__)

# Idempotency scope for Vapi tools
VAPI_TOOL_SCOPE = "vapi_tool"


class ToolResponse:
    """Standard Vapi tool response format."""
    
    def __init__(
        self,
        speak: str,
        action: str = "completed",  # "completed" | "needs_human" | "error"
        data: dict[str, Any] | None = None,
    ):
        self.speak = speak
        self.action = action
        self.data = data or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "speak": self.speak,
            "action": self.action,
            "data": self.data,
        }


class BaseToolHandler:
    """Base class for all Vapi tool handlers."""
    
    # Define which roles can use which tools
    TOOL_PERMISSIONS = {
        # Public tools (customers)
        "create_service_request": ["customer", "technician", "dispatch", "manager", "executive", "admin"],
        "schedule_appointment": ["customer", "technician", "dispatch", "manager", "executive", "admin"],
        "reschedule_appointment": ["customer", "dispatch", "manager", "executive", "admin"],
        "cancel_appointment": ["customer", "dispatch", "manager", "executive", "admin"],
        "check_appointment_status": ["customer", "manager", "executive", "admin"],
        "check_availability": ["customer", "manager", "executive", "admin"],
        "request_quote": ["customer", "technician", "manager", "executive", "admin"],
        "check_lead_status": ["customer", "manager", "executive", "admin"],
        "request_membership_enrollment": ["customer", "manager", "executive", "admin"],
        "billing_inquiry": ["customer", "billing", "manager", "executive", "admin"],
        "invoice_request": ["customer", "billing", "manager", "executive", "admin"],
        "payment_terms_inquiry": ["customer", "billing", "manager", "executive", "admin"],
        "get_pricing": ["customer", "manager", "executive", "admin"],
        "get_maintenance_plans": ["customer", "manager", "executive", "admin"],
        "get_service_area_info": ["customer", "technician", "hr", "billing", "manager", "dispatch", "executive", "admin"],
        "check_business_hours": ["customer", "technician", "hr", "billing", "manager", "dispatch", "executive", "admin"],
        "create_complaint": ["customer", "manager", "executive", "admin"],
        
        # Technician-only tools
        "ivr_close_sale": ["technician", "manager", "executive", "admin"],
        
        # HR tools
        "payroll_inquiry": ["hr", "manager", "executive", "admin"],
        "onboarding_inquiry": ["hr", "manager", "executive", "admin"],
        "hiring_inquiry": ["hr", "manager", "executive", "admin"],
        
        # Operations tools
        "inventory_inquiry": ["manager", "dispatch", "executive", "admin"],
        "purchase_request": ["manager", "dispatch", "executive", "admin"],
    }
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
    
    def validate_required_params(
        self,
        parameters: dict[str, Any],
        required: list[str],
    ) -> tuple[bool, list[str]]:
        """
        Validate that required parameters are present.
        
        Returns:
            (is_valid, missing_fields)
        """
        missing = []
        for field in required:
            value = parameters.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        
        return len(missing) == 0, missing
    
    def normalize_phone(self, phone: str | None) -> str | None:
        """Normalize phone number format."""
        if not phone:
            return None
        
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # If it already starts with +, return as-is (supports international numbers)
        if cleaned.startswith('+'):
            return cleaned
        
        # Remove all non-digit characters for US number processing
        digits = ''.join(filter(str.isdigit, phone))
        
        # Add +1 if it's a 10-digit US number
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+{digits}"
        
        # If we have digits but no +, try to format as US number
        if len(digits) >= 10:
            return f"+{digits}"
        
        return None
    
    def normalize_email(self, email: str | None) -> str | None:
        """Normalize email format."""
        if not email:
            return None
        
        email = email.strip().lower()
        if '@' in email:
            return email
        
        return None
    
    def generate_idempotency_key(
        self,
        tool_call_id: str,
        call_id: str,
        parameters: dict[str, Any],
    ) -> str:
        """Generate idempotency key for tool call."""
        # Create deterministic key from tool call ID and key parameters
        # Extract key identifying parameters (normalized)
        key_params = {
            k: v for k, v in parameters.items()
            if k in ["phone", "email", "customer_name", "appointment_id", "lead_id"]
        }
        
        # Build key parts list
        key_parts = [
            self.tool_name,
            tool_call_id,
            call_id or "",
        ]
        
        # Add parameter values to key parts
        for k, v in sorted(key_params.items()):
            if v:
                key_parts.append(f"{k}:{v}")
        
        return generate_key_hash(VAPI_TOOL_SCOPE, key_parts)
    
    def log_audit(
        self,
        session: Session,
        request_id: str,
        call_id: str | None,
        tool_call_id: str | None,
        intent: str | None,
        brain: str | None,
        parameters: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        status: str = "processed",
        error_message: str | None = None,
    ) -> None:
        """Log tool call to audit log."""
        try:
            log_vapi_tool_call(
                session=session,
                request_id=request_id,
                call_id=call_id,
                tool_call_id=tool_call_id,
                intent=intent,
                brain=brain,
                parameters=parameters,
                result=result,
                status=status,
                error_message=error_message,
            )
        except Exception as e:
            self.logger.warning(f"Failed to log audit: {e}")
    
    def get_odoo_client(self):
        """Get Odoo client instance."""
        return create_odoo_client_from_settings()
    
    async def safe_odoo_operation(
        self,
        operation: callable,
        operation_name: str,
        data: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute an Odoo operation with graceful error handling.
        
        Args:
            operation: The async function to execute
            operation_name: Name of the operation for logging
            data: Data being processed (for local capture)
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            Result of the operation, or error handling result if Odoo fails
        """
        from src.utils.odoo_error_handler import OdooErrorHandler
        from src.db.session import get_session_factory
        
        session_factory = get_session_factory()
        session = session_factory()
        
        try:
            return await OdooErrorHandler.wrap_odoo_operation(
                operation=operation,
                operation_name=operation_name,
                data=data,
                session=session,
                *args,
                **kwargs,
            )
        finally:
            session.close()
    
    async def check_duplicate_call(
        self,
        phone: str | None,
        call_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Check for recent calls from the same phone number and existing appointments.
        
        Returns:
            Dict with duplicate_call info if found, None otherwise
            {
                "is_duplicate": bool,
                "recent_call_hours_ago": float | None,
                "existing_appointment": dict | None,
                "message": str | None
            }
        """
        if not phone:
            return None
        
        try:
            # Normalize phone
            normalized_phone = self.normalize_phone(phone)
            if not normalized_phone:
                return None
            
            # Check for recent calls (within 24 hours) from audit_log
            session_factory = get_session_factory()
            session = session_factory()
            try:
                from src.db.models import AuditLog
                from datetime import datetime, timedelta
                from sqlalchemy import and_, or_
                
                # Search for recent calls with this phone number
                # Look in command_json for phone field or use call_id pattern
                recent_cutoff = datetime.now() - timedelta(hours=24)
                
                # Try to find recent calls - check command_json if it exists
                phone_suffix = normalized_phone[-10:] if len(normalized_phone) >= 10 else normalized_phone
                phone_suffix_alt = phone[-10:] if len(phone) >= 10 else phone
                
                # Query for recent calls - check if command_json contains phone
                # Query for recent calls from same phone (within last 4 hours)
                # Note: AuditLog doesn't have call_id field, so we use request_id or filter via command_json
                filter_conditions = [
                    AuditLog.created_at >= recent_cutoff,
                    AuditLog.channel == "voice",
                ]
                # Exclude current call by checking request_id if call_id is provided
                if call_id:
                    filter_conditions.append(AuditLog.request_id != call_id)
                
                recent_calls_query = session.query(AuditLog).filter(and_(*filter_conditions))
                
                # Try to filter by phone in command_json (may not exist in all records)
                try:
                    recent_calls = recent_calls_query.filter(
                        or_(
                            AuditLog.command_json['entities']['phone'].astext.contains(phone_suffix),
                            AuditLog.command_json['entities']['phone'].astext.contains(phone_suffix_alt),
                        )
                    ).order_by(AuditLog.created_at.desc()).limit(1).all()
                except Exception:
                    # If JSON query fails, just check recent calls without phone filter
                    recent_calls = recent_calls_query.order_by(AuditLog.created_at.desc()).limit(5).all()
                    # Filter manually by checking command_json
                    recent_calls = [
                        call for call in recent_calls
                        if call.command_json and 
                        call.command_json.get('entities', {}).get('phone', '').endswith(phone_suffix)
                    ][:1]
                
                recent_call = None
                if recent_calls:
                    recent_call = recent_calls[0]
                    hours_ago = (datetime.now() - recent_call.created_at.replace(tzinfo=None)).total_seconds() / 3600
                else:
                    hours_ago = None
                
                # Check for existing appointments
                existing_appointment = None
                try:
                    from src.integrations.odoo_appointments import create_appointment_service
                    appointment_service = await create_appointment_service()
                    
                    # Find appointments for this phone number
                    appointments = await appointment_service.find_appointment_by_contact(
                        phone=normalized_phone,
                        date_from=datetime.now() - timedelta(days=30),  # Last 30 days
                    )
                    
                    # Filter to future appointments or very recent past appointments (within 24 hours)
                    now = datetime.now()
                    for apt in appointments:
                        if apt.get("start"):
                            try:
                                apt_start = datetime.fromisoformat(apt["start"].replace("Z", "+00:00"))
                                apt_start_local = apt_start.replace(tzinfo=None)
                                # Future appointment or very recent (within 24 hours)
                                if apt_start_local > now or (now - apt_start_local).total_seconds() < 86400:
                                    existing_appointment = apt
                                    break
                            except Exception:
                                continue
                except Exception as apt_err:
                    self.logger.warning(f"Failed to check existing appointments: {apt_err}")
                
                # If we found a recent call or existing appointment, return duplicate info
                if recent_call or existing_appointment:
                    message = None
                    if existing_appointment:
                        apt_start = existing_appointment.get("start")
                        if apt_start:
                            try:
                                apt_dt = datetime.fromisoformat(apt_start.replace("Z", "+00:00"))
                                apt_str = apt_dt.strftime("%A, %B %d at %I:%M %p")
                                message = f"Welcome back! I see you have an appointment scheduled for {apt_str}. Would you like to modify your appointment?"
                            except Exception:
                                message = "Welcome back! I see you just called. Would you like to modify your appointment?"
                        else:
                            message = "Welcome back! I see you just called. Would you like to modify your appointment?"
                    elif recent_call and hours_ago and hours_ago < 1:
                        message = "Welcome back! I see you just called. Would you like to modify your appointment?"
                    
                    return {
                        "is_duplicate": True,
                        "recent_call_hours_ago": hours_ago,
                        "existing_appointment": existing_appointment,
                        "message": message,
                    }
                
            finally:
                session.close()
            
        except Exception as e:
            self.logger.warning(f"Error checking duplicate call: {e}")
        
        return None
    
    def detect_profanity_abuse(
        self,
        conversation_context: str | None = None,
        user_text: str | None = None,
    ) -> bool:
        """
        Detect if user is using profanity or abusive language.
        
        Returns:
            True if profanity/abuse detected, False otherwise
        """
        if not conversation_context and not user_text:
            return False
        
        text = (conversation_context or "") + " " + (user_text or "")
        text_lower = text.lower()
        
        # Common profanity/abuse indicators (basic list - can be enhanced)
        profanity_indicators = [
            # Profanity (common words)
            "fuck", "shit", "damn", "hell", "asshole", "bastard", "bitch",
            # Abusive language
            "you're stupid", "you're dumb", "idiot", "moron", "stupid system",
            "this is bullshit", "this sucks", "terrible service",
            # Threatening language
            "i'll sue", "i'll report you", "i'll complain", "lawyer",
            # Aggressive language
            "i'm furious", "i'm extremely angry", "worst service ever",
        ]
        
        for indicator in profanity_indicators:
            if indicator in text_lower:
                return True
        
        return False
    
    def detect_wrong_number(
        self,
        conversation_context: str | None = None,
        user_text: str | None = None,
    ) -> bool:
        """
        Detect if user is indicating they dialed the wrong number.
        
        Returns:
            True if wrong number detected, False otherwise
        """
        if not conversation_context and not user_text:
            return False
        
        text = (conversation_context or "") + " " + (user_text or "")
        text_lower = text.lower()
        
        wrong_number_phrases = [
            "wrong number",
            "sorry wrong number",
            "misdial",
            "wrong company",
            "didn't mean to call",
            "accidental call",
            "not who i wanted",
            "wrong business",
        ]
        
        for phrase in wrong_number_phrases:
            if phrase in text_lower:
                return True
        
        return False
    
    def handle_unclear_speech(
        self,
        confidence: float | None = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> ToolResponse | None:
        """
        Handle unclear/garbled speech by asking for clarification.
        
        Args:
            confidence: Confidence score from speech recognition (0.0-1.0)
            retry_count: Number of times we've already asked for clarification
            max_retries: Maximum number of retries before offering callback
        
        Returns:
            ToolResponse with clarification request, or None if should continue
        """
        if confidence is not None and confidence < 0.5:
            # Low confidence - ask for clarification
            if retry_count < max_retries:
                message = "I'm sorry, I didn't catch that. Could you repeat that, please?"
                return self.format_needs_human_response(
                    message,
                    data={
                        "unclear_speech": True,
                        "confidence": confidence,
                        "retry_count": retry_count + 1,
                    },
                )
            else:
                # Too many retries - offer callback
                message = (
                    "I'm having trouble understanding. Would you prefer to receive a callback "
                    "from one of our representatives, or would you like to try again?"
                )
                return self.format_needs_human_response(
                    message,
                    data={
                        "unclear_speech": True,
                        "confidence": confidence,
                        "retry_count": retry_count,
                        "callback_offered": True,
                    },
                )
        
        return None
    
    def get_conversation_context(
        self,
        call_id: str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """
        Get collected information from previous tool calls in this conversation.
        
        Returns:
            Dict with collected fields (e.g., {"customer_name": "John", "phone": "+1234567890"})
        """
        if not call_id:
            return {}
        
        try:
            if not session:
                session_factory = get_session_factory()
                session = session_factory()
                should_close = True
            else:
                should_close = False
            
            try:
                from src.db.models import AuditLog
                from sqlalchemy import and_
                
                # Get all tool calls for this call_id
                # Look for audit logs with this call_id in request_id
                # We'll search for recent calls within the last hour that might be part of the same conversation
                from datetime import timedelta
                from sqlalchemy import or_, func
                
                recent_cutoff = datetime.now() - timedelta(hours=1)
                recent_calls = session.query(AuditLog).filter(
                    and_(
                        AuditLog.channel == "voice",
                        AuditLog.created_at >= recent_cutoff,
                        or_(
                            AuditLog.request_id.contains(call_id) if call_id else False,
                            func.cast(AuditLog.command_json, func.Text).contains(call_id) if call_id else False,
                        ),
                    )
                ).order_by(AuditLog.created_at.desc()).limit(20).all()
                
                # Extract collected information from command_json
                collected = {}
                for log_entry in recent_calls:
                    if log_entry.command_json:
                        # Check if this log entry is from the same call
                        # Look for call_id in command_json metadata or request_id
                        cmd_json = log_entry.command_json
                        log_call_id = (
                            cmd_json.get("metadata", {}).get("call_id") or
                            cmd_json.get("call_id") or
                            (log_entry.request_id if call_id and call_id in (log_entry.request_id or "") else None)
                        )
                        
                        # Only include if it's from the same call
                        if log_call_id == call_id or (call_id and call_id in (log_entry.request_id or "")):
                            entities = cmd_json.get("entities", {})
                            if isinstance(entities, dict):
                                # Extract entity fields
                                for key, value in entities.items():
                                    if value and key not in collected:
                                        collected[key] = value
                
                return collected
            finally:
                if should_close:
                    session.close()
        except Exception as e:
            self.logger.warning(f"Error getting conversation context: {e}")
            return {}
    
    def check_already_collected(
        self,
        field_name: str,
        call_id: str | None = None,
        session: Session | None = None,
    ) -> bool:
        """
        Check if a field has already been collected in this conversation.
        
        Returns:
            True if field already collected, False otherwise
        """
        if not call_id:
            return False
        
        context = self.get_conversation_context(call_id, session)
        
        # Map field names to entity keys
        field_mapping = {
            "customer_name": "full_name",
            "name": "full_name",
            "phone": "phone",
            "email": "email",
            "address": "address",
            "zip_code": "zip_code",
            "service_type": "service_type",
            "problem_description": "problem_description",
        }
        
        entity_key = field_mapping.get(field_name, field_name)
        return entity_key in context and context[entity_key]
    
    def detect_multiple_intents(
        self,
        conversation_context: str | None = None,
        user_text: str | None = None,
    ) -> list[str] | None:
        """
        Detect if user has multiple requests in their message.
        
        Returns:
            List of detected intent keywords, or None if single intent
        """
        text = (conversation_context or "") + " " + (user_text or "")
        if not text.strip():
            return None
        
        text_lower = text.lower()
        
        # Intent keywords
        intent_keywords = {
            "service": ["service", "repair", "fix", "broken", "not working", "diagnostic"],
            "appointment": ["appointment", "schedule", "book", "reschedule", "cancel"],
            "quote": ["quote", "price", "cost", "estimate", "how much"],
            "billing": ["bill", "invoice", "payment", "pay", "balance", "due"],
            "complaint": ["complaint", "unhappy", "upset", "problem", "issue", "wrong"],
            "membership": ["membership", "maintenance plan", "tune-up"],
        }
        
        # Detect multiple intents
        detected = []
        for intent, keywords in intent_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected.append(intent)
        
        # Return if multiple intents detected
        return detected if len(detected) > 1 else None
    
    def format_multi_request_response(
        self,
        detected_intents: list[str],
    ) -> ToolResponse:
        """
        Format response asking user to prioritize multiple requests.
        
        Returns:
            ToolResponse asking for prioritization
        """
        intent_descriptions = {
            "service": "service request",
            "appointment": "appointment",
            "quote": "quote",
            "billing": "billing inquiry",
            "complaint": "complaint",
            "membership": "membership",
        }
        
        descriptions = [intent_descriptions.get(i, i) for i in detected_intents]
        
        if len(descriptions) == 2:
            speak = f"I understand you need help with {descriptions[0]} and {descriptions[1]}. Let's handle these one at a time. Which is most urgent?"
        else:
            speak = f"I understand you have multiple requests: {', '.join(descriptions[:-1])}, and {descriptions[-1]}. Let's handle these one at a time. Which is most urgent?"
        
        return ToolResponse(
            speak=speak,
            action="needs_human",
            data={
                "multiple_intents_detected": True,
                "detected_intents": detected_intents,
                "requires_prioritization": True,
            },
        )
    
    def format_error_response(
        self,
        error: Exception,
        user_message: str = "I'm sorry, I encountered an error processing your request.",
    ) -> ToolResponse:
        """Format error response."""
        self.logger.exception(f"Error in {self.tool_name}: {error}")
        return ToolResponse(
            speak=user_message,
            action="error",
            data={
                "error": str(error),
                "tool": self.tool_name,
            },
        )
    
    def format_needs_human_response(
        self,
        message: str,
        missing_fields: list[str] | None = None,
        data: dict[str, Any] | None = None,
        intent_acknowledged: bool = False,
    ) -> ToolResponse:
        """
        Format response indicating human intervention needed.
        
        Args:
            message: The message to speak
            missing_fields: List of missing field names
            data: Additional response data
            intent_acknowledged: If True, intent has already been acknowledged in a previous response.
                                 If False, this response should acknowledge intent first.
        """
        response_data = data or {}
        if missing_fields:
            response_data["missing_fields"] = missing_fields
            # Mark that we need to ask for fields one at a time
            response_data["_intent_first_rule"] = True
            # If intent not yet acknowledged, mark it so the AI knows to acknowledge first
            if not intent_acknowledged:
                response_data["_acknowledge_intent_first"] = True
        
        return ToolResponse(
            speak=message,
            action="needs_human",
            data=response_data,
        )
    
    def format_success_response(
        self,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> ToolResponse:
        """Format successful response."""
        return ToolResponse(
            speak=message,
            action="completed",
            data=data or {},
        )
    
    def check_access(
        self,
        tool_name: str,
        caller_role: str,
        caller_is_active: bool = True,
    ) -> tuple[bool, str]:
        """
        Check if caller has permission to use this tool.
        
        Args:
            tool_name: Name of the tool to check
            caller_role: Caller's role (from CallerRole enum value)
            caller_is_active: Whether caller's account is active
            
        Returns:
            (allowed: bool, error_message: str)
        """
        # Admin has all permissions
        if caller_role == "admin":
            return True, ""
        
        # Get required roles for this tool
        required_roles = self.TOOL_PERMISSIONS.get(tool_name, [])
        
        # If tool not in permissions list, allow public access (backward compatible)
        if not required_roles:
            return True, ""
        
        # Check if caller's role is allowed
        if caller_role not in required_roles:
            role_names = ", ".join(r.title() for r in required_roles)
            return False, f"This feature is only available to {role_names}."
        
        # Check if caller is active
        if not caller_is_active:
            return False, "Your account is inactive. Please contact your manager."
        
        return True, ""


async def handle_tool_call_with_base(
    tool_name: str,
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> dict[str, Any]:
    """
    Generic tool call handler wrapper with base functionality.
    
    This handles:
    - Idempotency checking
    - Audit logging
    - Error handling
    - Response formatting
    
    Args:
        tool_name: Name of the tool
        tool_call_id: Vapi tool call ID
        parameters: Tool parameters
        call_id: Vapi call ID
        conversation_context: Optional conversation context
        
    Returns:
        Vapi-compatible response dict
    """
    request_id = generate_request_id()
    base_handler = BaseToolHandler(tool_name)
    
    # Generate idempotency key
    idempotency_key = base_handler.generate_idempotency_key(
        tool_call_id=tool_call_id,
        call_id=call_id or "",
        parameters=parameters,
    )
    
    # Get database session
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        # Check idempotency
        checker = IdempotencyChecker(session)
        existing = checker.get_existing(VAPI_TOOL_SCOPE, idempotency_key)
        
        if existing and existing.get("_idempotency_status") != "in_progress":
            base_handler.logger.info(
                f"Idempotency hit for {tool_call_id}, returning cached result"
            )
            cached_result = existing.get("response_json", {})
            return cached_result
        
        # Mark as in progress
        checker.start(VAPI_TOOL_SCOPE, idempotency_key)
        
        # Get collected context from previous tool calls
        collected_context = {}
        if call_id:
            collected_context = base_handler.get_conversation_context(call_id, session)
            # Add collected context to parameters so tools can use it
            if collected_context:
                parameters["_collected_context"] = collected_context
        
        # Get tool handler
        from src.vapi.tools import get_tool_handler
        handler = get_tool_handler(tool_name)
        
        if not handler:
            response = base_handler.format_error_response(
                ValueError(f"Tool '{tool_name}' not found"),
                f"I'm sorry, I don't recognize the '{tool_name}' tool.",
            )
            result = response.to_dict()
        else:
            # Call tool handler with timeout (25 seconds to ensure we respond before Vapi's 30s timeout)
            try:
                response = await asyncio.wait_for(
                    handler(
                        tool_call_id=tool_call_id,
                        parameters=parameters,
                        call_id=call_id,
                        conversation_context=conversation_context,
                    ),
                    timeout=25.0,  # 25 second timeout (Vapi timeout is 30s)
                )
                
                # Ensure response is ToolResponse or dict
                if isinstance(response, ToolResponse):
                    result = response.to_dict()
                elif isinstance(response, dict):
                    result = response
                else:
                    result = base_handler.format_success_response(
                        str(response)
                    ).to_dict()
            
            except asyncio.TimeoutError:
                base_handler.logger.error(f"Tool {tool_name} timed out after 25 seconds")
                result = base_handler.format_error_response(
                    TimeoutError("Tool execution timed out"),
                    "I'm sorry, that request is taking longer than expected. Please try again or contact us directly.",
                ).to_dict()
            except Exception as e:
                result = base_handler.format_error_response(e).to_dict()
        
        # Log audit
        base_handler.log_audit(
            session=session,
            request_id=request_id,
            call_id=call_id,
            tool_call_id=tool_call_id,
            intent=None,  # Will be set by individual tools
            brain=None,   # Will be set by individual tools
            parameters=parameters,
            result=result,
            status="processed" if result.get("action") != "error" else "error",
            error_message=result.get("data", {}).get("error") if result.get("action") == "error" else None,
        )
        
        # Complete idempotency
        checker.complete(VAPI_TOOL_SCOPE, idempotency_key, result)
        
        return result
    
    except Exception as e:
        base_handler.logger.exception(f"Error in tool call wrapper: {e}")
        response = base_handler.format_error_response(e)
        result = response.to_dict()
        
        # Log error
        try:
            base_handler.log_audit(
                session=session,
                request_id=request_id,
                call_id=call_id,
                tool_call_id=tool_call_id,
                intent=None,
                brain=None,
                parameters=parameters,
                result=result,
                status="error",
                error_message=str(e),
            )
        except:
            pass
        
        return result
    
    finally:
        session.close()
