"""
HAES HVAC - PEOPLE Brain Handlers

Main entry point for PEOPLE brain command handling.
Handles hiring, onboarding, training, and payroll inquiries.
"""

import logging

from src.hael.schema import HaelCommand, Intent
from src.brains.people.schema import PeopleResult, PeopleStatus
from src.brains.people.hiring_policy import get_hiring_requirements, format_hiring_info
from src.brains.people.onboarding_catalog import get_onboarding_checklist, get_onboarding_summary
from src.brains.people.training_catalog import get_training_program, get_training_summary
from src.brains.people.payroll_rules import get_payroll_summary

logger = logging.getLogger(__name__)

# Supported PEOPLE intents
PEOPLE_INTENTS = {
    Intent.HIRING_INQUIRY,
    Intent.ONBOARDING_INQUIRY,
    Intent.PAYROLL_INQUIRY,
}


def handle_people_command(command: HaelCommand) -> PeopleResult:
    """
    Handle a PEOPLE brain command.

    This is the main entry point for all PEOPLE operations.

    Args:
        command: HAEL command to process

    Returns:
        PeopleResult with operation outcome
    """
    logger.info(f"PEOPLE brain handling command: {command.intent.value}")

    # Check if intent is supported
    if command.intent not in PEOPLE_INTENTS:
        return PeopleResult(
            status=PeopleStatus.UNSUPPORTED_INTENT,
            message=f"Intent '{command.intent.value}' is not handled by PEOPLE brain",
            requires_human=False,
        )

    # Check if HAEL says requires human
    if command.requires_human:
        return PeopleResult(
            status=PeopleStatus.NEEDS_HUMAN,
            message="HAEL indicated human intervention required",
            requires_human=True,
            missing_fields=command.missing_fields,
        )

    # Route to specific handler
    try:
        if command.intent == Intent.HIRING_INQUIRY:
            return _handle_hiring_inquiry(command)
        elif command.intent == Intent.ONBOARDING_INQUIRY:
            return _handle_onboarding_inquiry(command)
        elif command.intent == Intent.PAYROLL_INQUIRY:
            return _handle_payroll_inquiry(command)
        else:
            return PeopleResult(
                status=PeopleStatus.ERROR,
                message=f"Unhandled intent: {command.intent.value}",
                requires_human=True,
            )
    except Exception as e:
        logger.exception(f"Error handling PEOPLE command: {e}")
        return PeopleResult(
            status=PeopleStatus.ERROR,
            message=f"Internal error: {str(e)}",
            requires_human=True,
        )


def _handle_hiring_inquiry(command: HaelCommand) -> PeopleResult:
    """Handle hiring inquiry."""
    # Hiring inquiries don't require identity - general info
    requirements = get_hiring_requirements()

    return PeopleResult(
        status=PeopleStatus.SUCCESS,
        message=format_hiring_info(),
        requires_human=False,
        hiring_requirements=requirements,
        data={
            "interview_stages": requirements.interview_stages,
            "approval_required": True,
            "approvers": requirements.approvers,
        },
    )


def _handle_onboarding_inquiry(command: HaelCommand) -> PeopleResult:
    """Handle onboarding inquiry."""
    entities = command.entities

    # Need identity for employee-specific onboarding status
    if not entities.email:
        return PeopleResult(
            status=PeopleStatus.NEEDS_HUMAN,
            message="Need employee email to look up onboarding status",
            requires_human=True,
            missing_fields=["email"],
        )

    # Get onboarding info
    checklist = get_onboarding_checklist()
    summary = get_onboarding_summary()
    training = get_training_program()

    return PeopleResult(
        status=PeopleStatus.SUCCESS,
        message=(
            f"Onboarding checklist has {summary['total_items']} items "
            f"({summary['required_items']} required). "
            f"Training program: {training.onboarding_days}-day onboarding with "
            f"{len(training.topics)} topics."
        ),
        requires_human=False,
        onboarding_items=checklist,
        training_program=training,
        data={
            "summary": summary,
            "training_summary": get_training_summary(),
        },
    )


def _handle_payroll_inquiry(command: HaelCommand) -> PeopleResult:
    """Handle payroll inquiry."""
    entities = command.entities

    # Need identity for employee-specific payroll info
    if not entities.email:
        return PeopleResult(
            status=PeopleStatus.NEEDS_HUMAN,
            message="Need employee email to look up payroll information",
            requires_human=True,
            missing_fields=["email"],
        )

    # Get payroll info
    payroll_info = get_payroll_summary()

    return PeopleResult(
        status=PeopleStatus.SUCCESS,
        message=(
            f"Payroll is processed {payroll_info['pay_period']}. "
            "Commission: 15% on repairs, 5% on installs. "
            "Commission is paid when invoice is issued AND collected."
        ),
        requires_human=False,
        data={
            "payroll_config": payroll_info,
            "employee_email": entities.email,
        },
    )

