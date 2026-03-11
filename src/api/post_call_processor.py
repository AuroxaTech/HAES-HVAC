"""
HAES HVAC - Post-Call Processor

Processes VAPI structured outputs from end-of-call reports.
ALL write operations (booking, reschedule, cancel, service request, quote,
complaint, invoice, membership) happen here — not during the call.

Notifications (SMS + email) are sent automatically after each action.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from src.hael.schema import (
    Channel,
    Entity,
    HaelCommand,
    Intent,
    Brain,
    UrgencyLevel,
)
from src.brains.ops import handle_ops_command
from src.brains.ops.schema import OpsStatus
from src.utils.request_id import generate_request_id
from src.vapi.tools.base import BaseToolHandler

logger = logging.getLogger(__name__)

# Log prefix for easy grep in server logs (e.g. fly logs | grep PostCallProcessor)
_PREFIX = "[PostCallProcessor]"

def _mask_phone(phone: str | None) -> str:
    """Last 4 digits only for log validation without PII."""
    if not phone or len(phone) < 4:
        return "***"
    return f"***{phone.strip()[-4:]}"

# Map string urgency to enum
_URGENCY_MAP = {
    "emergency": UrgencyLevel.EMERGENCY,
    "urgent": UrgencyLevel.HIGH,
    "routine": UrgencyLevel.MEDIUM,
    "low": UrgencyLevel.LOW,
}


def _webhook_caller_number(payload: dict) -> str | None:
    """Extract caller number from end-of-call-report webhook (message.call.customer.number or message.call.from)."""
    call_data = (payload or {}).get("message", {}).get("call", {})
    return (
        call_data.get("customer", {}).get("number")
        or call_data.get("from")
    ) or None


class PostCallProcessor:
    """Processes structured outputs from VAPI end-of-call reports."""

    def __init__(self):
        self._handler = BaseToolHandler("post_call_processor")
        self._fallback_phone: str | None = None  # webhook caller number for SMS fallback

    # ── Public entry point ───────────────────────────────────────────

    async def process(
        self, call_id: str, payload: dict, *, recording_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Main entry — called from the end-of-call webhook handler.

        Args:
            call_id: VAPI call ID
            payload: Full end-of-call-report webhook payload
            recording_url: Optional VAPI call recording URL

        Returns:
            Summary dict of actions taken
        """
        self._recording_url = recording_url
        structured_outputs = self._extract_structured_outputs(payload)
        if not structured_outputs:
            logger.info("%s call_id=%s no structured outputs — skipping", _PREFIX, call_id)
            return {"actions": [], "skipped": True}

        output_names = list(structured_outputs.keys())
        logger.info(
            "%s call_id=%s structured_outputs_received=%s",
            _PREFIX, call_id, output_names,
        )

        # Ensure we always have dicts (defensive against unexpected VAPI shape)
        customer = structured_outputs.get("Customer Profile") or {}
        appointment = structured_outputs.get("Appointment Action") or {}
        pending = structured_outputs.get("Pending Request") or {}
        analytics = structured_outputs.get("Call Analytics") or {}
        if not isinstance(customer, dict):
            customer = {}
        if not isinstance(appointment, dict):
            appointment = {}
        if not isinstance(pending, dict):
            pending = {}
        if not isinstance(analytics, dict):
            analytics = {}

        # Normalize customer phone; use webhook caller number when missing or placeholder
        raw_phone = customer.get("phone")
        webhook_caller = _webhook_caller_number(payload)
        fallback_phone = self._handler.normalize_phone(webhook_caller) if webhook_caller else None
        self._fallback_phone = fallback_phone

        phone = self._handler.normalize_phone(raw_phone)
        if not phone or (isinstance(raw_phone, str) and "{{" in raw_phone):
            phone = fallback_phone
            if fallback_phone:
                logger.info(
                    "%s call_id=%s using webhook caller number for phone (structured output missing or placeholder)",
                    _PREFIX, call_id,
                )
        email = self._handler.normalize_email(customer.get("email"))

        logger.info(
            "%s call_id=%s Customer_Profile name=%s %s phone=%s has_email=%s",
            _PREFIX, call_id,
            customer.get("firstName"), customer.get("lastName"),
            _mask_phone(phone), bool(email),
        )
        logger.info(
            "%s call_id=%s Appointment_Action action=%s urgency=%s isEmergency=%s chosenSlotStart=%s existingAppointmentId=%s",
            _PREFIX, call_id,
            appointment.get("action"), appointment.get("urgency"),
            appointment.get("isEmergency"), appointment.get("chosenSlotStart"),
            appointment.get("existingAppointmentId"),
        )
        logger.info(
            "%s call_id=%s Pending_Request requestType=%s",
            _PREFIX, call_id, pending.get("requestType"),
        )
        logger.info(
            "%s call_id=%s Call_Analytics followUpRequired=%s primaryIntent=%s followUpReason=%s",
            _PREFIX, call_id,
            analytics.get("followUpRequired"), analytics.get("primaryIntent"),
            (analytics.get("followUpReason") or "")[:80],
        )

        results: list[dict[str, Any]] = []

        # Process in priority order — emergencies first
        is_emergency = appointment.get("isEmergency", False)
        urgency_str = (appointment.get("urgency") or "routine").lower()

        # 1. Appointment actions (book / reschedule / cancel)
        action = (appointment.get("action") or "none").lower()
        if action not in ("book", "reschedule", "cancel"):
            logger.info(
                "%s call_id=%s appointment action=%s (skipped, no appointment action)",
                _PREFIX, call_id, action,
            )
        if action == "book":
            logger.info("%s call_id=%s processing action=book_appointment", _PREFIX, call_id)
            result = await self._book_appointment(
                call_id, customer, appointment, phone, email, urgency_str, is_emergency,
                analytics=analytics,
            )
            logger.info(
                "%s call_id=%s result action=book_appointment success=%s appointment_id=%s lead_id=%s error=%s",
                _PREFIX, call_id,
                result.get("success"), result.get("appointment_id"), result.get("lead_id"),
                result.get("error"),
            )
            results.append({"action": "book_appointment", **result})
        elif action == "reschedule":
            logger.info("%s call_id=%s processing action=reschedule_appointment", _PREFIX, call_id)
            result = await self._reschedule_appointment(
                call_id, customer, appointment, phone, email,
                analytics=analytics,
            )
            logger.info(
                "%s call_id=%s result action=reschedule_appointment success=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("error"),
            )
            results.append({"action": "reschedule_appointment", **result})
        elif action == "cancel":
            logger.info("%s call_id=%s processing action=cancel_appointment", _PREFIX, call_id)
            result = await self._cancel_appointment(
                call_id, customer, appointment, phone, email,
                analytics=analytics,
            )
            logger.info(
                "%s call_id=%s result action=cancel_appointment success=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("error"),
            )
            results.append({"action": "cancel_appointment", **result})

        # 2. Pending requests (quote, complaint, invoice, membership, service request)
        request_type = (pending.get("requestType") or "none").lower()
        if request_type not in ("quote", "complaint", "invoice", "membership", "service_request"):
            logger.info(
                "%s call_id=%s pending requestType=%s (skipped, no pending request)",
                _PREFIX, call_id, request_type,
            )
        if request_type == "quote":
            logger.info("%s call_id=%s processing action=create_quote", _PREFIX, call_id)
            result = await self._create_quote(
                call_id, customer, pending.get("quoteRequest", {}), phone, email,
                analytics=analytics,
            )
            logger.info(
                "%s call_id=%s result action=create_quote success=%s lead_id=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("lead_id"), result.get("error"),
            )
            results.append({"action": "create_quote", **result})
        elif request_type == "complaint":
            logger.info("%s call_id=%s processing action=handle_complaint", _PREFIX, call_id)
            result = await self._handle_complaint(
                call_id, customer, pending.get("complaint", {}), phone, email,
                analytics=analytics,
            )
            logger.info(
                "%s call_id=%s result action=handle_complaint success=%s lead_id=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("lead_id"), result.get("error"),
            )
            results.append({"action": "handle_complaint", **result})
        elif request_type == "invoice":
            logger.info("%s call_id=%s processing action=send_invoice", _PREFIX, call_id)
            result = await self._send_invoice(
                call_id, customer, pending.get("invoiceRequest", {}), phone, email,
            )
            logger.info(
                "%s call_id=%s result action=send_invoice success=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("error"),
            )
            results.append({"action": "send_invoice", **result})
        elif request_type == "membership":
            logger.info("%s call_id=%s processing action=enroll_membership", _PREFIX, call_id)
            result = await self._enroll_membership(
                call_id, customer, pending.get("membershipEnrollment", {}), phone, email,
            )
            logger.info(
                "%s call_id=%s result action=enroll_membership success=%s lead_id=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("lead_id"), result.get("error"),
            )
            results.append({"action": "enroll_membership", **result})
        elif request_type == "service_request":
            logger.info("%s call_id=%s processing action=create_service_request", _PREFIX, call_id)
            result = await self._create_service_request(
                call_id, customer, pending.get("serviceRequest", {}),
                phone, email, urgency_str, is_emergency,
                analytics=analytics,
            )
            logger.info(
                "%s call_id=%s result action=create_service_request success=%s lead_id=%s error=%s",
                _PREFIX, call_id, result.get("success"), result.get("lead_id"), result.get("error"),
            )
            results.append({"action": "create_service_request", **result})

        # 3. Create follow-up activity if needed
        if analytics.get("followUpRequired"):
            logger.info(
                "%s call_id=%s processing follow_up reason=%s",
                _PREFIX, call_id, (analytics.get("followUpReason") or "")[:100],
            )
            await self._create_follow_up(call_id, customer, analytics, phone)
            logger.info("%s call_id=%s follow_up completed", _PREFIX, call_id)

        # 4. Upload call recording to CRM lead (fire-and-forget)
        if self._recording_url:
            lead_id = next(
                (r.get("lead_id") for r in results if r.get("lead_id")),
                None,
            )
            if lead_id:
                from src.integrations.odoo_attachments import upload_recording_to_odoo

                asyncio.create_task(
                    upload_recording_to_odoo(
                        self._recording_url, "crm.lead", lead_id, call_id,
                    )
                )
                logger.info(
                    "%s call_id=%s queued recording upload to crm.lead %s",
                    _PREFIX, call_id, lead_id,
                )

        action_names = [r.get("action", "") for r in results]
        logger.info(
            "%s call_id=%s complete actions_count=%s actions=%s",
            _PREFIX, call_id, len(results), action_names,
        )
        return {"actions": results, "skipped": False}

    # ── Structured output extraction ─────────────────────────────────

    def _extract_structured_outputs(self, payload: dict) -> dict[str, Any]:
        """Parse structured outputs from VAPI end-of-call payload.

        VAPI may send structuredOutputs as either:
        - A list of {name, result} objects, or
        - A dict keyed by UUID with {name, result} values.
        """
        message = payload.get("message", payload)
        artifact = message.get("artifact", {})
        raw = artifact.get("structuredOutputs") or []

        # Normalize to list of output objects (VAPI sometimes sends dict keyed by UUID)
        if isinstance(raw, dict):
            raw_outputs = list(raw.values())
        elif isinstance(raw, list):
            raw_outputs = raw
        else:
            raw_outputs = []

        if not raw_outputs:
            return {}

        raw_names = [
            o.get("name", "") for o in raw_outputs
            if isinstance(o, dict)
        ]
        logger.info(
            "%s raw structuredOutputs from VAPI: names=%s count=%s",
            _PREFIX, raw_names, len(raw_outputs),
        )

        # Map each output by its name; only store result if it's a dict
        parsed = {}
        for output in raw_outputs:
            if not isinstance(output, dict):
                continue
            name = output.get("name", "")
            result = output.get("result", {})
            if name and isinstance(result, dict):
                parsed[name] = result

        return parsed

    # ── Booking ──────────────────────────────────────────────────────

    async def _book_appointment(
        self,
        call_id: str,
        customer: dict,
        appointment: dict,
        phone: str | None,
        email: str | None,
        urgency_str: str,
        is_emergency: bool,
        analytics: dict | None = None,
    ) -> dict[str, Any]:
        """Create appointment in Odoo via OPS brain handler."""
        try:
            entities = self._build_entity(customer, appointment, phone, email)
            urgency = _URGENCY_MAP.get(urgency_str, UrgencyLevel.MEDIUM)

            caller_type = customer.get("callerType")
            mgmt_company = customer.get("managementCompany")
            call_summary = (analytics or {}).get("callSummary") if analytics else None
            if call_summary and not isinstance(call_summary, str):
                call_summary = str(call_summary).strip() or None
            elif call_summary:
                call_summary = call_summary.strip() or None

            command = HaelCommand(
                request_id=generate_request_id(),
                channel=Channel.VOICE,
                raw_text=appointment.get("problemDescription", ""),
                intent=Intent.SCHEDULE_APPOINTMENT,
                brain=Brain.OPS,
                entities=entities,
                confidence=0.9,
                requires_human=False,
                missing_fields=[],
                idempotency_key="",
                metadata={
                    "call_id": call_id,
                    "chosen_slot_start": appointment.get("chosenSlotStart"),
                    "chosen_slot_technician_id": appointment.get("chosenSlotTechnicianId"),
                    "urgency": urgency_str,
                    "technician_notes": appointment.get("technicianNotes"),
                    "caller_type": caller_type,
                    "property_management_company": mgmt_company,
                    "is_warranty": appointment.get("isWarranty", False),
                    "previous_service_id": appointment.get("previousServiceId"),
                    "referral_source": customer.get("leadSource"),
                    "confirmed_partner_id": customer.get("confirmedPartnerId"),
                    "call_summary": call_summary,
                },
            )

            result = await handle_ops_command(command)

            if result.status == OpsStatus.ERROR:
                logger.error("Booking failed for call %s: %s", call_id, result.message)
                # Try next closest slot
                fallback = await self._try_next_slot(
                    call_id, entities, appointment, urgency_str,
                )
                if fallback:
                    result = fallback["result"]
                    appointment["chosenSlotStart"] = fallback["new_slot_start"]
                else:
                    return {"success": False, "error": result.message}

            # Schedule reminder
            self._schedule_reminder(result, phone, customer)

            # Create lead
            lead_id = await self._create_lead_for_booking(
                call_id, entities, urgency, is_emergency, appointment, customer,
            )

            # Send confirmation notification
            await self._send_confirmation(
                phone, email,
                f"Your appointment is confirmed for {appointment.get('appointmentWindow', 'your scheduled time')}. "
                f"A technician will arrive during that window.",
                customer.get("firstName"),
            )

            return {
                "success": True,
                "appointment_id": (result.data or {}).get("appointment_id"),
                "lead_id": lead_id,
            }
        except Exception as e:
            logger.exception("Error booking appointment for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    async def _try_next_slot(
        self,
        call_id: str,
        entities: Entity,
        appointment: dict,
        urgency_str: str,
    ) -> dict | None:
        """If chosen slot is taken, find next closest and rebook."""
        try:
            from src.integrations.odoo_appointments import create_appointment_service
            from src.brains.ops.service_catalog import infer_service_type_from_description

            svc = infer_service_type_from_description(
                appointment.get("serviceType") or "General service"
            )
            appt_service = await create_appointment_service()
            candidates = await appt_service.get_live_technicians()
            if not candidates:
                return None

            # Try to find next available slot from first candidate
            candidate_id = str(candidates[0].get("id"))
            chosen = appointment.get("chosenSlotStart", "")
            try:
                after = datetime.fromisoformat(chosen.replace("Z", "+00:00"))
            except Exception:
                after = datetime.now()

            slots = await appt_service.find_next_two_available_slots(
                tech_id=candidate_id,
                after=after,
                duration_minutes=svc.duration_minutes_max,
            )
            if not slots:
                return None

            new_slot = slots[0]
            # Rebook with new slot
            command = HaelCommand(
                request_id=generate_request_id(),
                channel=Channel.VOICE,
                raw_text=appointment.get("problemDescription", ""),
                intent=Intent.SCHEDULE_APPOINTMENT,
                brain=Brain.OPS,
                entities=entities,
                confidence=0.9,
                requires_human=False,
                missing_fields=[],
                idempotency_key="",
                metadata={
                    "call_id": call_id,
                    "chosen_slot_start": new_slot.start.isoformat(),
                    "urgency": urgency_str,
                    "slot_adjusted": True,
                },
            )
            result = await handle_ops_command(command)
            if result.status != OpsStatus.ERROR:
                return {"result": result, "new_slot_start": new_slot.start.isoformat()}
        except Exception as e:
            logger.warning("Fallback slot search failed for call %s: %s", call_id, e)
        return None

    # ── Reschedule ───────────────────────────────────────────────────

    async def _reschedule_appointment(
        self,
        call_id: str,
        customer: dict,
        appointment: dict,
        phone: str | None,
        email: str | None,
        analytics: dict | None = None,
    ) -> dict[str, Any]:
        """Reschedule an existing appointment via OPS brain."""
        try:
            entities = self._build_entity(customer, appointment, phone, email)
            call_summary = (analytics or {}).get("callSummary") if analytics else None
            if call_summary and not isinstance(call_summary, str):
                call_summary = str(call_summary).strip() or None
            elif call_summary:
                call_summary = call_summary.strip() or None

            command = HaelCommand(
                request_id=generate_request_id(),
                channel=Channel.VOICE,
                raw_text=appointment.get("rescheduleReason", "Reschedule request"),
                intent=Intent.RESCHEDULE_APPOINTMENT,
                brain=Brain.OPS,
                entities=entities,
                confidence=0.9,
                requires_human=False,
                missing_fields=[],
                idempotency_key="",
                metadata={
                    "call_id": call_id,
                    "appointment_id": appointment.get("existingAppointmentId"),
                    "chosen_slot_start": appointment.get("chosenSlotStart"),
                    "call_summary": call_summary,
                },
            )
            result = await handle_ops_command(command)

            if result.status == OpsStatus.ERROR:
                return {"success": False, "error": result.message}

            await self._send_confirmation(
                phone, email,
                f"Your appointment has been moved to {appointment.get('appointmentWindow', 'the new time')}. "
                f"You'll receive a reminder before your appointment.",
                customer.get("firstName"),
            )
            return {"success": True}
        except Exception as e:
            logger.exception("Error rescheduling for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    # ── Cancel ───────────────────────────────────────────────────────

    async def _cancel_appointment(
        self,
        call_id: str,
        customer: dict,
        appointment: dict,
        phone: str | None,
        email: str | None,
        analytics: dict | None = None,
    ) -> dict[str, Any]:
        """Cancel an existing appointment via OPS brain."""
        try:
            entities = self._build_entity(customer, appointment, phone, email)
            call_summary = (analytics or {}).get("callSummary") if analytics else None
            if call_summary and not isinstance(call_summary, str):
                call_summary = str(call_summary).strip() or None
            elif call_summary:
                call_summary = call_summary.strip() or None

            command = HaelCommand(
                request_id=generate_request_id(),
                channel=Channel.VOICE,
                raw_text=appointment.get("cancellationReason", "Cancellation request"),
                intent=Intent.CANCEL_APPOINTMENT,
                brain=Brain.OPS,
                entities=entities,
                confidence=0.9,
                requires_human=False,
                missing_fields=[],
                idempotency_key="",
                metadata={
                    "call_id": call_id,
                    "appointment_id": appointment.get("existingAppointmentId"),
                    "cancellation_reason": appointment.get("cancellationReason"),
                    "call_summary": call_summary,
                },
            )
            result = await handle_ops_command(command)

            if result.status == OpsStatus.ERROR:
                return {"success": False, "error": result.message}

            await self._send_confirmation(
                phone, email,
                "Your appointment has been cancelled. If you need to reschedule, "
                "please call us anytime.",
                customer.get("firstName"),
            )
            return {"success": True}
        except Exception as e:
            logger.exception("Error cancelling for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    # ── Service request (non-booking) ────────────────────────────────

    async def _create_service_request(
        self,
        call_id: str,
        customer: dict,
        service_req: dict,
        phone: str | None,
        email: str | None,
        urgency_str: str,
        is_emergency: bool,
        analytics: dict | None = None,
    ) -> dict[str, Any]:
        """Create a service request lead in Odoo."""
        try:
            entities = Entity(
                full_name=f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                phone=phone,
                email=email,
                address=customer.get("address"),
                zip_code=customer.get("zipCode"),
                problem_description=service_req.get("issueDescription", ""),
                system_type=service_req.get("systemType"),
                urgency_level=_URGENCY_MAP.get(urgency_str, UrgencyLevel.MEDIUM),
            )

            call_summary = (analytics or {}).get("callSummary") if analytics else None
            if call_summary and not isinstance(call_summary, str):
                call_summary = str(call_summary).strip() or None
            elif call_summary:
                call_summary = call_summary.strip() or None

            from src.integrations.odoo_leads import create_lead_service

            lead_service = await create_lead_service()
            lead_result = await lead_service.upsert_service_lead(
                call_id=call_id,
                entities=entities,
                urgency=entities.urgency_level,
                is_emergency=is_emergency,
                emergency_reason="customer_stated_emergency" if is_emergency else None,
                raw_text=service_req.get("issueDescription", ""),
                request_id=generate_request_id(),
                channel="voice",
                structured_params={
                    "caller_type": customer.get("callerType"),
                    "property_management_company": customer.get("managementCompany"),
                    "technician_notes": service_req.get("technicianNotes"),
                    "lead_source": customer.get("leadSource"),
                },
                call_summary=call_summary,
            )
            lead_id = lead_result.get("lead_id")

            await self._send_confirmation(
                phone, email,
                "Your service request has been received. Our team will contact you "
                "to schedule an appointment.",
                customer.get("firstName"),
            )
            return {"success": True, "lead_id": lead_id}
        except Exception as e:
            logger.exception("Error creating service request for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    # ── Quote ────────────────────────────────────────────────────────

    async def _create_quote(
        self,
        call_id: str,
        customer: dict,
        quote_data: dict,
        phone: str | None,
        email: str | None,
        analytics: dict | None = None,
    ) -> dict[str, Any]:
        """Create a quote lead in Odoo CRM."""
        try:
            entities = Entity(
                full_name=f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                phone=phone,
                email=email,
                address=customer.get("address"),
                zip_code=customer.get("zipCode"),
                problem_description=(
                    f"Quote request: {quote_data.get('systemType', 'HVAC')} system. "
                    f"Sq ft: {quote_data.get('squareFootage', 'N/A')}. "
                    f"Age: {quote_data.get('systemAge', 'N/A')}. "
                    f"Budget: {quote_data.get('budgetRange', 'N/A')}. "
                    f"Timeline: {quote_data.get('timeline', 'N/A')}."
                ),
                urgency_level=UrgencyLevel.MEDIUM,
            )

            call_summary = (analytics or {}).get("callSummary") if analytics else None
            if call_summary and not isinstance(call_summary, str):
                call_summary = str(call_summary).strip() or None
            elif call_summary:
                call_summary = call_summary.strip() or None

            from src.integrations.odoo_leads import create_lead_service

            lead_service = await create_lead_service()
            lead_result = await lead_service.upsert_service_lead(
                call_id=call_id or f"quote_{generate_request_id()}",
                entities=entities,
                urgency=UrgencyLevel.MEDIUM,
                is_emergency=False,
                raw_text=entities.problem_description,
                request_id=generate_request_id(),
                channel="voice",
                structured_params={
                    "caller_type": customer.get("callerType"),
                    "lead_source": customer.get("leadSource"),
                },
                call_summary=call_summary,
            )
            lead_id = lead_result.get("lead_id")

            # Ensure FSM task
            if lead_id:
                try:
                    await lead_service.ensure_fsm_task_for_lead(
                        lead_id=lead_id,
                        customer_name=entities.full_name,
                        service_address=entities.address,
                    )
                except Exception as fsm_err:
                    logger.warning("FSM task creation failed for quote lead %s: %s", lead_id, fsm_err)

            SAME_DAY_INSTALL_LINK = "https://www.hvacrfinest.com/same-day-install-service"
            await self._send_confirmation(
                phone, email,
                f"Here's your instant quote and same-day install link: {SAME_DAY_INSTALL_LINK} "
                "Choose your system, see pricing, and book your install in minutes. We'll handle the rest.",
                customer.get("firstName"),
            )
            return {"success": True, "lead_id": lead_id}
        except Exception as e:
            logger.exception("Error creating quote for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    # ── Complaint ────────────────────────────────────────────────────

    async def _handle_complaint(
        self,
        call_id: str,
        customer: dict,
        complaint: dict,
        phone: str | None,
        email: str | None,
        analytics: dict | None = None,
    ) -> dict[str, Any]:
        """Create complaint ticket in Odoo and notify management."""
        try:
            from src.integrations.odoo import create_odoo_client_from_settings
            from src.config.settings import get_settings

            settings = get_settings()
            customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()

            odoo_client = create_odoo_client_from_settings()
            await odoo_client.authenticate()

            description = (
                f"[COMPLAINT]\n"
                f"Details: {complaint.get('details', 'No details provided')}\n"
                f"Previous Service Date: {complaint.get('previousServiceDate', 'N/A')}\n"
                f"Previous Service ID: {complaint.get('previousServiceId', 'N/A')}\n"
                f"Manager Callback Requested: {'Yes' if complaint.get('requestedManagerCallback') else 'No'}\n"
                f"Call ID: {call_id}"
            )
            call_summary = (analytics or {}).get("callSummary") if analytics else None
            if call_summary and (call_summary := str(call_summary).strip()):
                description = f"{description}\n\nCall Summary:\n{call_summary}"

            lead_id = await odoo_client.create("crm.lead", {
                "name": f"Complaint - {customer_name or phone}",
                "contact_name": customer_name,
                "phone": phone,
                "email_from": email,
                "description": description,
                "priority": "1",  # URGENT
            })

            # Tag as escalation (best-effort)
            try:
                tags = await odoo_client.search_read(
                    "crm.tag",
                    [("name", "in", ["Escalation", "Complaint", "URGENT"])],
                    fields=["id"],
                    limit=1,
                )
                if tags:
                    await odoo_client.write(
                        "crm.lead", [lead_id],
                        {"tag_ids": [(6, 0, [tags[0]["id"]])]},
                    )
            except Exception:
                pass

            # Notify management via SMS + email (fire-and-forget)
            asyncio.create_task(
                self._notify_management_complaint(
                    settings, customer_name, phone, complaint.get("details", ""),
                )
            )

            await self._send_confirmation(
                phone, email,
                "Your complaint has been received and escalated to our management team. "
                "Someone will follow up with you shortly.",
                customer.get("firstName"),
            )
            return {"success": True, "lead_id": lead_id}
        except Exception as e:
            logger.exception("Error handling complaint for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    async def _notify_management_complaint(
        self, settings: Any, customer_name: str, phone: str | None, details: str,
    ) -> None:
        """Send complaint notification to management (fire-and-forget)."""
        try:
            from src.integrations.twilio_sms import create_twilio_client_from_settings

            sms_body = (
                f"[COMPLAINT] {customer_name or 'Unknown'} ({phone or 'no phone'}): "
                f"{details[:200]}"
            )
            sms_client = create_twilio_client_from_settings()
            if sms_client:
                for mgr_phone in [settings.JUNIOR_PHONE, settings.LINDA_PHONE]:
                    if mgr_phone:
                        await sms_client.send_sms(to=mgr_phone, body=sms_body)
        except Exception as e:
            logger.warning("Failed to notify management of complaint: %s", e)

    # ── Invoice ──────────────────────────────────────────────────────

    async def _send_invoice(
        self,
        call_id: str,
        customer: dict,
        invoice_data: dict,
        phone: str | None,
        email: str | None,
    ) -> dict[str, Any]:
        """Trigger invoice email via CORE brain handler."""
        try:
            from src.brains.core import handle_core_command
            from src.brains.core.schema import CoreStatus

            entities = Entity(
                full_name=f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                phone=phone,
                email=email,
            )
            command = HaelCommand(
                request_id=generate_request_id(),
                channel=Channel.VOICE,
                raw_text=f"Invoice request: {invoice_data.get('invoiceNumber', 'N/A')}",
                intent=Intent.SERVICE_REQUEST,
                brain=Brain.CORE,
                entities=entities,
                confidence=0.9,
                requires_human=False,
                missing_fields=[],
                idempotency_key="",
                metadata={
                    "call_id": call_id,
                    "invoice_number": invoice_data.get("invoiceNumber"),
                },
            )
            # Core brain handler is synchronous
            result = handle_core_command(command)

            if result.status == CoreStatus.ERROR:
                return {"success": False, "error": result.message}

            await self._send_confirmation(
                phone, email,
                "Your invoice has been sent to your email. Please check your inbox.",
                customer.get("firstName"),
            )
            return {"success": True}
        except Exception as e:
            logger.exception("Error sending invoice for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    # ── Membership enrollment ────────────────────────────────────────

    async def _enroll_membership(
        self,
        call_id: str,
        customer: dict,
        enrollment: dict,
        phone: str | None,
        email: str | None,
    ) -> dict[str, Any]:
        """Create membership enrollment lead and send confirmation."""
        try:
            plan_name = enrollment.get("membershipType", "basic").title()

            entities = Entity(
                full_name=f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                phone=phone,
                email=email,
                address=customer.get("address"),
                zip_code=customer.get("zipCode"),
                problem_description=f"Membership Enrollment - {plan_name}",
                urgency_level=UrgencyLevel.MEDIUM,
            )

            from src.integrations.odoo_leads import create_lead_service

            lead_service = await create_lead_service()
            lead_result = await lead_service.upsert_service_lead(
                call_id=call_id or generate_request_id(),
                entities=entities,
                urgency=UrgencyLevel.MEDIUM,
                is_emergency=False,
                raw_text=f"Membership Enrollment - {plan_name}",
                request_id=generate_request_id(),
                channel="voice",
                structured_params={
                    "caller_type": customer.get("callerType"),
                    "lead_source": customer.get("leadSource"),
                },
            )
            lead_id = lead_result.get("lead_id")

            # Send enrollment-specific notification
            try:
                from src.integrations.twilio_sms import (
                    create_twilio_client_from_settings,
                    build_membership_enrollment_sms,
                )
                from src.integrations.email_notifications import (
                    create_email_service_from_settings,
                    build_membership_enrollment_email,
                )

                # SMS
                sms_client = create_twilio_client_from_settings()
                if sms_client and phone:
                    sms_body = build_membership_enrollment_sms(
                        customer_name=entities.full_name,
                        plan_name=plan_name,
                        annual_price=0,  # Will be set by enrollment workflow
                        payment_link="",
                    )
                    await sms_client.send_sms(to=phone, body=sms_body)

                # Email
                if email:
                    email_service = create_email_service_from_settings()
                    if email_service:
                        subj, html, text = build_membership_enrollment_email(
                            customer_name=entities.full_name,
                            plan_name=plan_name,
                            annual_price=0,
                            payment_link="",
                            vip_benefits="",
                        )
                        email_service.send_email(
                            to=email, subject=subj,
                            body_html=html, body_text=text,
                        )
            except Exception as notify_err:
                logger.warning("Membership notification failed: %s", notify_err)

            return {"success": True, "lead_id": lead_id}
        except Exception as e:
            logger.exception("Error enrolling membership for call %s: %s", call_id, e)
            return {"success": False, "error": str(e)}

    # ── Follow-up activity ───────────────────────────────────────────

    async def _create_follow_up(
        self,
        call_id: str,
        customer: dict,
        analytics: dict,
        phone: str | None,
    ) -> None:
        """Create a callback activity in Odoo if follow-up is required."""
        try:
            from src.integrations.odoo_leads import create_lead_service

            lead_service = await create_lead_service()
            # Find the lead for this customer
            customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()

            entities = Entity(
                full_name=customer_name,
                phone=phone,
                problem_description=f"Follow-up needed: {analytics.get('followUpReason', 'See call transcript')}",
            )
            lead_result = await lead_service.upsert_service_lead(
                call_id=call_id,
                entities=entities,
                urgency=UrgencyLevel.MEDIUM,
                is_emergency=False,
                raw_text=f"Follow-up: {analytics.get('followUpReason', '')}",
                request_id=generate_request_id(),
                channel="voice",
                structured_params={
                    "call_status": "Follow-up Required",
                    "follow_up_reason": analytics.get("followUpReason"),
                    "primary_intent": analytics.get("primaryIntent"),
                    "sentiment": analytics.get("sentiment"),
                },
            )

            # Create callback activity
            lead_id = lead_result.get("lead_id")
            if lead_id:
                try:
                    await lead_service.client.create("mail.activity", {
                        "res_id": lead_id,
                        "res_model": "crm.lead",
                        "summary": f"Callback needed - {analytics.get('followUpReason', 'Follow-up')}",
                        "note": (
                            f"Call ID: {call_id}\n"
                            f"Intent: {analytics.get('primaryIntent', 'unknown')}\n"
                            f"Sentiment: {analytics.get('sentiment', 'unknown')}\n"
                            f"Reason: {analytics.get('followUpReason', 'N/A')}"
                        ),
                    })
                except Exception as activity_err:
                    logger.warning("Failed to create callback activity: %s", activity_err)
        except Exception as e:
            logger.warning("Failed to create follow-up for call %s: %s", call_id, e)

    # ── Shared helpers ───────────────────────────────────────────────

    def _build_entity(
        self,
        customer: dict,
        appointment: dict,
        phone: str | None,
        email: str | None,
    ) -> Entity:
        """Build Entity from structured output data."""
        urgency_str = (appointment.get("urgency") or "routine").lower()
        return Entity(
            full_name=f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
            phone=phone,
            email=email,
            address=customer.get("address"),
            zip_code=customer.get("zipCode"),
            problem_description=appointment.get("problemDescription", ""),
            system_type=appointment.get("serviceType"),
            urgency_level=_URGENCY_MAP.get(urgency_str, UrgencyLevel.MEDIUM),
            property_type=customer.get("propertyType"),
        )

    async def _create_lead_for_booking(
        self,
        call_id: str,
        entities: Entity,
        urgency: UrgencyLevel,
        is_emergency: bool,
        appointment: dict,
        customer: dict,
    ) -> int | None:
        """Create/update CRM lead for a booked appointment."""
        try:
            from src.integrations.odoo_leads import create_lead_service

            lead_service = await create_lead_service()
            lead_result = await asyncio.wait_for(
                lead_service.upsert_service_lead(
                    call_id=call_id,
                    entities=entities,
                    urgency=urgency,
                    is_emergency=is_emergency,
                    emergency_reason="customer_stated_emergency" if is_emergency else None,
                    raw_text=appointment.get("problemDescription", ""),
                    request_id=generate_request_id(),
                    channel="voice",
                    structured_params={
                        "caller_type": customer.get("callerType"),
                        "property_management_company": customer.get("managementCompany"),
                        "technician_notes": appointment.get("technicianNotes"),
                        "lead_source": customer.get("leadSource"),
                    },
                ),
                timeout=15.0,
            )
            return lead_result.get("lead_id")
        except asyncio.TimeoutError:
            logger.warning("Lead creation timed out for call %s", call_id)
            return None
        except Exception as e:
            logger.warning("Lead creation failed for call %s: %s", call_id, e)
            return None

    async def _send_confirmation(
        self,
        phone: str | None,
        email: str | None,
        message: str,
        customer_name: str | None = None,
    ) -> None:
        """Send SMS + email confirmation to customer. Uses webhook caller number as fallback if SMS fails."""
        try:
            logger.info(
                "%s sending confirmation sms=%s email=%s to phone=%s",
                _PREFIX, bool(phone), bool(email), _mask_phone(phone),
            )
            from src.integrations.twilio_sms import create_twilio_client_from_settings
            from src.integrations.email_notifications import create_email_service_from_settings

            # SMS (primary; retry to webhook caller number on failure)
            fallback_phone = getattr(self, "_fallback_phone", None)
            if phone or fallback_phone:
                sms_body = f"HVAC-R Finest: {message}"
                sms_client = create_twilio_client_from_settings()
                if sms_client:
                    to_try = [phone] if phone else []
                    if fallback_phone and fallback_phone != phone:
                        to_try.append(fallback_phone)
                    if not to_try and fallback_phone:
                        to_try = [fallback_phone]
                    for to_phone in to_try:
                        try:
                            await sms_client.send_sms(to=to_phone, body=sms_body)
                            break
                        except Exception as sms_err:
                            logger.warning("SMS confirmation failed to %s: %s", _mask_phone(to_phone), sms_err)
                            if to_phone == phone and fallback_phone and fallback_phone != phone:
                                logger.info("%s retrying SMS to webhook caller %s", _PREFIX, _mask_phone(fallback_phone))
                            else:
                                break

            # Email
            if email:
                try:
                    email_service = create_email_service_from_settings()
                    if email_service:
                        greeting = f"Hi {customer_name}," if customer_name else "Hello,"
                        email_service.send_email(
                            to=email,
                            subject="HVAC-R Finest - Confirmation",
                            body_html=f"<p>{greeting}</p><p>{message}</p><p>Thank you for choosing HVAC-R Finest!</p>",
                            body_text=f"{greeting}\n\n{message}\n\nThank you for choosing HVAC-R Finest!",
                        )
                except Exception as email_err:
                    logger.warning("Email confirmation failed: %s", email_err)
        except Exception as e:
            logger.warning("Notification send failed: %s", e)

    def _schedule_reminder(
        self,
        result: Any,
        phone: str | None,
        customer: dict,
    ) -> None:
        """Schedule appointment reminder (best-effort)."""
        try:
            data = result.data or {}
            appointment_id = data.get("appointment_id")
            scheduled_time = data.get("scheduled_time")
            if not appointment_id or not scheduled_time:
                return

            from src.db.session import get_session_factory
            from src.utils.appointment_reminders import schedule_appointment_reminder

            session_factory = get_session_factory()
            db = session_factory()
            try:
                if isinstance(scheduled_time, str):
                    scheduled_time = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))

                schedule_appointment_reminder(
                    db=db,
                    appointment_id=appointment_id,
                    appointment_datetime=scheduled_time,
                    customer_phone=phone,
                    customer_name=f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                    appointment_date=scheduled_time.strftime("%A, %B %d"),
                    appointment_time=scheduled_time.strftime("%I:%M %p"),
                    tech_name=(data.get("assigned_technician") or {}).get("name"),
                    service_type=data.get("service_type"),
                )
            finally:
                db.close()
        except Exception as e:
            logger.warning("Failed to schedule reminder: %s", e)
