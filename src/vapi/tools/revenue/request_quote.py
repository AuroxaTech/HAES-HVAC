"""
HAES HVAC - Request Quote Tool

Direct Vapi tool for requesting installation/equipment quotes.
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
from src.brains.revenue import handle_revenue_command
from src.brains.revenue.schema import RevenueStatus
from src.utils.request_id import generate_request_id

logger = logging.getLogger(__name__)


async def handle_request_quote(
    tool_call_id: str,
    parameters: dict[str, Any],
    call_id: str | None = None,
    conversation_context: str | None = None,
) -> ToolResponse:
    """
    Handle request_quote tool call.
    
    Parameters:
        - customer_name (required): Customer name
        - phone (required): Phone number
        - email (optional): Email address
        - address (required): Property address
        - property_type (required): "residential", "commercial", "property_management"
        - square_footage (optional): Square footage
        - system_age_years (optional): System age in years
        - budget_range (optional): Budget range
        - timeline (required): Timeline for installation
        - system_type (optional): HVAC system type
    """
    handler = BaseToolHandler("request_quote")
    
    # Validate required parameters
    required = ["customer_name", "phone", "address", "property_type", "timeline"]
    is_valid, missing = handler.validate_required_params(parameters, required)
    
    if not is_valid:
        # Intent-First Rule: Don't ask for details in the same response as acknowledging intent
        return handler.format_needs_human_response(
            "I can help you with a quote for that.",
            missing_fields=missing,
            intent_acknowledged=False,
        )
    
    # Normalize phone
    phone = handler.normalize_phone(parameters.get("phone"))
    if not phone:
        return handler.format_needs_human_response(
            "I can help you with a quote for that.",
            missing_fields=["phone"],
            intent_acknowledged=False,
        )
    
    # Build Entity
    entities = Entity(
        full_name=parameters.get("customer_name"),
        phone=phone,
        email=handler.normalize_email(parameters.get("email")),
        address=parameters.get("address"),
        property_type=parameters.get("property_type"),
        square_footage=parameters.get("square_footage"),
        system_age_years=parameters.get("system_age_years"),
        budget_range=parameters.get("budget_range"),
        timeline=parameters.get("timeline"),
        system_type=parameters.get("system_type"),
    )
    
    # Build HaelCommand
    request_id = generate_request_id()
    command = HaelCommand(
        request_id=request_id,
        channel=Channel.VOICE,
        raw_text=conversation_context or parameters.get("timeline", ""),
        intent=Intent.QUOTE_REQUEST,
        brain=Brain.REVENUE,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "tool_call_id": tool_call_id,
            "call_id": call_id,
        },
    )
    
    # Call REVENUE brain handler
    try:
        result = handle_revenue_command(command)
        
        if result.requires_human or result.status == RevenueStatus.NEEDS_HUMAN:
            return handler.format_needs_human_response(
                result.message,
                missing_fields=getattr(result, "missing_fields", None),
                data=result.data or {},
            )
        
        if result.status == RevenueStatus.ERROR:
            return handler.format_error_response(
                Exception(result.message),
                "I encountered an error processing your quote request. Please try again or contact us directly.",
            )
        
        # Create lead in Odoo first (if not already created)
        lead_id = None
        try:
            from src.integrations.odoo_leads import create_lead_service
            
            lead_service = await create_lead_service()
            
            lead_result = await lead_service.upsert_service_lead(
                call_id=call_id or f"quote_{request_id}",
                entities=entities,
                urgency=entities.urgency_level,
                is_emergency=False,
                raw_text=conversation_context or "",
                request_id=request_id,
                channel="voice",
            )
            
            lead_id = lead_result.get("lead_id") if lead_result else None
        except Exception as lead_err:
            logger.warning(f"Failed to create lead for quote: {lead_err}")
            # Continue anyway - quote can be created without lead
        
        # Create sale.order quote in Odoo (Test 3.6)
        quote_id = None
        quote_data_from_result = (result.data or {}).get("quote_data")
        if quote_data_from_result and quote_data_from_result.get("needs_quote_creation"):
            try:
                from src.integrations.odoo_quotes import create_quote_service
                from src.brains.core.schema import PricingTier
                from src.integrations.odoo import create_odoo_client_from_settings
                
                client = create_odoo_client_from_settings()
                quote_service = await create_quote_service(client)
                
                # Map property type to PricingTier
                property_type = entities.property_type or "residential"
                if property_type.lower() in ["commercial", "business", "office", "industrial"]:
                    pricing_tier = PricingTier.COM
                elif property_type.lower() in ["property_management", "pm"]:
                    pricing_tier = PricingTier.DEFAULT_PM
                else:
                    pricing_tier = PricingTier.RETAIL  # Default to retail for residential
                
                quote_result = await quote_service.create_quote(
                    entities=entities,
                    lead_id=lead_id,
                    system_type=quote_data_from_result.get("system_type") or parameters.get("system_type"),
                    pricing_tier=pricing_tier,
                )
                
                quote_id = quote_result.get("quote_id")
                logger.info(f"Created sale.order quote {quote_id} for lead {lead_id}")
            except Exception as quote_err:
                logger.warning(f"Failed to create sale.order quote: {quote_err}")
                # Continue anyway - lead is still created
        
        # Format success response
        response_data = result.data or {}
        response_data["request_id"] = request_id
        if lead_id:
            response_data["lead_id"] = lead_id
        if quote_id:
            response_data["quote_id"] = quote_id
        
        # Add financing options
        response_data["financing_options"] = {
            "available": True,
            "partners": [
                {
                    "name": "Greensky",
                    "description": "Fast approval, flexible terms"
                },
                {
                    "name": "FTL",
                    "description": "Competitive rates for qualified buyers"
                },
                {
                    "name": "Microft",
                    "description": "Specialized HVAC financing"
                }
            ],
            "message": "We partner with multiple financing companies to help make new HVAC systems affordable. We can help you get approved quickly."
        }
        
        # Add estimated price ranges based on system type
        system_type = parameters.get("system_type", "").lower()
        square_footage = parameters.get("square_footage")
        
        # Price ranges (approximate, based on typical HVAC installations)
        price_ranges = {
            "complete_split_system": {"min": 6526, "max": 8441},
            "heat_pump": {"min": 7000, "max": 9000},
            "furnace": {"min": 4000, "max": 6000},
            "air_conditioner": {"min": 3500, "max": 5500},
            "ductless_mini_split": {"min": 3000, "max": 8000},
        }
        
        # Default range if system type not specified
        default_range = {"min": 6000, "max": 8500}
        
        if system_type in price_ranges:
            response_data["estimated_price_range"] = price_ranges[system_type]
        else:
            response_data["estimated_price_range"] = default_range
        
        # Note: Actual pricing will be provided in the detailed quote
        response_data["pricing_note"] = "These are estimated ranges. A detailed quote with exact pricing will be provided based on your specific property and system requirements."
        
        # Build enhanced response message with financing information
        base_message = result.message
        
        # Add price range info
        price_range = response_data.get("estimated_price_range", default_range)
        price_message = f"Based on your requirements, the estimated price range is ${price_range['min']:,} to ${price_range['max']:,}."
        
        # Add financing information
        financing_message = (
            "Yes, we offer financing! We partner with Greensky, FTL, and Microft to help make your new HVAC system affordable. "
            "We can help you get approved quickly - most applications are approved within minutes. "
            "Would you like me to send you more information about our financing options?"
        )
        
        # Combine messages
        enhanced_message = f"{base_message} {price_message} {financing_message}"
        
        # Check if customer expressed interest in financing
        interested_in_financing = (
            parameters.get("interested_in_financing") or
            parameters.get("financing_interest") or
            (conversation_context and any(keyword in conversation_context.lower() for keyword in ["financing", "finance", "loan", "payment plan"]))
        )
        
        # If interested, offer to collect contact info for financing details
        if interested_in_financing:
            email = handler.normalize_email(parameters.get("email"))
            if not email:
                # Ask for email to send financing info
                return handler.format_needs_human_response(
                    f"{enhanced_message}",
                    missing_fields=["email"],
                    data={
                        **response_data,
                        "awaiting_financing_contact_info": True,
                    },
                )
            else:
                # Email available, mention it will be sent
                enhanced_message += f" I'll send detailed financing information to {email}."
                
                # TODO: Send financing information email/SMS (handled by follow-up automation)
                response_data["financing_info_requested"] = True
                response_data["financing_contact_email"] = email
        
        return handler.format_success_response(
            enhanced_message,
            data=response_data,
        )
    
    except Exception as e:
        return handler.format_error_response(e)
