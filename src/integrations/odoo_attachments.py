"""
HAES HVAC - Odoo Attachment Upload Utility

Downloads a VAPI call recording and uploads it to Odoo as an ir.attachment
linked to a CRM lead or FSM task.
"""

import base64
import logging
from typing import Any

import httpx

from src.integrations.odoo import create_odoo_client_from_settings

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[OdooAttachments]"


async def upload_recording_to_odoo(
    recording_url: str,
    res_model: str,
    res_id: int,
    call_id: str,
) -> int | None:
    """Download a VAPI call recording and attach it to an Odoo record.

    Args:
        recording_url: URL of the recording file (from VAPI end-of-call payload)
        res_model: Odoo model to attach to ("crm.lead" or "project.task")
        res_id: Record ID in Odoo
        call_id: VAPI call ID (for naming and logging)

    Returns:
        Attachment ID on success, None on failure
    """
    try:
        # 1. Download recording
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as http:
            response = await http.get(recording_url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "audio/wav")
        mimetype = content_type.split(";")[0].strip()

        # Determine file extension from mimetype
        ext_map = {
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/ogg": "ogg",
            "audio/webm": "webm",
        }
        ext = ext_map.get(mimetype, "wav")

        file_data = response.content
        if not file_data:
            logger.warning(
                "%s call_id=%s empty recording response from %s",
                _LOG_PREFIX, call_id, recording_url[:80],
            )
            return None

        logger.info(
            "%s call_id=%s downloaded recording size=%d bytes mimetype=%s",
            _LOG_PREFIX, call_id, len(file_data), mimetype,
        )

        # 2. Base64 encode
        b64_data = base64.b64encode(file_data).decode("ascii")

        # 3. Upload to Odoo as ir.attachment
        odoo_client = create_odoo_client_from_settings()
        await odoo_client.authenticate()

        attachment_id = await odoo_client.create("ir.attachment", {
            "name": f"Call Recording - {call_id}.{ext}",
            "res_model": res_model,
            "res_id": res_id,
            "type": "binary",
            "datas": b64_data,
            "mimetype": mimetype,
        })

        await odoo_client.close()

        logger.info(
            "%s call_id=%s uploaded recording attachment_id=%s to %s %s",
            _LOG_PREFIX, call_id, attachment_id, res_model, res_id,
        )
        return attachment_id

    except Exception as e:
        logger.error(
            "%s call_id=%s failed to upload recording to %s %s: %s",
            _LOG_PREFIX, call_id, res_model, res_id, e,
        )
        return None
