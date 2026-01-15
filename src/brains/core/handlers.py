"""
HAES HVAC - CORE Brain Handlers

Main entry point for CORE brain command handling.
Handles pricing, billing, approvals, and compliance.
"""

import logging
from datetime import datetime

from src.hael.schema import HaelCommand, Intent
from src.brains.core.schema import (
    CoreResult,
    CoreStatus,
    InvoicePolicy,
    PricingResult,
    PricingTier,
)
from src.brains.core.pricing_catalog import get_tier_pricing, get_default_tier, PRICING_CATALOG
from src.brains.core.approval_rules import get_approval_decision, ApprovalType
from src.brains.core.payment_terms import get_payment_terms, format_payment_terms_text
from src.brains.core.compliance import get_required_disclosures

logger = logging.getLogger(__name__)

# Supported CORE intents
CORE_INTENTS = {
    Intent.BILLING_INQUIRY,
    Intent.PAYMENT_TERMS_INQUIRY,
    Intent.INVOICE_REQUEST,
    Intent.INVENTORY_INQUIRY,
    Intent.PURCHASE_REQUEST,
}


def handle_core_command(command: HaelCommand) -> CoreResult:
    """
    Handle a CORE brain command.
    
    This is the main entry point for all CORE operations.
    
    Args:
        command: HAEL command to process
        
    Returns:
        CoreResult with operation outcome
    """
    logger.info(f"CORE brain handling command: {command.intent.value}")
    
    # Check if intent is supported
    if command.intent not in CORE_INTENTS:
        return CoreResult(
            status=CoreStatus.UNSUPPORTED_INTENT,
            message=f"Intent '{command.intent.value}' is not handled by CORE brain",
            requires_human=False,
        )
    
    # Check if HAEL says requires human
    if command.requires_human:
        return CoreResult(
            status=CoreStatus.NEEDS_HUMAN,
            message="HAEL indicated human intervention required",
            requires_human=True,
            missing_fields=command.missing_fields,
        )
    
    # Route to specific handler
    try:
        if command.intent == Intent.BILLING_INQUIRY:
            return _handle_billing_inquiry(command)
        elif command.intent == Intent.PAYMENT_TERMS_INQUIRY:
            return _handle_payment_terms_inquiry(command)
        elif command.intent == Intent.INVOICE_REQUEST:
            return _handle_invoice_request(command)
        elif command.intent == Intent.INVENTORY_INQUIRY:
            return _handle_inventory_inquiry(command)
        elif command.intent == Intent.PURCHASE_REQUEST:
            return _handle_purchase_request(command)
        else:
            return CoreResult(
                status=CoreStatus.ERROR,
                message=f"Unhandled intent: {command.intent.value}",
                requires_human=True,
            )
    except Exception as e:
        logger.exception(f"Error handling CORE command: {e}")
        return CoreResult(
            status=CoreStatus.ERROR,
            message=f"Internal error: {str(e)}",
            requires_human=True,
        )


def _handle_billing_inquiry(command: HaelCommand) -> CoreResult:
    """Handle billing inquiry."""
    entities = command.entities
    
    # Need identity to lookup billing info
    if not (entities.phone or entities.email):
        return CoreResult(
            status=CoreStatus.NEEDS_HUMAN,
            message="Need contact information to look up billing details",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    # Get compliance disclosures to include
    compliance = get_required_disclosures()
    
    return CoreResult(
        status=CoreStatus.SUCCESS,
        message="I can help you with billing information. Let me look up your account.",
        requires_human=False,
        compliance=compliance,
        data={
            "contact_phone": entities.phone,
            "contact_email": entities.email,
            "action": "lookup_billing",
        },
    )


def _handle_payment_terms_inquiry(command: HaelCommand) -> CoreResult:
    """Handle payment terms inquiry."""
    entities = command.entities
    
    # Determine customer segment (if known)
    segment = None
    if entities.property_type == "commercial":
        segment = "commercial"
    elif entities.property_type == "residential":
        segment = "residential"
    elif entities.property_type == "property_management":
        segment = "property_management"
    
    # Get payment terms
    terms = get_payment_terms(segment)
    terms_text = format_payment_terms_text(segment)
    
    return CoreResult(
        status=CoreStatus.SUCCESS,
        message=terms_text,
        requires_human=False,
        payment_terms=terms,
        data={
            "segment": segment or "unknown",
        },
    )


def _handle_invoice_request(command: HaelCommand) -> CoreResult:
    """Handle invoice request."""
    entities = command.entities
    
    # Need identity to send invoice
    if not (entities.phone or entities.email):
        return CoreResult(
            status=CoreStatus.NEEDS_HUMAN,
            message="Need contact information to send invoice",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    # Build appropriate message based on available contact info
    if entities.email:
        message = f"I'll send a copy of your invoice to {entities.email}."
    elif entities.phone:
        message = "I'll look up your invoice and send it to the email address we have on file. If you'd like it sent to a different email, please provide it."
    else:
        message = "I'll send a copy of your invoice to your email on file."
    
    return CoreResult(
        status=CoreStatus.SUCCESS,
        message=message,
        requires_human=False,
        data={
            "contact_email": entities.email,
            "contact_phone": entities.phone,
            "action": "send_invoice",
        },
    )


def _handle_inventory_inquiry(command: HaelCommand) -> CoreResult:
    """Handle inventory inquiry."""
    # General inquiry - doesn't require identity
    return CoreResult(
        status=CoreStatus.SUCCESS,
        message="I can check on parts availability. What specific part or equipment are you looking for?",
        requires_human=False,
        data={
            "action": "inventory_lookup",
        },
    )


def _handle_purchase_request(command: HaelCommand) -> CoreResult:
    """Handle purchase request."""
    entities = command.entities
    
    # Need identity for PO creation
    if not (entities.phone or entities.email):
        return CoreResult(
            status=CoreStatus.NEEDS_HUMAN,
            message="Need contact information to process purchase request",
            requires_human=True,
            missing_fields=["phone or email"],
        )
    
    return CoreResult(
        status=CoreStatus.SUCCESS,
        message="I can help with your purchase request. A representative will follow up with pricing and availability.",
        requires_human=False,
        data={
            "contact_phone": entities.phone,
            "contact_email": entities.email,
            "action": "purchase_request",
        },
    )


# =============================================================================
# Pricing Engine Functions
# =============================================================================


def calculate_service_pricing(
    tier: PricingTier | None = None,
    is_emergency: bool = False,
    is_after_hours: bool = False,
    is_weekend: bool = False,
) -> PricingResult:
    """
    Calculate service call pricing.
    
    Args:
        tier: Customer pricing tier (defaults to Retail)
        is_emergency: Emergency service flag
        is_after_hours: After-hours service flag
        is_weekend: Weekend service flag
        
    Returns:
        PricingResult with fee breakdown
    """
    tier = tier or get_default_tier()
    tier_pricing = get_tier_pricing(tier)
    
    # Calculate fees
    diagnostic = tier_pricing.diagnostic_fee
    trip = tier_pricing.trip_charge
    emergency = tier_pricing.emergency_premium if is_emergency else 0.0
    after_hours = tier_pricing.after_hours_premium if is_after_hours else 0.0
    weekend = tier_pricing.weekend_premium if is_weekend else 0.0
    
    total = diagnostic + trip + emergency + after_hours + weekend
    
    notes = []
    if is_emergency:
        notes.append("Emergency service premium applied")
    if is_after_hours:
        notes.append("After-hours premium applied")
    if is_weekend:
        notes.append("Weekend premium applied")
    
    return PricingResult(
        tier=tier,
        diagnostic_fee=diagnostic,
        trip_charge=trip,
        emergency_premium=emergency,
        after_hours_premium=after_hours,
        weekend_premium=weekend,
        total_base_fee=total,
        notes=notes,
    )


def should_generate_invoice(
    work_order_status: str,
    payment_status: str,
) -> InvoicePolicy:
    """
    Determine if an invoice should be generated.
    
    From RDD: "invoice trigger: when tech is complete job and workorder is paid"
    
    Args:
        work_order_status: Current work order status
        payment_status: Current payment status
        
    Returns:
        InvoicePolicy with decision
    """
    # Normalize inputs
    wo_status = work_order_status.lower()
    pay_status = payment_status.lower()
    
    # Check if work is complete
    if wo_status not in ["completed", "complete", "done"]:
        return InvoicePolicy(
            should_generate=False,
            requires_human=False,
            reason="Work order not yet completed",
            trigger_condition="Work order must be marked complete",
        )
    
    # Check payment status
    if pay_status in ["paid", "collected", "received"]:
        return InvoicePolicy(
            should_generate=True,
            requires_human=False,
            reason="Work completed and payment received",
            trigger_condition="Auto-generate invoice",
        )
    
    # Work complete but payment pending
    return InvoicePolicy(
        should_generate=True,
        requires_human=False,
        reason="Work completed, invoice due",
        trigger_condition="Send invoice for collection",
    )

