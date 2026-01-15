"""
HAES HVAC - Odoo Sales Quote Integration

Creates sale.order quotes in Odoo with line items, pricing, validity period,
and approval workflow based on quote value.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from src.integrations.odoo import OdooClient, create_odoo_client_from_settings
from src.hael.schema import Entity
from src.utils.errors import OdooRPCError, OdooTransportError
from src.brains.core.schema import PricingTier

logger = logging.getLogger(__name__)

# Quote validity period (days)
DEFAULT_QUOTE_VALIDITY_DAYS = 30

# Approval thresholds
APPROVAL_THRESHOLD_HIGH_VALUE = 20000.0  # Quotes >$20K need approval
APPROVAL_THRESHOLD_MID_VALUE = 10000.0  # Quotes $10K-$20K assigned to Linda

# System type to line item mapping (simplified - in production would use product catalog)
SYSTEM_TYPE_PRODUCTS = {
    "complete_split_system": {
        "name": "Complete Split System Installation",
        "description": "3-piece HVAC system (Furnace, AC, Coil)",
        "estimated_unit_price": 7000.0,
    },
    "heat_pump": {
        "name": "Heat Pump Installation",
        "description": "Complete heat pump system",
        "estimated_unit_price": 8000.0,
    },
    "furnace": {
        "name": "Furnace Installation",
        "description": "Gas/electric furnace replacement",
        "estimated_unit_price": 5000.0,
    },
    "air_conditioner": {
        "name": "Air Conditioner Installation",
        "description": "Central AC unit installation",
        "estimated_unit_price": 4500.0,
    },
    "ductless_mini_split": {
        "name": "Ductless Mini Split Installation",
        "description": "Ductless mini-split system",
        "estimated_unit_price": 5500.0,
    },
}


class QuoteService:
    """Service for managing sales quotes in Odoo."""
    
    def __init__(self, client: OdooClient):
        self.client = client
    
    async def _ensure_authenticated(self) -> None:
        """Ensure the client is authenticated."""
        if not self.client.is_authenticated:
            await self.client.authenticate()
    
    async def create_quote(
        self,
        entities: Entity,
        estimated_value: float | None = None,
        system_type: str | None = None,
            pricing_tier: PricingTier = PricingTier.RETAIL,
        assigned_to_user_id: int | None = None,
        lead_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a sale.order quote in Odoo (Test 3.6).
        
        Args:
            entities: Customer entity with contact information
            estimated_value: Estimated quote value
            system_type: Type of HVAC system
            pricing_tier: Pricing tier (RESIDENTIAL, COMMERCIAL, PROPERTY_MANAGEMENT)
            assigned_to_user_id: User ID to assign quote to (optional)
            lead_id: CRM lead ID to link quote to (optional)
            
        Returns:
            Dictionary with quote_id and quote details
        """
        await self._ensure_authenticated()
        
        # Find or create partner (customer)
        partner_id = await self._find_or_create_partner(entities)
        
        # Calculate quote total and determine line items
        quote_total, order_lines = self._build_quote_line_items(
            system_type=system_type,
            estimated_value=estimated_value,
            square_footage=entities.square_footage,
            pricing_tier=pricing_tier,
        )
        
        # Determine quote status based on value
        quote_status, requires_approval = self._determine_quote_status(quote_total)
        
        # Determine assignment
        if not assigned_to_user_id:
            assigned_to_user_id = await self._determine_assignment(quote_total)
        
        # Set validity period
        validity_date = (datetime.now() + timedelta(days=DEFAULT_QUOTE_VALIDITY_DAYS)).date()
        
        # Format order lines for Odoo One2many format: [(0, 0, {values})]
        odoo_order_lines = [
            (0, 0, line_values)  # (0, 0, values) means create new record
            for line_values in order_lines
        ]
        
        # Create sale.order quote
        quote_values = {
            "partner_id": partner_id,
            "state": "draft",  # Quote state (draft = quote, sent = sent to customer, etc.)
            "date_order": datetime.now().isoformat(),
            "validity_date": validity_date.isoformat(),
            "order_line": odoo_order_lines,
            "note": self._build_quote_notes(entities, system_type),
        }
        
        # Assign salesperson if provided
        if assigned_to_user_id:
            quote_values["user_id"] = assigned_to_user_id
        
        # Link to CRM lead if provided
        if lead_id:
            quote_values["opportunity_id"] = lead_id
        
        try:
            quote_id = await self.client.create("sale.order", quote_values)
            logger.info(f"Created sale.order quote {quote_id} for partner {partner_id}")
            
            return {
                "quote_id": quote_id,
                "quote_total": quote_total,
                "quote_status": quote_status,
                "requires_approval": requires_approval,
                "validity_date": validity_date.isoformat(),
                "assigned_to_user_id": assigned_to_user_id,
                "partner_id": partner_id,
            }
        except OdooRPCError as e:
            logger.error(f"Failed to create sale.order quote: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error creating quote: {e}")
            raise
    
    async def _find_or_create_partner(self, entities: Entity) -> int:
        """Find existing partner or create new one."""
        # Search for existing partner by phone or email
        domain = []
        if entities.phone:
            domain.append(("phone", "=", entities.phone))
        elif entities.email:
            domain.append(("email", "=", entities.email))
        
        if domain:
            partners = await self.client.search_read(
                "res.partner",
                domain,
                fields=["id"],
                limit=1,
            )
            if partners:
                return partners[0]["id"]
        
        # Create new partner
        partner_values = {
            "name": entities.full_name or "Customer",
            "phone": entities.phone,
            "email": entities.email,
            "street": entities.address,
        }
        
        partner_id = await self.client.create("res.partner", partner_values)
        logger.info(f"Created new partner {partner_id} for quote")
        return partner_id
    
    def _build_quote_line_items(
        self,
        system_type: str | None,
        estimated_value: float | None,
        square_footage: int | None,
        pricing_tier: PricingTier,
    ) -> tuple[float, list[dict[str, Any]]]:
        """
        Build sale.order line items based on system type and estimated value.
        
        Returns:
            Tuple of (total_amount, list of order_line dictionaries)
        """
        order_lines = []
        total_amount = 0.0
        
        # If system type specified, use product mapping
        if system_type:
            system_lower = system_type.lower().replace(" ", "_")
            product_info = None
            
            for key, info in SYSTEM_TYPE_PRODUCTS.items():
                if key in system_lower:
                    product_info = info
                    break
            
            if product_info:
                # Apply pricing tier multiplier
                base_price = product_info["estimated_unit_price"]
                tier_multiplier = self._get_pricing_tier_multiplier(pricing_tier)
                unit_price = base_price * tier_multiplier
                
                order_lines.append({
                    "product_id": False,  # Would link to actual product in production
                    "name": product_info["name"],
                    "product_uom_qty": 1.0,
                    "price_unit": unit_price,
                })
                total_amount = unit_price
        
        # If estimated value provided and no line items yet, create generic line
        if estimated_value and not order_lines:
            order_lines.append({
                "product_id": False,
                "name": "HVAC System Installation - Custom Quote",
                "product_uom_qty": 1.0,
                "price_unit": estimated_value,
            })
            total_amount = estimated_value
        
        # Fallback: Estimate from square footage
        if not order_lines and square_footage:
            # Rough estimate: $3-5 per sq ft
            estimated_value = square_footage * 4.0  # Use middle estimate
            order_lines.append({
                "product_id": False,
                "name": "HVAC System Installation - Estimated from Square Footage",
                "product_uom_qty": 1.0,
                "price_unit": estimated_value,
            })
            total_amount = estimated_value
        
        # Default minimum quote if nothing else
        if not order_lines:
            total_amount = 6000.0  # Default minimum
            order_lines.append({
                "product_id": False,
                "name": "HVAC System Installation - Base Quote",
                "product_uom_qty": 1.0,
                "price_unit": total_amount,
            })
        
        return total_amount, order_lines
    
    def _get_pricing_tier_multiplier(self, pricing_tier: PricingTier) -> float:
        """Get pricing multiplier based on pricing tier."""
        # In production, this would be based on actual pricing catalog
        # For now, return 1.0 (base pricing)
        return 1.0
    
    def _determine_quote_status(self, quote_total: float) -> tuple[str, bool]:
        """
        Determine quote status based on value (Test 3.6).
        
        Rules:
        - <$20K: Draft (auto-approved)
        - >$20K: Draft (pending approval)
        
        Returns:
            Tuple of (status, requires_approval)
        """
        if quote_total >= APPROVAL_THRESHOLD_HIGH_VALUE:
            return "draft", True  # Pending approval
        else:
            return "draft", False  # Auto-approved
    
    async def _determine_assignment(self, quote_total: float) -> int | None:
        """
        Determine who to assign quote to (Test 3.6).
        
        Rules:
        - High-value (>$20K): Junior
        - Mid-value ($10K-$20K): Linda
        - Low-value (<$10K): Auto-assigned or default
        
        Returns:
            User ID or None
        """
        # In production, would look up actual user IDs
        # For now, return None (Odoo will use default)
        
        # TODO: Implement user ID lookup
        # if quote_total >= APPROVAL_THRESHOLD_HIGH_VALUE:
        #     # Look up Junior's user ID
        #     return junior_user_id
        # elif quote_total >= APPROVAL_THRESHOLD_MID_VALUE:
        #     # Look up Linda's user ID
        #     return linda_user_id
        
        return None
    
    def _build_quote_notes(self, entities: Entity, system_type: str | None) -> str:
        """Build internal notes for the quote."""
        notes_parts = []
        
        if entities.property_type:
            notes_parts.append(f"Property Type: {entities.property_type}")
        if entities.square_footage:
            notes_parts.append(f"Square Footage: {entities.square_footage}")
        if entities.system_age_years:
            notes_parts.append(f"Current System Age: {entities.system_age_years} years")
        if system_type:
            notes_parts.append(f"System Type: {system_type}")
        if entities.budget_range:
            notes_parts.append(f"Budget Range: {entities.budget_range}")
        if entities.timeline:
            notes_parts.append(f"Timeline: {entities.timeline}")
        
        return "\n".join(notes_parts) if notes_parts else "Quote generated via AI voice agent"


async def create_quote_service(client: OdooClient | None = None) -> QuoteService:
    """
    Create a QuoteService instance.
    
    Args:
        client: Optional OdooClient instance (will create from settings if not provided)
        
    Returns:
        QuoteService instance
    """
    if client is None:
        client = create_odoo_client_from_settings()
    return QuoteService(client)
