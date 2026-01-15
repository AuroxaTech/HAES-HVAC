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
    
    async def ensure_emergency_tag(self) -> int | None:
        """
        Find or create an 'Emergency' tag in crm.tag.
        
        Returns:
            Tag ID if found/created, None on failure
        """
        try:
            await self._ensure_authenticated()
            
            # Search for existing tag
            tags = await self.client.search_read(
                "crm.tag",
                [("name", "=", "Emergency")],
                fields=["id"],
                limit=1,
            )
            
            if tags:
                logger.debug(f"Found existing Emergency tag: {tags[0]['id']}")
                return tags[0]["id"]
            
            # Create new tag
            tag_id = await self.client.create("crm.tag", {"name": "Emergency", "color": 1})
            logger.info(f"Created Emergency tag: {tag_id}")
            return tag_id
            
        except Exception as e:
            logger.warning(f"Failed to ensure Emergency tag: {e}")
            return None
    
    async def ensure_lead_source(self, source_name: str = "AI Voice Agent") -> int | None:
        """
        Find or create a lead source in utm.source.
        
        Args:
            source_name: Name of the source (default: "AI Voice Agent")
            
        Returns:
            Source ID if found/created, None on failure
        """
        try:
            await self._ensure_authenticated()
            
            # Search for existing source
            sources = await self.client.search_read(
                "utm.source",
                [("name", "=", source_name)],
                fields=["id"],
                limit=1,
            )
            
            if sources:
                logger.debug(f"Found existing source: {sources[0]['id']}")
                return sources[0]["id"]
            
            # Create new source
            source_id = await self.client.create("utm.source", {"name": source_name})
            logger.info(f"Created source '{source_name}': {source_id}")
            return source_id
            
        except Exception as e:
            logger.warning(f"Failed to ensure lead source '{source_name}': {e}")
            return None
    
    async def ensure_tag(self, tag_name: str, color: int = 1) -> int | None:
        """
        Find or create a tag in crm.tag.
        
        Args:
            tag_name: Name of the tag
            color: Tag color (0-11)
            
        Returns:
            Tag ID if found/created, None on failure
        """
        try:
            await self._ensure_authenticated()
            
            # Search for existing tag
            tags = await self.client.search_read(
                "crm.tag",
                [("name", "=", tag_name)],
                fields=["id"],
                limit=1,
            )
            
            if tags:
                logger.debug(f"Found existing tag '{tag_name}': {tags[0]['id']}")
                return tags[0]["id"]
            
            # Create new tag
            tag_id = await self.client.create("crm.tag", {"name": tag_name, "color": color})
            logger.info(f"Created tag '{tag_name}': {tag_id}")
            return tag_id
            
        except Exception as e:
            logger.warning(f"Failed to ensure tag '{tag_name}': {e}")
            return None
    
    async def add_tag_to_lead(self, lead_id: int, tag_id: int) -> bool:
        """
        Add a tag to a lead using Odoo's Command API.
        
        Args:
            lead_id: CRM lead ID
            tag_id: Tag ID to add
            
        Returns:
            True on success, False on failure
        """
        try:
            await self._ensure_authenticated()
            
            # Use Command.link (4, tag_id, 0) to add tag to Many2many
            await self.client.write("crm.lead", [lead_id], {
                "tag_ids": [(4, tag_id, 0)]  # Command: link
            })
            logger.info(f"Added tag {tag_id} to lead {lead_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to add tag to lead: {e}")
            return False
    
    async def post_chatter_message(
        self,
        lead_id: int,
        body: str,
        subject: str | None = None,
    ) -> int | None:
        """
        Post a message to the lead's chatter (mail.message).
        
        Args:
            lead_id: CRM lead ID
            body: HTML body of the message
            subject: Optional subject
            
        Returns:
            Message ID on success, None on failure
        """
        try:
            await self._ensure_authenticated()
            
            message_values = {
                "model": "crm.lead",
                "res_id": lead_id,
                "body": body,
                "message_type": "notification",
            }
            if subject:
                message_values["subject"] = subject
            
            message_id = await self.client.call(
                "crm.lead",
                "message_post",
                [lead_id],
                body=body,
                subject=subject or "",
                message_type="notification",
            )
            logger.info(f"Posted chatter message to lead {lead_id}: {message_id}")
            return message_id
            
        except Exception as e:
            logger.warning(f"Failed to post chatter message: {e}")
            return None
    
    async def create_activity(
        self,
        lead_id: int,
        user_id: int,
        summary: str,
        note: str = "",
        activity_type_id: int | None = None,
        date_deadline: str | None = None,
    ) -> int | None:
        """
        Create a mail.activity assigned to a user.
        
        Args:
            lead_id: CRM lead ID
            user_id: Odoo user ID to assign
            summary: Activity summary/title
            note: Activity note/description
            activity_type_id: Activity type ID (defaults to "To Do" if None)
            date_deadline: Deadline date (YYYY-MM-DD), defaults to today
            
        Returns:
            Activity ID on success, None on failure
        """
        try:
            await self._ensure_authenticated()
            
            # Get activity type ID if not provided (try to find "To Do")
            if activity_type_id is None:
                try:
                    types = await self.client.search_read(
                        "mail.activity.type",
                        [("name", "ilike", "To Do")],
                        fields=["id"],
                        limit=1,
                    )
                    if types:
                        activity_type_id = types[0]["id"]
                    else:
                        # Fall back to first available type
                        types = await self.client.search_read(
                            "mail.activity.type",
                            [],
                            fields=["id"],
                            limit=1,
                        )
                        if types:
                            activity_type_id = types[0]["id"]
                except Exception:
                    pass
            
            if not activity_type_id:
                logger.warning("No activity type found, skipping activity creation")
                return None
            
            # Default deadline to today
            if not date_deadline:
                date_deadline = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            activity_values = {
                "res_model": "crm.lead",
                "res_model_id": await self._get_model_id("crm.lead"),
                "res_id": lead_id,
                "user_id": user_id,
                "summary": summary,
                "note": note,
                "activity_type_id": activity_type_id,
                "date_deadline": date_deadline,
            }
            
            activity_id = await self.client.create("mail.activity", activity_values)
            logger.info(f"Created activity {activity_id} for user {user_id} on lead {lead_id}")
            return activity_id
            
        except Exception as e:
            logger.warning(f"Failed to create activity: {e}")
            return None
    
    async def _get_model_id(self, model_name: str) -> int | None:
        """Get the ir.model ID for a model name."""
        try:
            models = await self.client.search_read(
                "ir.model",
                [("model", "=", model_name)],
                fields=["id"],
                limit=1,
            )
            return models[0]["id"] if models else None
        except Exception:
            return None
    
    async def _handle_emergency_notifications(
        self,
        lead_id: int,
        emergency_reason: str | None,
        entities: Entity,
        structured_params: dict[str, Any] | None,
    ) -> None:
        """
        Handle emergency-specific Odoo operations:
        1. Add Emergency tag
        2. Post chatter message with details
        3. Create activities for Dispatch/Linda/Tech
        """
        from src.config.settings import get_settings
        import json
        
        settings = get_settings()
        
        # 1. Add Emergency tag
        if settings.FEATURE_ODOO_ACTIVITIES:
            tag_id = await self.ensure_emergency_tag()
            if tag_id:
                await self.add_tag_to_lead(lead_id, tag_id)
        
        # 2. Post chatter message
        tech_name = None
        eta_info = ""
        pricing_info = ""
        
        if structured_params:
            # Try to get tech and pricing from structured params
            if "assigned_technician" in structured_params:
                tech_name = structured_params["assigned_technician"].get("name")
            if "eta_window_hours_min" in structured_params:
                eta_min = structured_params.get("eta_window_hours_min", 1.5)
                eta_max = structured_params.get("eta_window_hours_max", 3.0)
                eta_info = f"<br/><strong>ETA:</strong> {eta_min} - {eta_max} hours"
            if "pricing" in structured_params:
                pricing = structured_params["pricing"]
                if isinstance(pricing, dict):
                    pricing_info = f"<br/><strong>Base Fee:</strong> ${pricing.get('total_base_fee', 0):.2f}"
        
        chatter_body = (
            f'<div style="background:#fee;border-left:4px solid #c00;padding:10px;margin:5px 0;">'
            f'<strong style="color:#c00;">🚨 EMERGENCY SERVICE REQUEST</strong><br/>'
            f'<strong>Reason:</strong> {emergency_reason or "Emergency service needed"}<br/>'
            f'<strong>Customer:</strong> {entities.full_name or "Unknown"}<br/>'
            f'<strong>Phone:</strong> {entities.phone or "Not provided"}<br/>'
            f'<strong>Address:</strong> {entities.address or "Not provided"}'
        )
        if tech_name:
            chatter_body += f'<br/><strong>Assigned Tech:</strong> {tech_name}'
        chatter_body += eta_info
        chatter_body += pricing_info
        chatter_body += '</div>'
        
        await self.post_chatter_message(
            lead_id=lead_id,
            body=chatter_body,
            subject="🚨 Emergency Service Request",
        )
        
        # 3. Create activities (if feature enabled and IDs configured)
        if not settings.FEATURE_ODOO_ACTIVITIES:
            logger.debug("FEATURE_ODOO_ACTIVITIES disabled, skipping activity creation")
            return
        
        activity_summary = f"🚨 EMERGENCY: {entities.problem_description or 'Service needed'}"
        activity_note = (
            f"Emergency service request from {entities.full_name or 'caller'}.\n"
            f"Reason: {emergency_reason or 'Emergency service needed'}\n"
            f"Phone: {entities.phone or 'Not provided'}\n"
            f"Address: {entities.address or 'Not provided'}"
        )
        
        user_ids_to_notify = []
        
        # Dispatch user
        if settings.ODOO_DISPATCH_USER_ID and settings.ODOO_DISPATCH_USER_ID > 0:
            user_ids_to_notify.append(("Dispatch", settings.ODOO_DISPATCH_USER_ID))
        
        # Linda user
        if settings.ODOO_LINDA_USER_ID and settings.ODOO_LINDA_USER_ID > 0:
            user_ids_to_notify.append(("Linda", settings.ODOO_LINDA_USER_ID))
        
        # Assigned tech user
        if settings.ODOO_TECH_USER_IDS_JSON:
            try:
                tech_user_ids = json.loads(settings.ODOO_TECH_USER_IDS_JSON)
                if tech_name and tech_name.lower() in tech_user_ids:
                    user_ids_to_notify.append((tech_name, tech_user_ids[tech_name.lower()]))
            except json.JSONDecodeError:
                logger.warning("Failed to parse ODOO_TECH_USER_IDS_JSON")
        
        for name, user_id in user_ids_to_notify:
            await self.create_activity(
                lead_id=lead_id,
                user_id=user_id,
                summary=activity_summary,
                note=f"[{name}] {activity_note}",
            )
            logger.info(f"Created activity for {name} (user {user_id}) on lead {lead_id}")
    
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
        channel: str | None = None,  # "voice" or "chat"
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
            
            # Set lead source based on channel
            if channel == "chat":
                source_name = "Website Chat"
            else:
                source_name = "AI Voice Agent"  # Default for voice
            
            source_id = await self.ensure_lead_source(source_name)
            if source_id:
                # Try both source_id and source fields
                if "source_id" in valid_fields:
                    lead_values["source_id"] = source_id
                elif "source" in valid_fields:
                    # If source is a char field, set the name
                    sources = await self.client.search_read(
                        "utm.source",
                        [("id", "=", source_id)],
                        fields=["name"],
                        limit=1,
                    )
                    if sources:
                        lead_values["source"] = sources[0]["name"]
            
            # Map property_type to customer type and pricing tier
            property_type = (entities.property_type or "").lower()
            customer_type = None
            pricing_tier = None
            tags_to_add = []
            
            if property_type == "residential":
                customer_type = "Retail"
                pricing_tier = "Retail Pricing"
                tags_to_add.append("Residential")
            elif property_type == "commercial":
                customer_type = "Commercial"
                pricing_tier = "Com Pricing"
                tags_to_add.append("Commercial")
            elif property_type in ["property_management", "property management", "pm"]:
                customer_type = "Property Management"
                pricing_tier = "Default-PM Pricing"
                tags_to_add.append("Property Management")
                
                # Extract PM company name from metadata or description
                pm_company_name = None
                if structured_params and "pm_company_name" in structured_params:
                    pm_company_name = structured_params["pm_company_name"]
                elif structured_params and "property_management_company" in structured_params:
                    pm_company_name = structured_params["property_management_company"]
                
                # Add PM company name to description if available
                if pm_company_name:
                    desc_html.insert(-1, f'<tr><td style="padding:3px;">PM Company:</td><td style="padding:3px;">{pm_company_name}</td></tr>')
                    description = "".join(desc_html)
                    lead_values["description"] = description
                    
                    # Check if Lessen and set tax-exempt flag
                    if "lessen" in pm_company_name.lower():
                        # Try to set tax-exempt flag (may be on partner or lead)
                        if "is_tax_exempt" in valid_fields:
                            lead_values["is_tax_exempt"] = True
                        elif "tax_exempt" in valid_fields:
                            lead_values["tax_exempt"] = True
                        tags_to_add.append("Tax Exempt")
                
                # Set payment terms to Net 30 for PM customers
                # Try common field names for payment terms
                for field_name in ["payment_term_id", "payment_terms_id", "payment_terms"]:
                    if field_name in valid_fields:
                        try:
                            # Search for Net 30 payment term
                            payment_terms = await self.client.search_read(
                                "account.payment.term",
                                [("name", "ilike", "Net 30")],
                                fields=["id"],
                                limit=1,
                            )
                            if payment_terms:
                                lead_values[field_name] = payment_terms[0]["id"]
                                break
                        except Exception:
                            pass
                
                # Add payment terms note to description
                desc_html.insert(-1, f'<tr><td style="padding:3px;">Payment Terms:</td><td style="padding:3px;">Net 30</td></tr>')
                description = "".join(desc_html)
                lead_values["description"] = description
            
            # Set customer type if field exists
            if customer_type:
                # Try common field names for customer type
                for field_name in ["customer_type", "type_id", "category_id"]:
                    if field_name in valid_fields:
                        # Try to find or create category
                        try:
                            categories = await self.client.search_read(
                                "res.partner.category",
                                [("name", "=", customer_type)],
                                fields=["id"],
                                limit=1,
                            )
                            if categories:
                                if field_name == "category_id":
                                    lead_values[field_name] = [(6, 0, [categories[0]["id"]])]
                                else:
                                    lead_values[field_name] = categories[0]["id"]
                                break
                        except Exception:
                            pass
            
            # Add pricing tier to description if available
            if pricing_tier:
                desc_html.insert(-1, f'<tr><td style="padding:3px;">Pricing Tier:</td><td style="padding:3px;">{pricing_tier}</td></tr>')
                description = "".join(desc_html)
                lead_values["description"] = description
            
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
                action = "updated"
            else:
                # Create new lead
                lead_id = await self.client.create("crm.lead", lead_values)
                logger.info(f"Created new lead: {lead_id}")
                action = "created"
            
            # ---------------------------------------------------------------------
            # Emergency handling: tag + chatter + activities
            # ---------------------------------------------------------------------
            if is_emergency and lead_id:
                await self._handle_emergency_notifications(
                    lead_id=lead_id,
                    emergency_reason=emergency_reason,
                    entities=entities,
                    structured_params=structured_params,
                )
            
            # ---------------------------------------------------------------------
            # Apply tags based on customer type and service type
            # ---------------------------------------------------------------------
            if lead_id and tags_to_add:
                for tag_name in tags_to_add:
                    tag_id = await self.ensure_tag(tag_name)
                    if tag_id:
                        await self.add_tag_to_lead(lead_id, tag_id)
            
            # Add service type tag if available
            if lead_id and structured_params and "service_type" in structured_params:
                service_type = structured_params["service_type"]
                if isinstance(service_type, str):
                    service_tag_id = await self.ensure_tag(service_type)
                    if service_tag_id:
                        await self.add_tag_to_lead(lead_id, service_tag_id)
            
            return {
                "lead_id": lead_id,
                "action": action,
                "status": "success",
                "partner_id": partner_id,
                "customer_type": customer_type,
                "pricing_tier": pricing_tier,
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
    channel: str | None = None,  # "voice" or "chat"
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
            channel=channel,
        )
        return result
    finally:
        await client.close()
