"""
HAES HVAC - Check Business Hours Tool

Utility tool for checking current business hours status.
"""

import logging
from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo

from src.vapi.tools.base import BaseToolHandler, ToolResponse

logger = logging.getLogger(__name__)

# Business hours configuration
BUSINESS_TZ = ZoneInfo("America/Chicago")
BUSINESS_HOURS_START = 8  # 8 AM
BUSINESS_HOURS_END = 17   # 5 PM (17:00)


def is_business_hours() -> bool:
    """Check if current time is within business hours."""
    now = datetime.now(BUSINESS_TZ)
    
    # Check if weekday (Monday=0, Sunday=6)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    # Check if within hours
    hour = now.hour
    return BUSINESS_HOURS_START <= hour < BUSINESS_HOURS_END


async def handle_check_business_hours(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle check_business_hours tool call.
    
    Parameters:
        None
    """
    handler = BaseToolHandler("check_business_hours")
    
    try:
        now = datetime.now(BUSINESS_TZ)
        is_open = is_business_hours()
        
        # Calculate next business day
        next_day = now
        while next_day.weekday() >= 5 or next_day.hour >= BUSINESS_HOURS_END:
            next_day = next_day.replace(hour=BUSINESS_HOURS_START, minute=0, second=0, microsecond=0)
            if next_day.weekday() >= 5:
                # Move to Monday
                days_until_monday = (7 - next_day.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_day = next_day.replace(day=next_day.day + days_until_monday)
            else:
                next_day = next_day.replace(day=next_day.day + 1)
        
        if is_open:
            message = f"We're currently open. Business hours are {BUSINESS_HOURS_START} AM to {BUSINESS_HOURS_END - 12} PM CST, Monday through Friday."
        else:
            message = f"We're currently closed. Business hours are {BUSINESS_HOURS_START} AM to {BUSINESS_HOURS_END - 12} PM CST, Monday through Friday. We'll be open again on {next_day.strftime('%A, %B %d')}."
        
        return ToolResponse(
            speak=message,
            action="completed",
            data={
                "is_business_hours": is_open,
                "current_time": now.isoformat(),
                "business_hours_start": BUSINESS_HOURS_START,
                "business_hours_end": BUSINESS_HOURS_END,
                "next_business_day": next_day.isoformat(),
            },
        )
    
    except Exception as e:
        return handler.format_error_response(e)
