"""
HAES HVAC - Get Pricing Tool

Direct Vapi tool for getting service pricing information.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.brains.core.handlers import calculate_service_pricing
from src.brains.core.schema import PricingTier

logger = logging.getLogger(__name__)


async def handle_get_pricing(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle get_pricing tool call.
    
    Parameters:
        - property_type (required): "residential", "commercial", "property_management"
        - service_type (optional): Service type (e.g., "diagnostic", "repair")
        - urgency (optional): "emergency", "high", "medium", "low"
        - is_weekend (optional): Boolean, true if weekend service
        - is_after_hours (optional): Boolean, true if after-hours service
        - customer_type (optional): Override property_type with specific customer type
            Values: "retail", "commercial", "property_management", "com_lessen", "com_hotels"
    """
    handler = BaseToolHandler("get_pricing")
    
    # Validate required parameters
    required = ["property_type"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        return handler.format_needs_human_response(
            "I can help you with pricing information.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    try:
        # Map property_type/customer_type to PricingTier
        property_type = parameters.get("property_type", "").lower()
        customer_type_str = (parameters.get("customer_type") or property_type).lower()
        
        # Map to PricingTier enum
        tier_map = {
            "residential": PricingTier.RETAIL,
            "retail": PricingTier.RETAIL,
            "commercial": PricingTier.COM,
            "com": PricingTier.COM,
            "property_management": PricingTier.DEFAULT_PM,
            "property_management": PricingTier.DEFAULT_PM,
            "default_pm": PricingTier.DEFAULT_PM,
            "com_lessen": PricingTier.COM_LESSEN,
            "lessen": PricingTier.COM_LESSEN,
            "com_hotels": PricingTier.COM_HOTELS,
            "hotels": PricingTier.COM_HOTELS,
            "hotels/multi": PricingTier.COM_HOTELS,
        }
        
        tier = tier_map.get(customer_type_str, PricingTier.RETAIL)
        
        # Determine if emergency/urgent
        urgency = parameters.get("urgency", "medium").lower()
        is_emergency = urgency == "emergency"
        is_urgent = urgency == "high"
        
        # Get weekend/after-hours flags
        is_weekend = parameters.get("is_weekend", False)
        is_after_hours = parameters.get("is_after_hours", False)
        
        # Calculate pricing
        pricing_result = calculate_service_pricing(
            tier=tier,
            is_emergency=is_emergency,
            is_weekend=is_weekend,
            is_after_hours=is_after_hours,
        )
        
        # Handle both dict and PricingResult object returns (for test compatibility)
        if isinstance(pricing_result, dict):
            from src.brains.core.schema import PricingResult
            pricing = PricingResult(
                tier=tier,
                diagnostic_fee=pricing_result.get("diagnostic_fee", 0.0),
                trip_charge=pricing_result.get("trip_charge", 0.0),
                emergency_premium=pricing_result.get("emergency_premium", 0.0),
                after_hours_premium=pricing_result.get("after_hours_premium", 0.0),
                weekend_premium=pricing_result.get("weekend_premium", 0.0),
                total_base_fee=pricing_result.get("total_base_fee", pricing_result.get("diagnostic_fee", 0.0) + pricing_result.get("trip_charge", 0.0)),
                notes=pricing_result.get("notes", []),
            )
        else:
            pricing = pricing_result
        
        # Build comprehensive response message
        service_type = parameters.get("service_type", "service")
        tier_name = tier.value.replace("_", " ").title()
        
        message_parts = [f"For {tier_name} customers, {service_type} pricing includes:"]
        message_parts.append(f"Diagnostic fee: ${pricing.diagnostic_fee:.2f}")
        
        if pricing.trip_charge and pricing.trip_charge > 0:
            message_parts.append(f"Trip charge: ${pricing.trip_charge:.2f}")
        
        if pricing.emergency_premium and pricing.emergency_premium > 0:
            message_parts.append(f"Emergency premium: ${pricing.emergency_premium:.2f}")
        
        if pricing.after_hours_premium and pricing.after_hours_premium > 0:
            message_parts.append(f"After-hours premium: ${pricing.after_hours_premium:.2f}")
        
        if pricing.weekend_premium and pricing.weekend_premium > 0:
            message_parts.append(f"Weekend premium: ${pricing.weekend_premium:.2f}")
        
        total = pricing.total_base_fee
        message_parts.append(f"Total estimate: ${total:.2f}")
        
        message = " ".join(message_parts)
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "pricing_tier": tier.value,
                "tier_display_name": tier_name,
                "service_type": service_type,
                "diagnostic_fee": pricing.diagnostic_fee,
                "trip_charge": pricing.trip_charge,
                "emergency_premium": pricing.emergency_premium,
                "after_hours_premium": pricing.after_hours_premium,
                "weekend_premium": pricing.weekend_premium,
                "total_estimate": total,
                "is_emergency": is_emergency,
                "is_weekend": is_weekend,
                "is_after_hours": is_after_hours,
                "notes": pricing.notes,
            },
        )
    
    except Exception as e:
        logger.exception(f"Error in get_pricing tool: {e}")
        return handler.format_error_response(e)
