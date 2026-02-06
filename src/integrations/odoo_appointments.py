"""
HAES HVAC - Odoo Appointment/Calendar Integration

Creates and manages calendar events in Odoo for appointment scheduling.
Follows the same pattern as odoo_leads.py for consistency.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from src.brains.ops.scheduling_rules import TimeSlot, SlotStatus
from src.config.settings import get_settings
from src.integrations.odoo import OdooClient, create_odoo_client_from_settings
from src.utils.errors import OdooRPCError, OdooTransportError

logger = logging.getLogger(__name__)

# Fields we commonly write to calendar.event
CALENDAR_EVENT_FIELDS = [
    "name",
    "start",
    "stop",
    "start_date",
    "stop_date",
    "start_datetime",
    "stop_datetime",
    "duration",
    "allday",
    "partner_ids",
    "user_id",
    "description",
    "location",
    "res_id",
    "res_model",
    "active",
]


class AppointmentService:
    """
    Service for managing calendar appointments in Odoo.
    
    Handles:
    - Calendar event creation/update/cancel
    - Appointment lookup by contact
    - Technician availability checking
    - CRM lead linking
    - Scheduling rules integration
    """
    
    def __init__(self, client: OdooClient):
        self.client = client
        self._calendar_event_fields: set[str] | None = None
        self._partner_fields: set[str] | None = None
    
    async def _ensure_authenticated(self) -> None:
        """Ensure the client is authenticated."""
        if not self.client.is_authenticated:
            await self.client.authenticate()
    
    async def _get_calendar_event_fields(self) -> set[str]:
        """
        Get available fields for calendar.event model.
        Caches result for performance.
        """
        if self._calendar_event_fields is None:
            try:
                await self._ensure_authenticated()
                fields_info = await self.client.fields_get("calendar.event")
                self._calendar_event_fields = set(fields_info.keys())
                logger.debug(f"Cached {len(self._calendar_event_fields)} calendar.event fields")
            except Exception as e:
                logger.warning(f"Failed to get calendar.event fields: {e}")
                # Fall back to commonly available fields
                self._calendar_event_fields = set(CALENDAR_EVENT_FIELDS)
        return self._calendar_event_fields
    
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
    
    def _get_tech_user_id(self, tech_id: str) -> int | None:
        """
        Get Odoo user ID for a technician.
        
        Args:
            tech_id: Technician ID (e.g., "junior", "bounthon")
            
        Returns:
            Odoo user ID if found, None otherwise
        """
        settings = get_settings()
        try:
            tech_user_map = json.loads(settings.ODOO_TECH_USER_IDS_JSON)
            user_id = tech_user_map.get(tech_id.lower())
            return int(user_id) if user_id else None
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Failed to parse ODOO_TECH_USER_IDS_JSON: {e}")
            return None
    
    async def find_appointment_by_contact(
        self,
        phone: str | None = None,
        email: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find appointments by customer contact info.
        
        Args:
            phone: Phone number
            email: Email address
            date_from: Start date filter (optional)
            date_to: End date filter (optional)
            
        Returns:
            List of appointment records matching the criteria
        """
        try:
            await self._ensure_authenticated()
            
            domain = [("active", "=", True)]
            
            # Build partner search domain
            partner_domain = []
            if phone:
                # Normalize phone: remove all non-digits, then use last 10 digits
                clean_phone = re.sub(r"[^\d]", "", phone)  # Remove all non-digits (including +)
                if clean_phone:
                    # Use last 10 digits for matching (US numbers, or last 10 of international)
                    phone_suffix = clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone
                    # Search for phone containing these last 10 digits (handles +1, country codes, etc.)
                    partner_domain.append(("phone", "ilike", f"%{phone_suffix}"))
                    logger.info(f"Searching for partner with phone suffix: {phone_suffix} (from {phone})")
            if email:
                partner_domain.append(("email", "=ilike", email))
            
            # If we have contact info, find partners first
            partner_ids = []
            if partner_domain:
                partners = await self.client.search(
                    "res.partner",
                    partner_domain,
                    limit=10,
                )
                partner_ids = partners
                logger.info(f"Found {len(partner_ids)} partner(s) matching contact info (phone={bool(phone)}, email={bool(email)})")
                if partner_ids:
                    domain.append(("partner_ids", "in", partner_ids))
                else:
                    # No partners found, return empty
                    logger.warning(f"No partners found for phone={phone}, email={email}")
                    return []
            
            # Add date filters
            if date_from:
                domain.append(("start", ">=", date_from.strftime("%Y-%m-%d %H:%M:%S")))
            if date_to:
                domain.append(("start", "<=", date_to.strftime("%Y-%m-%d %H:%M:%S")))
            
            # Search calendar events
            events = await self.client.search_read(
                "calendar.event",
                domain,
                fields=["id", "name", "start", "stop", "partner_ids", "user_id", "location", "res_id", "res_model"],
                limit=50,
                order="start desc",
            )
            
            logger.info(f"Found {len(events)} appointments for contact (phone={bool(phone)}, email={bool(email)})")
            return events
            
        except Exception as e:
            logger.error(f"Failed to find appointments by contact: {e}")
            return []
    
    async def get_technician_calendar_events(
        self,
        tech_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get calendar events for a specific technician.
        
        Args:
            tech_id: Technician ID (e.g., "junior")
            date_from: Start date filter (optional, defaults to now)
            date_to: End date filter (optional, defaults to 30 days from now)
            
        Returns:
            List of calendar event records
        """
        try:
            await self._ensure_authenticated()
            
            user_id = self._get_tech_user_id(tech_id)
            if not user_id:
                logger.warning(f"No Odoo user ID found for technician {tech_id}")
                return []
            
            # Default date range: now to 30 days ahead
            if date_from is None:
                date_from = datetime.now(timezone.utc).replace(tzinfo=None)
            if date_to is None:
                date_to = date_from + timedelta(days=30)
            
            domain = [
                ("user_id", "=", user_id),
                ("active", "=", True),
                ("start", ">=", date_from.strftime("%Y-%m-%d %H:%M:%S")),
                ("start", "<=", date_to.strftime("%Y-%m-%d %H:%M:%S")),
            ]
            
            events = await self.client.search_read(
                "calendar.event",
                domain,
                fields=["id", "name", "start", "stop", "duration"],
                order="start asc",
            )
            
            logger.debug(f"Found {len(events)} calendar events for technician {tech_id} (user_id={user_id})")
            return events
            
        except Exception as e:
            logger.error(f"Failed to get technician calendar events: {e}")
            return []
    
    async def get_technician_availability(
        self,
        tech_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[TimeSlot]:
        """
        Get technician availability as TimeSlot objects.
        
        Fetches calendar events from Odoo and converts to TimeSlot format
        for use with scheduling_rules.py.
        
        Args:
            tech_id: Technician ID
            date_from: Start date
            date_to: End date
            
        Returns:
            List of TimeSlot objects representing booked time
        """
        events = await self.get_technician_calendar_events(tech_id, date_from, date_to)
        
        slots = []
        for event in events:
            try:
                # Parse start/stop times
                start_str = event.get("start")
                stop_str = event.get("stop")
                
                if not start_str or not stop_str:
                    continue
                
                # Handle datetime format (with or without timezone)
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                stop_dt = datetime.fromisoformat(stop_str.replace("Z", "+00:00"))
                
                # Convert to naive datetime (Odoo stores in UTC but returns without tzinfo)
                if start_dt.tzinfo:
                    start_dt = start_dt.replace(tzinfo=None)
                if stop_dt.tzinfo:
                    stop_dt = stop_dt.replace(tzinfo=None)
                
                slots.append(TimeSlot(
                    start=start_dt,
                    end=stop_dt,
                    status=SlotStatus.BOOKED,
                    technician_id=tech_id,
                    job_id=str(event.get("id")),
                ))
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse calendar event {event.get('id')}: {e}")
                continue
        
        return slots
    
    async def create_appointment(
        self,
        name: str,
        start: datetime,
        stop: datetime,
        partner_id: int | None = None,
        partner_ids: list[int] | None = None,
        tech_id: str | None = None,
        description: str | None = None,
        location: str | None = None,
        lead_id: int | None = None,
    ) -> int | None:
        """
        Create a calendar event in Odoo.
        
        Args:
            name: Event name/title
            start: Start datetime (will be converted to UTC)
            stop: End datetime (will be converted to UTC)
            partner_id: Single partner ID (customer)
            partner_ids: List of partner IDs (alternative to partner_id)
            tech_id: Technician ID (e.g., "junior")
            description: Event description
            location: Event location (address)
            lead_id: Optional CRM lead ID to link
            
        Returns:
            Calendar event ID if created, None on failure
        """
        try:
            await self._ensure_authenticated()
            valid_fields = await self._get_calendar_event_fields()
            
            # Convert datetime to UTC string format for Odoo
            # Odoo expects datetime strings in format "YYYY-MM-DD HH:MM:SS"
            # If datetime is timezone-aware, convert to UTC; if naive, assume UTC
            if start.tzinfo:
                start_utc = start.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                start_utc = start
            
            if stop.tzinfo:
                stop_utc = stop.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                stop_utc = stop
            
            start_str = start_utc.strftime("%Y-%m-%d %H:%M:%S")
            stop_str = stop_utc.strftime("%Y-%m-%d %H:%M:%S")
            
            # Build partner_ids list
            final_partner_ids = []
            if partner_ids:
                final_partner_ids = partner_ids
            elif partner_id:
                final_partner_ids = [partner_id]
            
            # Get technician user_id
            user_id = None
            if tech_id:
                user_id = self._get_tech_user_id(tech_id)
                if not user_id:
                    logger.warning(f"No Odoo user ID found for technician {tech_id}")
            
            # Build event values
            event_values: dict[str, Any] = {
                "name": name,
                "start": start_str,
                "stop": stop_str,
                "allday": False,
            }
            
            if final_partner_ids:
                event_values["partner_ids"] = [(6, 0, final_partner_ids)]  # Odoo Command: replace
            if user_id:
                event_values["user_id"] = user_id
            if description:
                event_values["description"] = description
            if location:
                event_values["location"] = location
            
            # Link to CRM lead if provided
            if lead_id:
                event_values["res_model"] = "crm.lead"
                event_values["res_id"] = lead_id
            
            # Set status to "Scheduled" if Field Service module status field exists
            # Field Service module may have a custom status field
            if "state" in valid_fields:
                # Try common status values for Field Service
                event_values["state"] = "scheduled"
            elif "status" in valid_fields:
                event_values["status"] = "scheduled"
            elif "x_status" in valid_fields:
                # Custom field naming convention
                event_values["x_status"] = "scheduled"
            
            # Filter to valid fields only
            event_values = self._filter_valid_fields(event_values, valid_fields)
            
            # Create the event
            event_id = await self.client.create("calendar.event", event_values)
            logger.info(f"Created calendar event {event_id}: {name} ({start_str} - {stop_str})")
            
            # Try to set status after creation if it wasn't set during creation
            # (Some Odoo modules require status to be set via write after creation)
            if "state" in valid_fields and "state" not in event_values:
                try:
                    await self.client.write("calendar.event", [event_id], {"state": "scheduled"})
                    logger.debug(f"Set status to 'scheduled' for calendar event {event_id}")
                except Exception as e:
                    logger.debug(f"Could not set status field (may not exist in this Odoo instance): {e}")
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to create appointment: {e}")
            return None
    
    async def update_appointment(
        self,
        event_id: int,
        name: str | None = None,
        start: datetime | None = None,
        stop: datetime | None = None,
        tech_id: str | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> bool:
        """
        Update an existing calendar event.
        
        Args:
            event_id: Calendar event ID
            name: New event name (optional)
            start: New start datetime (optional)
            stop: New end datetime (optional)
            tech_id: New technician ID (optional)
            description: New description (optional)
            location: New location (optional)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            await self._ensure_authenticated()
            valid_fields = await self._get_calendar_event_fields()
            
            update_values: dict[str, Any] = {}
            
            if name is not None:
                update_values["name"] = name
            if start is not None:
                if start.tzinfo:
                    start_utc = start.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    start_utc = start
                update_values["start"] = start_utc.strftime("%Y-%m-%d %H:%M:%S")
            if stop is not None:
                if stop.tzinfo:
                    stop_utc = stop.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    stop_utc = stop
                update_values["stop"] = stop_utc.strftime("%Y-%m-%d %H:%M:%S")
            if tech_id is not None:
                user_id = self._get_tech_user_id(tech_id)
                if user_id:
                    update_values["user_id"] = user_id
            if description is not None:
                update_values["description"] = description
            if location is not None:
                update_values["location"] = location
            
            if not update_values:
                logger.warning(f"No fields to update for event {event_id}")
                return True  # Nothing to update, consider success
            
            # Filter to valid fields
            update_values = self._filter_valid_fields(update_values, valid_fields)
            
            # Update the event
            await self.client.write("calendar.event", [event_id], update_values)
            logger.info(f"Updated calendar event {event_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update appointment {event_id}: {e}")
            return False
    
    async def cancel_appointment(self, event_id: int) -> bool:
        """
        Cancel a calendar event by setting active=False.
        
        Args:
            event_id: Calendar event ID
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            await self._ensure_authenticated()
            valid_fields = await self._get_calendar_event_fields()
            
            # Check if active field exists
            if "active" not in valid_fields:
                # If active field doesn't exist, we can't cancel this way
                # Option: delete the event (uncomment if preferred)
                # await self.client.unlink("calendar.event", [event_id])
                logger.warning(f"Cannot cancel event {event_id}: 'active' field not available")
                return False
            
            # Set active=False (soft delete)
            await self.client.write("calendar.event", [event_id], {"active": False})
            logger.info(f"Cancelled calendar event {event_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel appointment {event_id}: {e}")
            return False
    
    async def link_appointment_to_lead(
        self,
        event_id: int,
        lead_id: int,
    ) -> bool:
        """
        Link a calendar event to a CRM lead.
        
        Args:
            event_id: Calendar event ID
            lead_id: CRM lead ID
            
        Returns:
            True if linked successfully, False otherwise
        """
        try:
            await self._ensure_authenticated()
            valid_fields = await self._get_calendar_event_fields()
            
            update_values: dict[str, Any] = {
                "res_model": "crm.lead",
                "res_id": lead_id,
            }
            
            # Filter to valid fields
            update_values = self._filter_valid_fields(update_values, valid_fields)
            
            if "res_model" not in update_values or "res_id" not in update_values:
                logger.warning(f"Cannot link event {event_id} to lead {lead_id}: fields not available")
                return False
            
            await self.client.write("calendar.event", [event_id], update_values)
            logger.info(f"Linked calendar event {event_id} to CRM lead {lead_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to link appointment {event_id} to lead {lead_id}: {e}")
            return False
    
    async def find_next_available_slot(
        self,
        tech_id: str,
        after: datetime,
        duration_minutes: int,
    ) -> TimeSlot | None:
        """
        Find the next available slot for a technician using scheduling rules.
        
        Args:
            tech_id: Technician ID
            after: Find slots after this time
            duration_minutes: Required duration
            
        Returns:
            TimeSlot if found, None otherwise
        """
        from src.brains.ops.scheduling_rules import get_next_available_slot
        
        # Get existing bookings from Odoo
        existing_bookings = await self.get_technician_availability(tech_id, after, after + timedelta(days=30))
        
        # Use scheduling rules to find next slot
        return get_next_available_slot(after, duration_minutes, tech_id, existing_bookings)

    async def find_next_two_available_slots(
        self,
        tech_id: str,
        after: datetime,
        duration_minutes: int,
    ) -> list[TimeSlot]:
        """
        Find the next two distinct available slots for a technician.
        Used to offer the customer two time options (e.g. "Tuesday 10 AM or Wednesday 2 PM").

        Returns:
            List of 0, 1, or 2 TimeSlots.
        """
        from src.brains.ops.scheduling_rules import get_next_two_available_slots

        existing_bookings = await self.get_technician_availability(
            tech_id, after, after + timedelta(days=30)
        )
        return get_next_two_available_slots(
            after, duration_minutes, tech_id, existing_bookings
        )

    async def validate_slot_availability(
        self,
        requested_start: datetime,
        duration_minutes: int,
        tech_id: str | None = None,
    ) -> tuple[bool, str, list[TimeSlot]]:
        """
        Validate a slot is available for scheduling.
        
        Args:
            requested_start: Requested start time
            duration_minutes: Required duration
            tech_id: Technician ID (optional)
            
        Returns:
            Tuple of (is_valid, reason, alternatives)
        """
        from src.brains.ops.scheduling_rules import validate_scheduling_request
        
        # Get existing bookings if tech specified
        existing_bookings = []
        if tech_id:
            existing_bookings = await self.get_technician_availability(
                tech_id,
                requested_start - timedelta(days=1),
                requested_start + timedelta(days=1),
            )
        
        # Validate using scheduling rules
        result = validate_scheduling_request(requested_start, duration_minutes, tech_id, existing_bookings)
        
        return result.success, result.reason, result.alternatives


async def create_appointment_service() -> AppointmentService:
    """
    Create an AppointmentService instance from settings.
    
    Returns:
        Configured AppointmentService (client not yet authenticated)
    """
    client = create_odoo_client_from_settings()
    return AppointmentService(client)
