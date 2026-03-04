"""
Register VAPI Structured Outputs for Riley OPS (Internal Operations)

Creates structured outputs and attaches them to the Riley OPS assistant.
Completely separate from customer inbound structured outputs.
Run once to configure, then structured outputs persist in VAPI.

Usage:
    python scripts/register_ops_structured_outputs.py
"""

import os
import sys
import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings

settings = get_settings()
VAPI_API_KEY = settings.VAPI_API_KEY
ASSISTANT_ID = "fd35b574-1a9c-4052-99d8-a820e0ebabf7"  # Riley OPS

BASE_URL = "https://api.vapi.ai"
HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

# ── OPS Structured Outputs ───────────────────────────────────────────

OPS_OUTPUTS = [
    # ── Output 1: FSM Subtask Request ────────────────────────────────
    {
        "name": "FSM Subtask Request",
        "type": "ai",
        "description": (
            "Extract FSM subtask requests from this internal OPS call with HVAC-R Finest technicians. "
            "Technicians call Riley OPS to add subtasks to existing Field Service Management (FSM) jobs. "
            "They reference the parent job by its task code — a letter J followed by digits, e.g., J101246, J000532.\n\n"
            "BUSINESS CONTEXT:\n"
            "- HVAC-R Finest is an HVAC company in Dallas-Fort Worth, Texas.\n"
            "- Technicians are in the field and call to log additional work items on an existing job.\n"
            "- Each FSM job has a unique code like J101246. The technician will say this code during the call.\n"
            "- Subtasks are individual work items: 'replace condenser fan motor', 'check refrigerant levels', etc.\n\n"
            "EXTRACTION RULES:\n"
            "- parentTaskCode: REQUIRED when hasSubtasks is true. Extract the FSM job code the technician referenced. "
            "Format is J followed by digits (e.g., 'J101246'). If the technician only says digits like 'one-oh-one-two-four-six', "
            "prepend the J: 'J101246'. If they say 'job one-oh-one-two-four-six', extract as 'J101246'.\n"
            "- subtasks: REQUIRED when hasSubtasks is true. Extract ALL distinct subtasks the technician described. "
            "Each subtask needs:\n"
            "  - title: Short, action-oriented name (e.g., 'Replace condenser fan motor', 'Check refrigerant levels', "
            "'Install new thermostat', 'Inspect ductwork for leaks'). Use imperative verb form.\n"
            "  - description: Detailed context from what the technician said — equipment details, part numbers, "
            "brand/model info, symptoms observed, location on property, special instructions. "
            "Leave null if the technician only gave a brief title with no extra detail.\n"
            "- If the technician described work in a general way without listing individual subtasks, "
            "break the description into logical, separate subtask items.\n"
            "- callerName: The technician's name if they stated it during the call. Null if not mentioned.\n"
            "- callerPhone: The technician's phone number. Use the caller ID / phone number from the call metadata.\n"
            "- additionalNotes: Any extra context that doesn't belong in a specific subtask — "
            "e.g., 'customer not home until 3pm', 'needs parts ordered first', 'follow up with dispatch'. "
            "Null if no additional context.\n"
            "- hasSubtasks: Set to true if the technician requested subtasks to be added to a FSM job. "
            "Set to false if the call was about something else entirely (wrong number, general question, etc.)."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "hasSubtasks": {
                    "type": "boolean",
                    "description": (
                        "true if the technician requested one or more subtasks to be added to an existing FSM job. "
                        "false if the call was NOT about adding subtasks — e.g., wrong number, general question, "
                        "or the technician called but didn't actually request any subtask additions."
                    ),
                },
                "parentTaskCode": {
                    "type": "string",
                    "description": (
                        "The FSM task code referenced by the technician. Format: J followed by digits "
                        "(e.g., 'J101246', 'J000532'). Extract from spoken words: 'job one-oh-one-two-four-six' → 'J101246'. "
                        "If the technician says just digits without the J prefix, prepend it. "
                        "REQUIRED when hasSubtasks is true. Null when hasSubtasks is false."
                    ),
                },
                "subtasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": (
                                    "Short, action-oriented subtask name using imperative verb form. "
                                    "Examples: 'Replace condenser fan motor', 'Check refrigerant levels', "
                                    "'Install new thermostat', 'Inspect ductwork for leaks', "
                                    "'Clean evaporator coil', 'Test capacitor on compressor'. "
                                    "Keep to 3-8 words. Do not include the job code in the title."
                                ),
                            },
                            "description": {
                                "type": "string",
                                "description": (
                                    "Detailed description from what the technician said about this specific subtask. "
                                    "Include: equipment details (brand, model, size), part numbers mentioned, "
                                    "symptoms observed, location on property (rooftop, garage, attic, etc.), "
                                    "special instructions or safety notes. "
                                    "Null if the technician only gave a brief title with no additional detail."
                                ),
                            },
                        },
                        "required": ["title"],
                    },
                    "description": (
                        "Array of subtasks to create under the parent FSM task. "
                        "Extract ALL distinct work items the technician described. "
                        "If they said 'I need to replace the fan motor and check the refrigerant', "
                        "that's 2 subtasks. REQUIRED when hasSubtasks is true."
                    ),
                },
                "callerName": {
                    "type": "string",
                    "description": (
                        "The technician's name if they stated it during the call. "
                        "Extract first and last name if provided. Null if the technician didn't identify themselves by name."
                    ),
                },
                "callerPhone": {
                    "type": "string",
                    "description": (
                        "The technician's phone number. Use the caller ID from the call metadata "
                        "(the phone number the call came from). Format: E.164 if available, otherwise as captured."
                    ),
                },
                "additionalNotes": {
                    "type": "string",
                    "description": (
                        "Any extra context from the call that doesn't belong in a specific subtask description. "
                        "Examples: 'customer not home until 3pm', 'needs parts ordered before returning', "
                        "'dispatch should schedule follow-up for Thursday', 'warranty claim — previous service was last week'. "
                        "Null if no additional context beyond the subtask details."
                    ),
                },
            },
            "required": ["hasSubtasks"],
        },
    },
]


def main():
    print(f"Registering {len(OPS_OUTPUTS)} structured output(s) for Riley OPS assistant {ASSISTANT_ID}...\n")

    output_ids = []

    with httpx.Client(timeout=30) as client:
        for output_def in OPS_OUTPUTS:
            print(f"  Creating: {output_def['name']}...")
            resp = client.post(
                f"{BASE_URL}/structured-output",
                headers=HEADERS,
                json=output_def,
            )
            if resp.status_code not in (200, 201):
                print(f"    ERROR: {resp.status_code} - {resp.text}")
                continue

            data = resp.json()
            output_id = data.get("id")
            output_ids.append(output_id)
            print(f"    Created: {output_id}")

        if not output_ids:
            print("\nNo outputs created. Aborting.")
            return

        # Attach to Riley OPS assistant via artifactPlan
        print(f"\nAttaching {len(output_ids)} output(s) to Riley OPS assistant...")
        resp = client.patch(
            f"{BASE_URL}/assistant/{ASSISTANT_ID}",
            headers=HEADERS,
            json={
                "artifactPlan": {
                    "structuredOutputIds": output_ids,
                },
                "analysisPlan": {
                    "summaryPlan": {"enabled": True},
                    "successEvaluationPlan": {
                        "enabled": True,
                        "rubric": "PassFail",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Did Riley OPS successfully collect the technician's subtask request? "
                                    "Consider: did the technician provide a job number and describe the subtasks "
                                    "they needed added? A successful call means the subtask details were captured."
                                ),
                            }
                        ],
                    },
                },
            },
        )

        if resp.status_code in (200, 201):
            print("Attached successfully!")
        else:
            print(f"ERROR attaching: {resp.status_code} - {resp.text}")

    print("\nDone. Structured output IDs:")
    for oid in output_ids:
        print(f"  {oid}")
    print(f"\nRiley OPS Assistant: {ASSISTANT_ID}")
    print("Server messages required: end-of-call-report")


if __name__ == "__main__":
    main()
