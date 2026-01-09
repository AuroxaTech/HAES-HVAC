"""
HAES HVAC - API Module

API routers for external integrations:
- Vapi tools (Module 8)
- Vapi Server URL (Vapi Full Setup)
- Chat (Module 8)
- Reports (Module 9)
"""

from src.api.vapi_tools import router as vapi_tools_router
from src.api.vapi_server import router as vapi_server_router
from src.api.chat import router as chat_router

__all__ = ["vapi_tools_router", "vapi_server_router", "chat_router"]

