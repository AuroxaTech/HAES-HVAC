"""
HAES HVAC - Odoo CRM Lead Integration

Creates and updates CRM leads in Odoo for service requests.
Designed for idempotent upsert operations (one lead per call_id).
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from src.integrations.odoo import OdooClient, create_odoo_client_from_settings
from src.hael.schema import Entity, UrgencyLevel
from src.utils.errors import OdooRPCError, OdooTransportError

logger = logging.getLogger(__name__)

# Fields we commonly write to crm.lead
# We'll verify these exist before writing
CRM_LEAD_FIELDS = [
    "name",
    "description",
    "contact_name",
    "phone",
    "email_from",
    "partner_id",
    "street",
    "city",
    "zip",
    "state_id",
    "country_id",
    "type",  # lead vs opportunity
    "priority",  # 0-3 priority
]

# Mapping from UrgencyLevel to Odoo priority (0=low, 1=medium, 2=high, 3=very high)
URGENCY_TO_PRIORITY = {
    UrgencyLevel.EMERGENCY: "3",
    UrgencyLevel.HIGH: "2",
    UrgencyLevel.MEDIUM: "1",
    UrgencyLevel.LOW: "0",
    UrgencyLevel.UNKNOWN: "1",  # Default to medium
}


class LeadService:
    """
    Service for managing CRM leads in Odoo.
    
    Handles:
    - Partner (contact) lookup/creation
    - Lead creation and updates
    - Safe field mapping with capability checking
    """
    
    def __init__(self, client: OdooClient):
        self.client = client
        self._crm_lead_fields: set[str] | None = None
        self._partner_fields: set[str] | None = None
    
    async def _ensure_authenticated(self) -> None:
        """Ensure the client is authenticated."""
        if not self.client.is_authenticated:
            await self.client.authenticate()
    
    async def _get_crm_lead_fields(self) -> set[str]:
        """
        Get available fields for crm.lead model.
        Caches result for performance.
        """
        if self._crm_lead_fields is None:
            try:
                await self._ensure_authenticated()
                fields_info = await self.client.fields_get("crm.lead")
                self._crm_lead_fields = set(fields_info.keys())
                logger.debug(f"Cached {len(self._crm_lead_fields)} crm.lead fields")
            except Exception as e:
                logger.warning(f"Failed to get crm.lead fields: {e}")
                # Fall back to commonly available fields
                self._crm_lead_fields = set(CRM_LEAD_FIELDS)
        return self._crm_lead_fields
    
    async def _get_partner_fields(self) -> set[str]:
        """
        Get available fields for res.partner model.
        Caches result for performance.
        """
        if self._partner_fields is None:
            try:
                await self._ensure_authenticated()
                fields_info = await self.client.fields_get("res.partner")
                self._partner_fields = set(fields_info.keys())
                logger.debug(f"Cached {len(self._partner_fields)} res.partner fields")
            except Exception as e:
                logger.warning(f"Failed to get res.partner fields: {e}")
                self._partner_fields = {"name", "phone", "email", "street", "city", "zip"}
        return self._partner_fields
    
    def _filter_valid_fields(self, values: dict[str, Any], valid_fields: set[str]) -> dict[str, Any]:
        """Filter out fields that don't exist in the model."""
        return {k: v for k, v in values.items() if k in valid_fields and v is not None}
    
    async def ensure_partner(
        self,
        phone: str | None = None,
        email: str | None = None,
        name: str | None = None,
        address: str | None = None,
        city: str | None = None,
        zip_code: str | None = None,
    ) -> int | None:
        """
        Find or create a res.partner (contact) in Odoo.
        
        Searches by phone first, then email. Creates new if not found OR if
        the existing partner's name doesn't match (to avoid updating wrong contact).
        
        Args:
            phone: Phone number
            email: Email address
            name: Contact name
            address: Street address
            city: City
            zip_code: ZIP/postal code
            
        Returns:
            Partner ID if found/created, None if failed
        """
        try:
            await self._ensure_authenticated()
            
            # Normalize phone for search
            clean_phone = None
            if phone:
                clean_phone = re.sub(r"[^\d+]", "", phone)
            
            # Helper to check if names match (fuzzy)
            def names_match(existing_name: str, new_name: str | None) -> bool:
                if not new_name:
                    return True  # No new name provided, assume match
                existing_lower = (existing_name or "").lower().strip()
                new_lower = new_name.lower().strip()
                # Exact match or one contains the other
                return (
                    existing_lower == new_lower or
                    existing_lower in new_lower or
                    new_lower in existing_lower
                )
            
            # Search by phone first
            if clean_phone:
                partners = await self.client.search_read(
                    "res.partner",
                    [("phone", "ilike", clean_phone[-10:])],  # Last 10 digits
                    fields=["id", "name", "phone", "email"],
                    limit=1,
                )
                if partners:
                    existing = partners[0]
                    if names_match(existing["name"], name):
                        logger.info(f"Found existing partner by phone: {existing['id']} ({existing['name']})")
                        return existing["id"]
                    else:
                        logger.info(f"Found partner {existing['id']} by phone but name mismatch: '{existing['name']}' vs '{name}' - creating new")
            
            # Search by email
            if email:
                partners = await self.client.search_read(
                    "res.partner",
                    [("email", "=ilike", email)],
                    fields=["id", "name", "phone", "email"],
                    limit=1,
                )
                if partners:
                    existing = partners[0]
                    if names_match(existing["name"], name):
                        logger.info(f"Found existing partner by email: {existing['id']} ({existing['name']})")
                        return existing["id"]
                    else:
                        logger.info(f"Found partner {existing['id']} by email but name mismatch: '{existing['name']}' vs '{name}' - creating new")
            
            # Create new partner
            valid_fields = await self._get_partner_fields()
            partner_values = {
                "name": name or phone or email or "Unknown Caller",
                "phone": phone,
                "email": email,
                "street": address,
                "city": city,
                "zip": zip_code,
                "is_company": False,
            }
            partner_values = self._filter_valid_fields(partner_values, valid_fields)
            
            if not partner_values.get("name"):
                partner_values["name"] = "Unknown Caller"
            
            partner_id = await self.client.create("res.partner", partner_values)
            logger.info(f"Created new partner: {partner_id}")
            return partner_id
            
        except Exception as e:
            logger.warning(f"Failed to ensure partner: {e}")
            return None
    
    async def search_lead_by_ref(self, call_id: str) -> dict[str, Any] | None:
        """
        Search for an existing lead by call_id reference.
        
        We store call_id in the lead description or a ref field.
        
        Args:
            call_id: The Vapi call ID
            
        Returns:
            Lead dict if found, None otherwise
        """
        try:
            await self._ensure_authenticated()
            
            # Search in description for the call_id marker
            leads = await self.client.search_read(
                "crm.lead",
                [("description", "ilike", f"[call_id:{call_id}]")],
                fields=["id", "name", "description", "phone", "email_from", "contact_name"],
                limit=1,
            )
            
            if leads:
                return leads[0]
            return None
            
        except Exception as e:
            logger.warning(f"Failed to search lead by ref: {e}")
            return None
    
    async def upsert_service_lead(
        self,
        call_id: str,
        entities: Entity,
        urgency: UrgencyLevel = UrgencyLevel.UNKNOWN,
        is_emergency: bool = False,
        emergency_reason: str | None = None,
        raw_text: str = "",
        structured_params: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create or update a CRM lead for a service request.
        
        Uses call_id to ensure idempotency - multiple calls with same
        call_id will update the existing lead.
        
        Args:
            call_id: Vapi call ID (unique per conversation)
            entities: Extracted entities from HAEL
            urgency: Urgency level
            is_emergency: Whether this is an emergency
            emergency_reason: Reason for emergency classification
            raw_text: Original user text
            structured_params: Additional structured parameters
            request_id: Internal request ID
            
        Returns:
            Dict with lead_id, action (created/updated), and status
        """
        try:
            await self._ensure_authenticated()
            valid_fields = await self._get_crm_lead_fields()
            
            # Check for existing lead
            existing_lead = await self.search_lead_by_ref(call_id)
            
            # Build lead name
            location_hint = (
                entities.city or
                entities.zip_code or
                (entities.phone[-4:] if entities.phone else None) or
                call_id[:8]
            )
            lead_name = f"Service Request - {location_hint}"
            if is_emergency:
                lead_name = f"🚨 EMERGENCY: {lead_name}"
            
            # Build description with HTML formatting for Odoo
            desc_html = []
            
            # Hidden marker for search (small text)
            desc_html.append(f'<p style="font-size:10px;color:#888;">[call_id:{call_id}]</p>')
            
            # Emergency banner
            if is_emergency:
                desc_html.append(
                    '<div style="background:#fee;border:2px solid #c00;padding:10px;margin:10px 0;border-radius:5px;">'
                    f'<strong style="color:#c00;">⚠️ EMERGENCY</strong><br/>'
                    f'{emergency_reason or "Urgent attention needed"}'
                    '</div>'
                )
            
            # Customer Information Section
            desc_html.append('<h3 style="border-bottom:1px solid #ccc;padding-bottom:5px;">📋 Customer Information</h3>')
            desc_html.append('<table style="width:100%;border-collapse:collapse;">')
            
            if entities.full_name:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;width:120px;">Name:</td><td style="padding:5px;">{entities.full_name}</td></tr>')
            if entities.phone:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;">Phone:</td><td style="padding:5px;">{entities.phone}</td></tr>')
            if entities.email:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;">Email:</td><td style="padding:5px;">{entities.email}</td></tr>')
            if entities.address:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;">Address:</td><td style="padding:5px;">{entities.address}</td></tr>')
            elif entities.zip_code:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;">ZIP Code:</td><td style="padding:5px;">{entities.zip_code}</td></tr>')
            if entities.property_type:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;">Property:</td><td style="padding:5px;">{entities.property_type.title()}</td></tr>')
            
            desc_html.append('</table>')
            
            # Service Request Details Section
            desc_html.append('<h3 style="border-bottom:1px solid #ccc;padding-bottom:5px;margin-top:15px;">🔧 Service Request</h3>')
            desc_html.append('<table style="width:100%;border-collapse:collapse;">')
            
            # Urgency with color coding
            urgency_colors = {
                "emergency": "#c00",
                "high": "#f60",
                "medium": "#fc0",
                "low": "#090",
            }
            urgency_color = urgency_colors.get(urgency.value, "#666")
            desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;width:120px;">Urgency:</td><td style="padding:5px;"><span style="color:{urgency_color};font-weight:bold;">{urgency.value.upper()}</span></td></tr>')
            
            if entities.problem_description:
                desc_html.append(f'<tr><td style="padding:5px;font-weight:bold;vertical-align:top;">Issue:</td><td style="padding:5px;">{entities.problem_description}</td></tr>')
            
            desc_html.append('</table>')
            
            # Metadata Section
            desc_html.append('<h3 style="border-bottom:1px solid #ccc;padding-bottom:5px;margin-top:15px;">📝 Metadata</h3>')
            desc_html.append('<table style="width:100%;border-collapse:collapse;font-size:12px;color:#666;">')
            
            if request_id:
                desc_html.append(f'<tr><td style="padding:3px;width:120px;">Request ID:</td><td style="padding:3px;">{request_id}</td></tr>')
            desc_html.append(f'<tr><td style="padding:3px;">Created:</td><td style="padding:3px;">{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</td></tr>')
            desc_html.append(f'<tr><td style="padding:3px;">Channel:</td><td style="padding:3px;">Voice (Vapi)</td></tr>')
            
            desc_html.append('</table>')
            
            description = "".join(desc_html)
            
            # Build lead values
            priority = URGENCY_TO_PRIORITY.get(urgency, "1")
            
            lead_values: dict[str, Any] = {
                "name": lead_name,
                "description": description,
                "contact_name": entities.full_name,
                "phone": entities.phone,
                "email_from": entities.email,
                "street": entities.address,
                "city": entities.city,
                "zip": entities.zip_code,
                "priority": priority,
                "type": "lead",  # Keep as lead until converted
            }
            
            # Try to link partner if we can create/find one
            partner_id = await self.ensure_partner(
                phone=entities.phone,
                email=entities.email,
                name=entities.full_name,
                address=entities.address,
                city=entities.city,
                zip_code=entities.zip_code,
            )
            if partner_id:
                lead_values["partner_id"] = partner_id
            
            # Filter to valid fields only
            lead_values = self._filter_valid_fields(lead_values, valid_fields)
            
            if existing_lead:
                # Update existing lead
                lead_id = existing_lead["id"]
                await self.client.write("crm.lead", [lead_id], lead_values)
                logger.info(f"Updated existing lead: {lead_id}")
                return {
                    "lead_id": lead_id,
                    "action": "updated",
                    "status": "success",
                    "partner_id": partner_id,
                }
            else:
                # Create new lead
                lead_id = await self.client.create("crm.lead", lead_values)
                logger.info(f"Created new lead: {lead_id}")
                return {
                    "lead_id": lead_id,
                    "action": "created",
                    "status": "success",
                    "partner_id": partner_id,
                }
                
        except OdooRPCError as e:
            logger.error(f"Odoo RPC error creating lead: {e}")
            return {
                "lead_id": None,
                "action": "failed",
                "status": "error",
                "error": str(e),
            }
        except OdooTransportError as e:
            logger.error(f"Odoo transport error creating lead: {e}")
            return {
                "lead_id": None,
                "action": "failed",
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error creating lead: {e}")
            return {
                "lead_id": None,
                "action": "failed",
                "status": "error",
                "error": str(e),
            }


# =============================================================================
# Call-to-Lead Correlation (Phase 2)
# =============================================================================

# Uses idempotency_keys table to track call_id → lead_id mapping
# Scope: "vapi_call_lead"
# Key: call_id
# response_json: {"odoo_lead_id": <id>, "partner_id": <id>}

CALL_LEAD_SCOPE = "vapi_call_lead"


class CallLeadCorrelation:
    """
    Manages the correlation between Vapi call_id and Odoo lead_id.
    
    Uses the idempotency_keys table to persist this mapping,
    ensuring one lead per call even across multiple tool-calls.
    """
    
    def __init__(self, db_session):
        """
        Initialize with a database session.
        
        Args:
            db_session: SQLAlchemy session
        """
        self.session = db_session
    
    def get_lead_id_for_call(self, call_id: str) -> int | None:
        """
        Get the Odoo lead_id for a given call_id if it exists.
        
        Args:
            call_id: Vapi call ID
            
        Returns:
            Odoo lead_id if found, None otherwise
        """
        from sqlalchemy import select
        from src.db.models import IdempotencyKey
        
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.scope == CALL_LEAD_SCOPE,
            IdempotencyKey.key == call_id,
            IdempotencyKey.status == "completed",
        )
        record = self.session.execute(stmt).scalar_one_or_none()
        
        if record and record.response_json:
            return record.response_json.get("odoo_lead_id")
        return None
    
    def store_lead_id_for_call(
        self,
        call_id: str,
        lead_id: int,
        partner_id: int | None = None,
    ) -> None:
        """
        Store the Odoo lead_id for a given call_id.
        
        Args:
            call_id: Vapi call ID
            lead_id: Odoo CRM lead ID
            partner_id: Odoo partner ID (optional)
        """
        from datetime import timedelta, timezone
        from sqlalchemy import select
        from src.db.models import IdempotencyKey
        
        # Check if exists
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.scope == CALL_LEAD_SCOPE,
            IdempotencyKey.key == call_id,
        )
        record = self.session.execute(stmt).scalar_one_or_none()
        
        response_data = {
            "odoo_lead_id": lead_id,
            "partner_id": partner_id,
            "stored_at": datetime.utcnow().isoformat(),
        }
        
        if record:
            # Update existing
            record.status = "completed"
            record.response_json = response_data
        else:
            # Create new
            record = IdempotencyKey(
                scope=CALL_LEAD_SCOPE,
                key=call_id,
                status="completed",
                response_json=response_data,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),  # Keep for 30 days
            )
            self.session.add(record)
        
        self.session.commit()
        logger.debug(f"Stored call→lead mapping: {call_id} → {lead_id}")
    
    def get_or_none(self, call_id: str) -> dict[str, Any] | None:
        """
        Get the full stored response for a call_id.
        
        Args:
            call_id: Vapi call ID
            
        Returns:
            Dict with odoo_lead_id, partner_id, etc. or None
        """
        from sqlalchemy import select
        from src.db.models import IdempotencyKey
        
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.scope == CALL_LEAD_SCOPE,
            IdempotencyKey.key == call_id,
            IdempotencyKey.status == "completed",
        )
        record = self.session.execute(stmt).scalar_one_or_none()
        
        if record and record.response_json:
            return record.response_json
        return None


# =============================================================================
# Convenience Functions
# =============================================================================


async def create_lead_service() -> LeadService:
    """
    Create a LeadService instance from settings.
    
    Returns:
        Configured LeadService (client not yet authenticated)
    """
    client = create_odoo_client_from_settings()
    return LeadService(client)


async def upsert_lead_for_call(
    call_id: str,
    entities: Entity,
    urgency: UrgencyLevel = UrgencyLevel.UNKNOWN,
    is_emergency: bool = False,
    emergency_reason: str | None = None,
    raw_text: str = "",
    structured_params: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to upsert a lead for a call.
    
    Creates the LeadService, performs the upsert, and cleans up.
    
    Returns:
        Dict with lead_id, action, and status
    """
    client = create_odoo_client_from_settings()
    service = LeadService(client)
    
    try:
        result = await service.upsert_service_lead(
            call_id=call_id,
            entities=entities,
            urgency=urgency,
            is_emergency=is_emergency,
            emergency_reason=emergency_reason,
            raw_text=raw_text,
            structured_params=structured_params,
            request_id=request_id,
        )
        return result
    finally:
        await client.close()
