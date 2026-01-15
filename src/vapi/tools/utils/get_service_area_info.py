"""
HAES HVAC - Get Service Area Info Tool

Utility tool for service area coverage information.
"""

import logging
from typing import Any

from src.vapi.tools.base import BaseToolHandler, ToolResponse
from src.vapi.tools.utils.service_area import SERVICE_RADIUS_MILES

logger = logging.getLogger(__name__)


async def handle_get_service_area_info(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle get_service_area_info tool call.
    
    Parameters:
        - zip_code (optional): ZIP code to check
        - address (optional): Address to check
    """
    handler = BaseToolHandler("get_service_area_info")
    
    try:
        message = f"We service within {SERVICE_RADIUS_MILES} miles of downtown Dallas, Texas."
        
        # If address/ZIP provided, check if within area
        address = parameters.get("address")
        zip_code = parameters.get("zip_code")
        
        if address or zip_code:
            from src.vapi.tools.utils.service_area import is_within_service_area
            is_within, area_error = is_within_service_area(address, zip_code)
            
            if is_within:
                message += " Your location is within our service area."
            elif area_error:
                message += f" {area_error}"
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "service_radius_miles": SERVICE_RADIUS_MILES,
                "service_center": "Downtown Dallas, Texas",
                "address_provided": bool(address),
                "zip_code_provided": bool(zip_code),
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
