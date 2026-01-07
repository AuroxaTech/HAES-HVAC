#!/usr/bin/env python3
"""
HAES HVAC - HAEL Sample Verification Script

Validates HAEL extraction and routing against test fixtures.

Usage:
    uv run python scripts/verify_hael_samples.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, ".")

from src.hael import (
    Brain,
    Channel,
    Intent,
    RuleBasedExtractor,
    build_hael_command,
    route_command,
)


def load_fixtures() -> list[dict]:
    """Load test fixtures from JSON file."""
    fixtures_path = Path("tests/fixtures/hael_samples.json")
    with open(fixtures_path) as f:
        data = json.load(f)
    return data["samples"]


def verify_sample(sample: dict, extractor: RuleBasedExtractor) -> tuple[bool, list[str]]:
    """
    Verify a single sample against expected results.

    Returns:
        Tuple of (passed, list of failure messages)
    """
    failures = []
    sample_id = sample["id"]
    input_text = sample["input"]
    expected = sample["expected"]

    # Run extraction
    extraction = extractor.extract(input_text)

    # Run routing
    routing = route_command(extraction)

    # Build command
    command = build_hael_command(
        request_id=f"test-{sample_id}",
        channel=Channel.CHAT,
        raw_text=input_text,
        extraction=extraction,
        routing=routing,
    )

    # Check intent
    expected_intent = expected.get("intent")
    if expected_intent and command.intent.value != expected_intent:
        failures.append(f"Intent: expected '{expected_intent}', got '{command.intent.value}'")

    # Check brain
    expected_brain = expected.get("brain")
    if expected_brain and command.brain.value != expected_brain:
        failures.append(f"Brain: expected '{expected_brain}', got '{command.brain.value}'")

    # Check requires_human
    expected_requires_human = expected.get("requires_human")
    if expected_requires_human is not None and command.requires_human != expected_requires_human:
        failures.append(
            f"requires_human: expected {expected_requires_human}, got {command.requires_human}"
        )

    # Check urgency level
    expected_urgency = expected.get("urgency_level")
    if expected_urgency and command.entities.urgency_level.value != expected_urgency:
        failures.append(
            f"urgency_level: expected '{expected_urgency}', got '{command.entities.urgency_level.value}'"
        )

    # Check phone extraction
    if expected.get("has_phone") and not command.entities.phone:
        failures.append("Expected phone to be extracted but was None")

    # Check email extraction
    if expected.get("has_email") and not command.entities.email:
        failures.append("Expected email to be extracted but was None")

    # Check zip extraction
    if expected.get("has_zip") and not command.entities.zip_code:
        failures.append("Expected zip_code to be extracted but was None")

    # Check problem description
    if expected.get("has_problem_description") and not command.entities.problem_description:
        failures.append("Expected problem_description to be extracted but was None")

    # Check property type
    if expected.get("has_property_type") and not command.entities.property_type:
        failures.append("Expected property_type to be extracted but was None")

    # Check missing fields contain specific items
    missing_fields_contain = expected.get("missing_fields_contain", [])
    for field in missing_fields_contain:
        if not any(field in mf for mf in command.missing_fields):
            failures.append(f"Expected missing_fields to contain '{field}', got {command.missing_fields}")

    return len(failures) == 0, failures


def main() -> int:
    """Run HAEL sample verification."""
    print("=" * 60)
    print("HAES HVAC - HAEL Sample Verification")
    print("=" * 60)

    # Load fixtures
    try:
        samples = load_fixtures()
        print(f"\nLoaded {len(samples)} test samples")
    except FileNotFoundError:
        print("✗ Fixtures file not found: tests/fixtures/hael_samples.json")
        return 1

    # Create extractor
    extractor = RuleBasedExtractor()
    print(f"Using extractor: {extractor.get_name()}")

    # Run verification
    print("\n" + "-" * 60)
    passed = 0
    failed = 0

    for sample in samples:
        sample_id = sample["id"]
        description = sample.get("description", "")

        success, failures = verify_sample(sample, extractor)

        if success:
            print(f"✓ {sample_id}")
            passed += 1
        else:
            print(f"✗ {sample_id}")
            for failure in failures:
                print(f"    - {failure}")
            failed += 1

    # Summary
    print("\n" + "-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("-" * 60)

    if failed == 0:
        print("\n" + "=" * 60)
        print("PASS - All HAEL samples verified successfully")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("FAIL - Some HAEL samples failed verification")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

