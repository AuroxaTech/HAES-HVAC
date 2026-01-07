"""
HAES HVAC - PEOPLE Brain Training Catalog

Training program structure from RDD Section 6.
"""

from src.brains.people.schema import TrainingProgram, TrainingTopic


# Training topics from RDD
TRAINING_TOPICS: list[TrainingTopic] = [
    # Technical Training
    TrainingTopic(
        id="tech_hvac_fundamentals",
        name="HVAC Fundamentals",
        description="Basic HVAC principles and system components",
        duration_hours=8.0,
        required=True,
    ),
    TrainingTopic(
        id="tech_diagnostics",
        name="Diagnostic Procedures",
        description="Systematic troubleshooting and diagnostics",
        duration_hours=8.0,
        required=True,
    ),
    TrainingTopic(
        id="tech_refrigerant",
        name="Refrigerant Handling",
        description="Safe refrigerant handling and EPA compliance",
        duration_hours=4.0,
        required=True,
        certification_required=True,
    ),
    TrainingTopic(
        id="tech_electrical",
        name="Electrical Safety",
        description="Electrical systems and safety procedures",
        duration_hours=4.0,
        required=True,
    ),
    TrainingTopic(
        id="tech_installation",
        name="Installation Procedures",
        description="Equipment installation best practices",
        duration_hours=8.0,
        required=True,
    ),

    # Safety Training
    TrainingTopic(
        id="safety_osha",
        name="OSHA 10 Safety",
        description="OSHA 10-hour construction safety course",
        duration_hours=10.0,
        required=True,
        certification_required=True,
    ),
    TrainingTopic(
        id="safety_vehicle",
        name="Vehicle Safety",
        description="Company vehicle operation and safety",
        duration_hours=2.0,
        required=True,
    ),
    TrainingTopic(
        id="safety_ladder",
        name="Ladder Safety",
        description="Proper ladder use and fall prevention",
        duration_hours=2.0,
        required=True,
    ),

    # Customer Service
    TrainingTopic(
        id="cs_communication",
        name="Customer Communication",
        description="Professional customer interaction",
        duration_hours=4.0,
        required=True,
    ),
    TrainingTopic(
        id="cs_upselling",
        name="Service Recommendations",
        description="Identifying and presenting additional services",
        duration_hours=2.0,
        required=False,
    ),

    # Systems Training
    TrainingTopic(
        id="sys_odoo",
        name="Odoo System Training",
        description="Using Odoo for work orders and timekeeping",
        duration_hours=4.0,
        required=True,
    ),
    TrainingTopic(
        id="sys_inventory",
        name="Inventory Management",
        description="Parts inventory and ordering procedures",
        duration_hours=2.0,
        required=True,
    ),
]


# Training program structure from RDD
DEFAULT_TRAINING_PROGRAM = TrainingProgram(
    onboarding_days=14,  # 14-day onboarding period
    ramp_days=[30, 60, 90],  # 30/60/90 day ramp milestones
    topics=TRAINING_TOPICS,
    friday_meeting_recurring=True,  # Weekly Friday training meetings
)


def get_training_program() -> TrainingProgram:
    """Get the default training program."""
    return DEFAULT_TRAINING_PROGRAM


def get_training_topics() -> list[TrainingTopic]:
    """Get all training topics."""
    return TRAINING_TOPICS.copy()


def get_required_training() -> list[TrainingTopic]:
    """Get only required training topics."""
    return [t for t in TRAINING_TOPICS if t.required]


def get_certification_training() -> list[TrainingTopic]:
    """Get training topics that require certification."""
    return [t for t in TRAINING_TOPICS if t.certification_required]


def calculate_total_training_hours() -> float:
    """Calculate total training hours for all required topics."""
    return sum(t.duration_hours for t in get_required_training())


def get_training_summary() -> dict:
    """Get summary of training program."""
    required = get_required_training()
    certifications = get_certification_training()

    return {
        "total_topics": len(TRAINING_TOPICS),
        "required_topics": len(required),
        "total_hours": calculate_total_training_hours(),
        "certifications_required": len(certifications),
        "onboarding_days": DEFAULT_TRAINING_PROGRAM.onboarding_days,
        "ramp_milestones": DEFAULT_TRAINING_PROGRAM.ramp_days,
    }

