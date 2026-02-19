#!/usr/bin/env python3
"""
Test: Schedule for next week (e.g. Tuesday) — confirm the chosen slot is accepted.

Reproduces the flow where:
1. check_availability returns two slots (e.g. Tue 8–12, Wed 2–6)
2. Customer confirms Tuesday
3. schedule_appointment is called with chosen_slot_start = Tuesday slot

If the calendar is open, the backend should accept the slot. If the bot incorrectly
says "no longer available", this script will show it and what slots were re-offered.

Usage:
    From project root with .env (Odoo credentials):
        .venv/bin/python scripts/test_schedule_chosen_slot_next_week.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")
load_dotenv()

from src.hael.schema import Channel, Entity, HaelCommand, Intent, Brain
from src.brains.ops import handle_ops_command
from src.brains.ops.schema import OpsStatus
from src.integrations.odoo_appointments import create_appointment_service
from src.brains.ops.service_catalog import infer_service_type_from_description
from src.utils.request_id import generate_request_id


def _next_week_start():
    """Next Tuesday 8 AM local (or next operating day)."""
    from src.brains.ops.scheduling_rules import BUSINESS_START, OPERATING_DAYS
    now = datetime.now()
    day = now.replace(hour=BUSINESS_START.hour, minute=BUSINESS_START.minute, second=0, microsecond=0)
    for _ in range(14):
        if day > now and day.weekday() in OPERATING_DAYS:
            return day
        day += timedelta(days=1)
    return day


async def main() -> int:
    print("=" * 60)
    print("Test: Schedule chosen slot (next week) — is it still accepted?")
    print("=" * 60)

    appointment_service = await create_appointment_service()
    service_type = infer_service_type_from_description("General service")
    duration_minutes = service_type.duration_minutes_max

    # 1) Get two slots (same logic as check_availability: two earliest across techs)
    now = datetime.now()
    from src.brains.ops.handlers import _dispatch_search_start
    preferred_start = _dispatch_search_start(now, allow_same_day_after_cutoff=False)
    # Prefer next week
    next_week = _next_week_start()
    if next_week > preferred_start:
        preferred_start = next_week

    candidates = await appointment_service.get_live_technicians()
    all_entries = []
    for c in candidates:
        cid = str(c.get("id"))
        raw = await appointment_service.find_next_two_available_slots(
            tech_id=cid, after=preferred_start, duration_minutes=duration_minutes
        )
        for s in raw or []:
            start_naive = s.start.astimezone().replace(tzinfo=None) if s.start.tzinfo else s.start
            if start_naive >= preferred_start:
                all_entries.append((start_naive, s, cid))
    all_entries.sort(key=lambda x: x[0])
    first_two = all_entries[:2]

    if not first_two:
        print("No slots found. Check Odoo calendar and preferred_start.")
        return 1

    chosen_start_dt = first_two[0][1].start
    chosen_tech_id = first_two[0][2]
    chosen_start_iso = chosen_start_dt.isoformat()
    print(f"\n1) Simulated check_availability returned 2 slots.")
    print(f"   First slot (chosen): {chosen_start_iso} (technician_id={chosen_tech_id})")
    print(f"   Second slot:         {first_two[1][1].start.isoformat()} (technician_id={first_two[1][2]})")

    # 2) Build SCHEDULE_APPOINTMENT command with chosen_slot_start
    entities = Entity(
        full_name="Test Customer",
        phone="+15551234567",
        email="test@example.com",
        address="123 Test St, Dallas, TX 75115",
        zip_code="75115",
        problem_description="AC not cooling",
    )
    command = HaelCommand(
        request_id=generate_request_id(),
        channel=Channel.VOICE,
        raw_text="Schedule for next week",
        intent=Intent.SCHEDULE_APPOINTMENT,
        brain=Brain.OPS,
        entities=entities,
        confidence=0.9,
        requires_human=False,
        missing_fields=[],
        idempotency_key="",
        metadata={
            "chosen_slot_start": chosen_start_iso,
            "call_id": "test-schedule-chosen-slot",
        },
    )

    # 3) Call handler
    print("\n2) Calling schedule_appointment with chosen_slot_start (no technician_id in metadata)...")
    result = await handle_ops_command(command)

    # 4) Report
    print("\n--- Result ---")
    print("status:", result.status)
    print("requires_human:", result.requires_human)
    print("message:", (result.message or "")[:300])

    if result.data:
        if "next_available_slots" in result.data:
            print("re-offered slots:", len(result.data["next_available_slots"]))
            for i, s in enumerate(result.data["next_available_slots"]):
                print(f"  re-offer {i+1}: start={s.get('start')} technician_id={s.get('technician_id')}")
        if result.data.get("appointment_id"):
            print("appointment_id:", result.data["appointment_id"])
            print("scheduled_time:", result.data.get("scheduled_time"))

    if result.status == OpsStatus.SUCCESS and result.data and result.data.get("appointment_id"):
        print("\nPASS: Chosen slot was accepted and appointment created.")
        return 0
    if result.requires_human and "no longer available" in (result.message or "").lower():
        print("\nFAIL: Bot said slot is 'no longer available' despite calendar open (possible bug).")
        return 1
    if result.requires_human:
        print("\nNOTE: Handler returned needs_human (may be expected if slot truly taken).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
