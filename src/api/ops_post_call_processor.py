"""
HAES HVAC - OPS Post-Call Processor

Processes VAPI structured outputs from Riley OPS end-of-call reports.
Completely separate from customer inbound PostCallProcessor.

Currently handles:
  - FSM subtask creation (technicians adding subtasks to existing jobs)

Future phases will add more OPS actions here.
"""

import logging
from typing import Any

from src.integrations.odoo_fsm_subtasks import FSMSubtaskService

logger = logging.getLogger(__name__)

# Log prefix — distinct from customer inbound's [PostCallProcessor]
_PREFIX = "[OpsPostCallProcessor]"


def _mask_phone(phone: str | None) -> str:
    """Last 4 digits only for log privacy."""
    if not phone or len(phone) < 4:
        return "***"
    return f"***{phone.strip()[-4:]}"


def _webhook_caller_number(payload: dict) -> str | None:
    """Extract caller number from end-of-call-report webhook."""
    call_data = (payload or {}).get("message", {}).get("call", {})
    return (
        call_data.get("customer", {}).get("number")
        or call_data.get("from")
    ) or None


class OpsPostCallProcessor:
    """Processes structured outputs from Riley OPS end-of-call reports.

    Separate from customer inbound PostCallProcessor.
    Currently handles: FSM subtask creation.
    """

    def __init__(self):
        self._fsm_service: FSMSubtaskService | None = None

    def _get_fsm_service(self) -> FSMSubtaskService:
        """Lazy-init FSM subtask service."""
        if self._fsm_service is None:
            self._fsm_service = FSMSubtaskService()
        return self._fsm_service

    # ── Public entry point ───────────────────────────────────────────

    async def process(self, call_id: str, payload: dict) -> dict[str, Any]:
        """Main entry — called from end-of-call webhook handler.

        Args:
            call_id: VAPI call ID
            payload: Full end-of-call-report webhook payload

        Returns:
            Summary dict of actions taken
        """
        structured_outputs = self._extract_structured_outputs(payload)
        if not structured_outputs:
            logger.info("%s call_id=%s no structured outputs — skipping", _PREFIX, call_id)
            return {"actions": [], "skipped": True}

        output_names = list(structured_outputs.keys())
        logger.info(
            "%s call_id=%s structured_outputs_received=%s",
            _PREFIX, call_id, output_names,
        )

        caller_phone = _webhook_caller_number(payload)
        results: list[dict[str, Any]] = []

        # ── FSM Subtask Request ──────────────────────────────────────
        subtask_request = structured_outputs.get("FSM Subtask Request")
        if subtask_request and isinstance(subtask_request, dict):
            if subtask_request.get("hasSubtasks"):
                result = await self._process_subtask_request(
                    call_id, subtask_request, caller_phone,
                )
                results.append(result)
            else:
                logger.info(
                    "%s call_id=%s FSM Subtask Request hasSubtasks=false — skipping",
                    _PREFIX, call_id,
                )

        logger.info(
            "%s call_id=%s processing complete actions=%d",
            _PREFIX, call_id, len(results),
        )
        return {"actions": results}

    # ── Structured Output Extraction ─────────────────────────────────

    def _extract_structured_outputs(self, payload: dict) -> dict[str, Any]:
        """Parse structured outputs from VAPI end-of-call payload.

        VAPI may send structuredOutputs as either:
        - A list of {name, result} objects, or
        - A dict keyed by UUID with {name, result} values.
        """
        message = payload.get("message", payload)
        artifact = message.get("artifact", {})
        raw = artifact.get("structuredOutputs") or []

        # Normalize to list (VAPI sometimes sends dict keyed by UUID)
        if isinstance(raw, dict):
            raw_outputs = list(raw.values())
        elif isinstance(raw, list):
            raw_outputs = raw
        else:
            raw_outputs = []

        if not raw_outputs:
            return {}

        raw_names = [
            o.get("name", "") for o in raw_outputs if isinstance(o, dict)
        ]
        logger.info(
            "%s raw structuredOutputs from VAPI: names=%s count=%s",
            _PREFIX, raw_names, len(raw_outputs),
        )

        parsed: dict[str, Any] = {}
        for output in raw_outputs:
            if not isinstance(output, dict):
                continue
            name = output.get("name", "")
            result = output.get("result", {})
            if name and isinstance(result, dict):
                parsed[name] = result

        return parsed

    # ── FSM Subtask Processing ───────────────────────────────────────

    async def _process_subtask_request(
        self,
        call_id: str,
        request: dict[str, Any],
        caller_phone: str | None,
    ) -> dict[str, Any]:
        """Create subtasks in Odoo under the parent FSM task."""
        parent_code = request.get("parentTaskCode", "")
        subtasks = request.get("subtasks") or []
        caller_name = request.get("callerName")
        additional_notes = request.get("additionalNotes")

        logger.info(
            "%s call_id=%s processing subtask_request parent=%s subtask_count=%d caller=%s phone=%s",
            _PREFIX, call_id, parent_code, len(subtasks),
            caller_name or "unknown", _mask_phone(caller_phone),
        )

        if not parent_code:
            logger.warning(
                "%s call_id=%s no parentTaskCode in subtask request — skipping",
                _PREFIX, call_id,
            )
            return {"action": "subtask_creation", "success": False, "error": "no_parent_code"}

        if not subtasks:
            logger.warning(
                "%s call_id=%s parentTaskCode=%s but no subtasks extracted — skipping",
                _PREFIX, call_id, parent_code,
            )
            return {"action": "subtask_creation", "success": False, "error": "no_subtasks"}

        fsm_service = self._get_fsm_service()

        # 1. Look up parent task
        try:
            parent_task = await fsm_service.lookup_parent_task(parent_code)
        except Exception as e:
            logger.error(
                "%s call_id=%s failed to look up parent task %s: %s",
                _PREFIX, call_id, parent_code, e,
            )
            await self._send_sms(
                caller_phone,
                f"HVAC-R Finest: Could not find job {parent_code}. Please verify the job number and try again.",
            )
            return {"action": "subtask_creation", "success": False, "error": f"lookup_failed: {e}"}

        if not parent_task:
            logger.warning(
                "%s call_id=%s parent task not found: %s",
                _PREFIX, call_id, parent_code,
            )
            await self._send_sms(
                caller_phone,
                f"HVAC-R Finest: Job {parent_code} was not found in the system. Please check the job number.",
            )
            return {"action": "subtask_creation", "success": False, "error": "parent_not_found"}

        # 2. Create subtasks
        try:
            results = await fsm_service.create_subtasks_batch(parent_task, subtasks)
        except Exception as e:
            logger.error(
                "%s call_id=%s failed to create subtasks for %s: %s",
                _PREFIX, call_id, parent_code, e,
            )
            await self._send_sms(
                caller_phone,
                f"HVAC-R Finest: There was an issue adding subtasks to job {parent_code}. Please contact dispatch.",
            )
            return {"action": "subtask_creation", "success": False, "error": f"creation_failed: {e}"}

        succeeded = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        logger.info(
            "%s call_id=%s subtask_creation complete parent=%s succeeded=%d failed=%d",
            _PREFIX, call_id, parent_code, len(succeeded), len(failed),
        )

        if additional_notes:
            logger.info(
                "%s call_id=%s additional_notes: %s",
                _PREFIX, call_id, additional_notes[:200],
            )

        # 3. Send SMS confirmation
        if succeeded:
            titles = ", ".join(r["title"] for r in succeeded)
            sms_body = (
                f"HVAC-R Finest: Added {len(succeeded)} subtask(s) to job {parent_code}: {titles}."
            )
            if failed:
                sms_body += f" ({len(failed)} subtask(s) could not be added — contact dispatch.)"
            await self._send_sms(caller_phone, sms_body)

        return {
            "action": "subtask_creation",
            "success": len(succeeded) > 0,
            "parent_code": parent_code,
            "parent_task_id": parent_task["id"],
            "subtasks_created": len(succeeded),
            "subtasks_failed": len(failed),
            "results": results,
        }

    # ── SMS Notification ─────────────────────────────────────────────

    async def _send_sms(self, to_phone: str | None, body: str) -> None:
        """Send SMS confirmation to the technician."""
        if not to_phone:
            logger.warning("%s cannot send SMS — no phone number", _PREFIX)
            return

        try:
            from src.integrations.twilio_sms import create_twilio_client_from_settings

            sms_client = create_twilio_client_from_settings()
            await sms_client.send_sms(to=to_phone, body=body)
            logger.info(
                "%s SMS sent to %s: %s",
                _PREFIX, _mask_phone(to_phone), body[:80],
            )
        except Exception as e:
            logger.warning(
                "%s SMS failed to %s: %s", _PREFIX, _mask_phone(to_phone), e,
            )
