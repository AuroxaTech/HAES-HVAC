"""
HAES HVAC - Odoo FSM Subtask Integration

Creates subtasks under existing FSM (Field Service) parent tasks in Odoo.
Used by OpsPostCallProcessor to process technician subtask requests.
"""

import logging
from typing import Any

from src.integrations.odoo import OdooClient, create_odoo_client_from_settings

logger = logging.getLogger(__name__)

_LOG_PREFIX = "[FSMSubtaskService]"


class FSMSubtaskService:
    """Creates subtasks under parent FSM tasks in Odoo."""

    def __init__(self, client: OdooClient | None = None):
        self.client = client or create_odoo_client_from_settings()
        self._project_task_fields: set[str] | None = None

    async def _ensure_authenticated(self) -> None:
        """Ensure the Odoo client is authenticated."""
        if not self.client._uid:
            await self.client.authenticate()

    async def _get_project_task_fields(self) -> set[str]:
        """Get available fields for project.task model. Caches result."""
        if self._project_task_fields is None:
            try:
                await self._ensure_authenticated()
                fields_info = await self.client.fields_get("project.task")
                self._project_task_fields = set(fields_info.keys())
                logger.debug(
                    "%s Cached %d project.task fields",
                    _LOG_PREFIX, len(self._project_task_fields),
                )
            except Exception as e:
                logger.warning("%s Failed to get project.task fields: %s", _LOG_PREFIX, e)
                self._project_task_fields = {
                    "name", "parent_id", "partner_id", "project_id", "description",
                }
        return self._project_task_fields

    def _filter_valid_fields(
        self, values: dict[str, Any], valid_fields: set[str],
    ) -> dict[str, Any]:
        """Filter out fields that don't exist in the model."""
        return {k: v for k, v in values.items() if k in valid_fields and v is not None}

    # ── Lookup ────────────────────────────────────────────────────────

    async def lookup_parent_task(self, task_code: str) -> dict[str, Any] | None:
        """Look up parent FSM task by its task_code field (e.g., 'J101246').

        The task_code field in Odoo stores the J-prefixed code and does NOT
        correspond to the Odoo record id.

        Returns the task dict or None if not found.
        """
        # Normalize: ensure J prefix, uppercase
        code = task_code.strip().upper()
        if not code.startswith("J"):
            code = f"J{code}"

        await self._ensure_authenticated()

        tasks = await self.client.search_read(
            "project.task",
            [("task_code", "=", code)],
            fields=["id", "name", "task_code", "project_id", "partner_id", "stage_id", "user_ids"],
        )

        if not tasks:
            logger.warning(
                "%s Parent task not found: task_code=%s", _LOG_PREFIX, code,
            )
            return None

        task = tasks[0]
        logger.info(
            "%s Found parent task: task_code=%s id=%d name=%s",
            _LOG_PREFIX, code, task["id"], task.get("name"),
        )
        return task

    # ── Subtask Creation ──────────────────────────────────────────────

    async def create_subtask(
        self,
        parent_task: dict[str, Any],
        subtask: dict[str, Any],
    ) -> int:
        """Create a single subtask under the parent FSM task.

        Args:
            parent_task: Parent task dict from lookup_parent_task()
            subtask: Dict with 'title' (required) and 'description' (optional)

        Returns:
            Created task ID
        """
        task_fields = await self._get_project_task_fields()

        values: dict[str, Any] = {
            "name": subtask["title"],
            "parent_id": parent_task["id"],
        }

        # Inherit project from parent (Odoo M2O returns [id, name] tuple)
        project_id = parent_task.get("project_id")
        if project_id:
            values["project_id"] = (
                project_id[0] if isinstance(project_id, (list, tuple)) else project_id
            )

        # Inherit customer from parent
        partner_id = parent_task.get("partner_id")
        if partner_id:
            values["partner_id"] = (
                partner_id[0] if isinstance(partner_id, (list, tuple)) else partner_id
            )

        # Inherit assignees from parent (M2M field — use set command)
        user_ids = parent_task.get("user_ids")
        if user_ids and isinstance(user_ids, list) and user_ids:
            values["user_ids"] = [(6, 0, user_ids)]

        # Optional description
        if subtask.get("description"):
            values["description"] = subtask["description"]

        values = self._filter_valid_fields(values, task_fields)

        await self._ensure_authenticated()
        task_id = await self.client.create("project.task", values)

        task_code = f"J{task_id:06d}"
        logger.info(
            "%s Created subtask %s: '%s' under parent %d",
            _LOG_PREFIX, task_code, subtask["title"], parent_task["id"],
        )
        return task_id

    async def create_subtasks_batch(
        self,
        parent_task: dict[str, Any],
        subtasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Create multiple subtasks under a parent task.

        Returns list of result dicts with task_code and success status.
        """
        results: list[dict[str, Any]] = []

        for subtask in subtasks:
            try:
                task_id = await self.create_subtask(parent_task, subtask)
                task_code = f"J{task_id:06d}"
                results.append({
                    "title": subtask["title"],
                    "task_code": task_code,
                    "task_id": task_id,
                    "success": True,
                })
            except Exception as e:
                logger.error(
                    "%s Failed to create subtask '%s': %s",
                    _LOG_PREFIX, subtask.get("title", "unknown"), e,
                )
                results.append({
                    "title": subtask.get("title", "unknown"),
                    "error": str(e),
                    "success": False,
                })

        succeeded = sum(1 for r in results if r["success"])
        logger.info(
            "%s Batch complete: %d/%d subtasks created under parent %d",
            _LOG_PREFIX, succeeded, len(subtasks), parent_task["id"],
        )
        return results
