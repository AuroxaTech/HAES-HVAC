"""
HAES HVAC - Get Maintenance Plans Tool

Utility tool for maintenance plan information and pricing.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse

logger = logging.getLogger(__name__)


async def handle_get_maintenance_plans(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle get_maintenance_plans tool call.
    
    Parameters:
        - property_type (optional): "residential", "commercial"
    """
    handler = BaseToolHandler("get_maintenance_plans")
    
    try:
        property_type = parameters.get("property_type", "residential").lower()
        
        if property_type == "commercial":
            message = (
                "We offer a Commercial Maintenance Plan for $379 per year. "
                "This includes VIP contract benefits, priority scheduling, and regular tune-ups. "
                "Would you like to enroll?"
            )
            plan_name = "Commercial Maintenance Plan"
            price = 379
        else:
            message = (
                "We offer a Basic Maintenance Plan for $279 per year. "
                "This includes VIP contract benefits, priority scheduling, and regular tune-ups. "
                "Would you like to enroll?"
            )
            plan_name = "Basic Maintenance Plan"
            price = 279
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "property_type": property_type,
                "plan_name": plan_name,
                "annual_price": price,
                "benefits": [
                    "VIP contract benefits",
                    "Priority scheduling",
                    "Regular tune-ups",
                ],
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
