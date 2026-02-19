#!/usr/bin/env python3
"""
List Odoo technicians and their next available slots.

Uses the same appointment service as check_availability: live technicians
from hr.employee + res.users, then find_next_two_available_slots per tech.

Usage:
    # From project root, with .env containing Odoo credentials:
    python scripts/list_odoo_technicians_and_slots.py
    # or
    .venv/bin/python scripts/list_odoo_technicians_and_slots.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Project root
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")
load_dotenv()

from src.brains.ops.scheduling_rules import (
    BUSINESS_START,
    OPERATING_DAYS,
    SAME_DAY_DISPATCH_CUTOFF,
)
from src.brains.ops.service_catalog import infer_service_type_from_description
from src.integrations.odoo_appointments import create_appointment_service


def _next_business_day_start(now: datetime) -> datetime:
    next_start = now.replace(
        hour=BUSINESS_START.hour,
        minute=BUSINESS_START.minute,
        second=0,
        microsecond=0,
    ) + timedelta(days=1)
    while next_start.weekday() not in OPERATING_DAYS:
        next_start += timedelta(days=1)
    return next_start


def _dispatch_search_start(now: datetime, allow_same_day_after_cutoff: bool = False) -> datetime:
    if not allow_same_day_after_cutoff and now.time() >= SAME_DAY_DISPATCH_CUTOFF:
        return _next_business_day_start(now)
    baseline = now + timedelta(hours=2)
    day_start = now.replace(
        hour=BUSINESS_START.hour,
        minute=BUSINESS_START.minute,
        second=0,
        microsecond=0,
    )
    if baseline < day_start:
        baseline = day_start
    while baseline.weekday() not in OPERATING_DAYS:
        baseline = _next_business_day_start(baseline)
    return baseline


async def main() -> int:
    print("=" * 60)
    print("Odoo technicians and next available slots")
    print("=" * 60)

    try:
        appointment_service = await create_appointment_service()
    except Exception as e:
        print(f"Failed to create appointment service: {e}")
        return 1

    # Fetch live technicians
    print("\nFetching live technicians from Odoo...")
    try:
        technicians = await appointment_service.get_live_technicians()
    except Exception as e:
        print(f"Failed to get technicians: {e}")
        return 1

    if not technicians:
        print("No technicians found (hr.employee technicians with assignable res.users).")
        return 0

    print(f"Found {len(technicians)} technician(s).\n")

    service_type = infer_service_type_from_description("General service")
    duration_minutes = service_type.duration_minutes_max
    now = datetime.now()
    preferred_start = _dispatch_search_start(now, allow_same_day_after_cutoff=False)

    for i, tech in enumerate(technicians, 1):
        tech_id = tech.get("id")
        name = tech.get("name") or f"Tech #{tech_id}"
        login = tech.get("login", "")
        print(f"--- Technician {i}: {name} (id={tech_id}, login={login}) ---")

        try:
            slots = await appointment_service.find_next_two_available_slots(
                tech_id=str(tech_id),
                after=preferred_start,
                duration_minutes=duration_minutes,
            )
        except Exception as e:
            print(f"  Slots error: {e}")
            print()
            continue

        if not slots:
            print("  No available slots in horizon.")
        else:
            for j, slot in enumerate(slots, 1):
                start_str = slot.start.strftime("%A, %Y-%m-%d %I:%M %p")
                end_str = slot.end.strftime("%I:%M %p")
                print(f"  Slot {j}: {start_str} – {end_str}")
        print()

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
