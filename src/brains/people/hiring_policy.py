"""
HAES HVAC - PEOPLE Brain Hiring Policy

Hiring requirements and approval rules from RDD Section 6.
"""

from src.brains.people.schema import HiringRequirements


# Required documents from RDD
REQUIRED_DOCUMENTS = [
    "Resume/CV",
    "Government ID (Driver's License or State ID)",
    "Social Security Card",
    "Work Authorization (I-9)",
]

# Background check requirements from RDD
BACKGROUND_CHECKS = [
    "Criminal Background Check",
    "Drug Screening",
    "Motor Vehicle Record (MVR) Check",
    "HVAC License Verification",
    "EPA 608 Certification Verification",
    "TDLR Registration Verification",
]

# Approvers from RDD - hiring requires joint approval
HIRING_APPROVERS = ["Junior", "Linda", "Bounthon"]

# Interview stages from RDD
INTERVIEW_STAGES = [
    "Phone Screen",
    "Technical Interview",
    "Ride-Along",
    "Final Leadership Interview",
    "Background Checks",
    "Offer",
]


def get_hiring_requirements() -> HiringRequirements:
    """
    Get all hiring requirements.

    Returns:
        HiringRequirements with documents, checks, and approval info
    """
    return HiringRequirements(
        required_documents=REQUIRED_DOCUMENTS,
        background_checks=BACKGROUND_CHECKS,
        approvers=HIRING_APPROVERS,
        interview_stages=INTERVIEW_STAGES,
    )


def get_next_steps(current_stage: str | None = None) -> list[str]:
    """
    Get next steps in the hiring process.

    Args:
        current_stage: Current stage in the process (or None for start)

    Returns:
        List of next steps
    """
    if not current_stage:
        return [
            "Submit application with required documents",
            f"Required: {', '.join(REQUIRED_DOCUMENTS[:2])}...",
            f"First interview stage: {INTERVIEW_STAGES[0]}",
        ]

    # Find current position in stages
    current_lower = current_stage.lower()
    current_index = -1

    for i, stage in enumerate(INTERVIEW_STAGES):
        if current_lower in stage.lower():
            current_index = i
            break

    if current_index < 0:
        return ["Stage not recognized - contact HR for guidance"]

    if current_index >= len(INTERVIEW_STAGES) - 1:
        return ["Final stage reached - pending offer decision"]

    next_stage = INTERVIEW_STAGES[current_index + 1]
    return [
        f"Current stage: {INTERVIEW_STAGES[current_index]}",
        f"Next stage: {next_stage}",
    ]


def format_hiring_info() -> str:
    """
    Format hiring information for display.

    Returns:
        Human-readable hiring information
    """
    requirements = get_hiring_requirements()

    lines = [
        "HAES HVAC Hiring Process",
        "",
        "Required Documents:",
    ]
    lines.extend(f"  - {doc}" for doc in requirements.required_documents)

    lines.extend([
        "",
        "Interview Stages:",
    ])
    lines.extend(f"  {i+1}. {stage}" for i, stage in enumerate(requirements.interview_stages))

    lines.extend([
        "",
        f"Hiring Approval: Joint approval from {', '.join(requirements.approvers)}",
    ])

    return "\n".join(lines)

