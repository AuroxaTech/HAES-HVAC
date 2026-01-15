"""
HAES HVAC - Billing Inquiry Tool

Direct Vapi tool for billing inquiries.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.hael.schema import (
    Channel,
    Entity,
    HaelCommand,
    Intent,
    Brain,
)
from src.brains.core import handle_core_command
from src.brains.core.schema import CoreStatus
from src.brains.core.payment_terms import get_payment_terms, format_payment_terms_text
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)


async def handle_billing_inquiry(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle billing_inquiry tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (optional): Phone number
        - email (optional): Email address
        - invoice_number (optional): Specific invoice number
        - property_type (optional): "residential", "commercial", "property_management" (for payment terms)
    """
    handler = BaseToolHandler("billing_inquiry")
    
    # Validate required parameters - need phone OR email
    customer_name = parameters.get("customer_name")
    phone = parameters.get("phone")
    email = parameters.get("email")
    
    missing = []
    if not customer_name:
        missing.append("customer_name")
    if not phone and not email:
        missing.append("phone or email")
    
    if missing:
        return handler.format_needs_human_response(
            "I can help you with your billing information.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Build Entity
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=handler.normalize_phone(parameters.get("phone")),
        email=handler.normalize_email(parameters.get("email")),
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or "billing inquiry",
        intent=Intent.BILLING_INQUIRY,
        brain=Brain.CORE,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
            "invoice_number": parameters.get("invoice_number"),
        },
    )
    
    # Call CORE brain handler
    try:
        result = handle_core_command(command)
        
        if result.requires_human or result.status == CoreStatus.NEEDS_HUMAN:
            return handler.format_needs_human_response(
                result.message,
                missing_fields=getattr(result, "missing_fields", None),
                data=result.data or {},
            )
        
        if result.status == CoreStatus.ERROR:
            return handler.format_error_response(
                Exception(result.message),
                "I encountered an error checking your billing information. Please try again or contact us directly.",
            )
        
        # Format success response
        response_data = result.data or {}
        response_data["request_id"] = request_id
        
        # Add payment terms and late fee information based on customer type
        property_type = parameters.get("property_type", "").lower()
        
        # Map property_type to payment terms segment
        segment_map = {
            "residential": "residential",
            "commercial": "commercial",
            "property_management": "property_management",
        }
        segment = segment_map.get(property_type)
        
        # Get payment terms
        payment_terms = get_payment_terms(segment)
        payment_terms_text = format_payment_terms_text(segment)
        
        # Add payment terms to response
        response_data["payment_terms"] = {
            "segment": payment_terms.segment,
            "due_days": payment_terms.due_days,
            "due_text": "Due upon receipt" if payment_terms.due_days == 0 else f"Net {payment_terms.due_days} days",
            "late_fee_percent": payment_terms.late_fee_percent,
            "late_fee_text": f"{payment_terms.late_fee_percent}% per month after due date",
            "accepted_methods": payment_terms.accepted_methods,
            "formatted_text": payment_terms_text,
        }
        
        # Enhance message with payment terms if available
        enhanced_message = result.message
        if segment:
            if payment_terms.due_days == 0:
                due_info = "Payment is due upon receipt"
            elif payment_terms.due_days == 15:
                due_info = "Payment terms are Net 15 days"
            elif payment_terms.due_days == 30:
                due_info = "Payment terms are Net 30 days"
            else:
                due_info = f"Payment terms are Net {payment_terms.due_days} days"
            
            enhanced_message += f" {due_info}. "
            enhanced_message += f"If payment is overdue, a {payment_terms.late_fee_percent}% late fee applies per month. "
            enhanced_message += f"Accepted payment methods include: {', '.join(payment_terms.accepted_methods)}."
        
        return handler.format_success_response(
            enhanced_message,
            data=response_data,
        )
    
    except Exception as e:
        return handler.format_error_response(e)
