"""
HAES HVAC - REVENUE Brain Handlers

Main entry point for REVENUE brain command handling.
Handles leads, quotes, and sales pipeline.
"""

import logging
from datetime import datetime

from src.hael.schema import HaelCommand, Intent
from src.brains.revenue.schema import (
    LeadData,
    LeadQualification,
    LeadSource,
    PipelineStage,
    RevenueResult,
    RevenueStatus,
)
from src.brains.revenue.qualification import qualify_lead, get_response_time_goal
from src.brains.revenue.routing import route_lead, get_primary_assignee
from src.brains.revenue.followups import generate_lead_followups

logger = logging.getLogger(__name__)

# Supported REVENUE intents
REVENUE_INTENTS = {
    Intent.QUOTE_REQUEST,
}


def handle_revenue_command(command: HaelCommand) -> RevenueResult:
    """
    Handle a REVENUE brain command.
    
    This is the main entry point for all REVENUE operations.
    
    Args:
        command: HAEL command to process
        
    Returns:
        RevenueResult with operation outcome
    """
    logger.info(f"REVENUE brain handling command: {command.intent.value}")
    
    # Check if intent is supported
    if command.intent not in REVENUE_INTENTS:
        return RevenueResult(
            status=RevenueStatus.UNSUPPORTED_INTENT,
            message=f"Intent '{command.intent.value}' is not handled by REVENUE brain",
            requires_human=False,
        )
    
    # Check if HAEL says requires human
    if command.requires_human:
        return RevenueResult(
            status=RevenueStatus.NEEDS_HUMAN,
            message="HAEL indicated human intervention required",
            requires_human=True,
            missing_fields=command.missing_fields,
        )
    
    # Route to specific handler
    try:
        if command.intent == Intent.QUOTE_REQUEST:
            return _handle_quote_request(command)
        else:
            return RevenueResult(
                status=RevenueStatus.ERROR,
                message=f"Unhandled intent: {command.intent.value}",
                requires_human=True,
            )
    except Exception as e:
        logger.exception(f"Error handling REVENUE command: {e}")
        return RevenueResult(
            status=RevenueStatus.ERROR,
            message=f"Internal error: {str(e)}",
            requires_human=True,
        )


def _handle_quote_request(command: HaelCommand) -> RevenueResult:
    """Handle a quote request."""
    entities = command.entities
    
    # Validate required fields
    missing = []
    if not (entities.phone or entities.email or entities.full_name):
        missing.append("identity (phone, email, or name)")
    if not entities.property_type:
        missing.append("property_type")
    if not entities.timeline:
        missing.append("timeline")
    
    # Strongly recommended fields (warn but don't block)
    recommended_missing = []
    if not entities.square_footage:
        recommended_missing.append("square_footage")
    if not entities.system_age_years:
        recommended_missing.append("system_age_years")
    
    if missing:
        return RevenueResult(
            status=RevenueStatus.NEEDS_HUMAN,
            message="Missing required information for quote",
            requires_human=True,
            missing_fields=missing,
            data={"recommended_missing": recommended_missing},
        )
    
    # Qualify the lead
    qualification, confidence, qual_reason = qualify_lead(
        problem_description=entities.problem_description,
        timeline=entities.timeline,
        urgency_level=entities.urgency_level,
        budget_range=entities.budget_range,
    )
    
    # Low confidence qualification should flag for human
    if confidence < 0.6:
        return RevenueResult(
            status=RevenueStatus.NEEDS_HUMAN,
            message=f"Lead qualification uncertain ({qual_reason})",
            requires_human=True,
            qualification=qualification,
            data={
                "qualification_confidence": confidence,
                "qualification_reason": qual_reason,
            },
        )
    
    # Route the lead
    assignees, routing_reason = route_lead(
        property_type=entities.property_type,
        budget_range=entities.budget_range,
    )
    
    # Generate follow-ups
    now = datetime.utcnow()
    followups = generate_lead_followups(
        lead_created_at=now,
        qualification=qualification,
        customer_email=entities.email,
        customer_phone=entities.phone,
    )
    
    # Build lead data
    lead = LeadData(
        customer_name=entities.full_name,
        customer_phone=entities.phone,
        customer_email=entities.email,
        property_type=entities.property_type,
        property_address=entities.address,
        square_footage=entities.square_footage,
        system_age_years=entities.system_age_years,
        budget_range=entities.budget_range,
        timeline=entities.timeline,
        problem_description=entities.problem_description,
        qualification=qualification,
        source=LeadSource.PHONE if command.channel.value == "voice" else LeadSource.WEBSITE,
        stage=PipelineStage.PENDING_QUOTE_APPROVAL,
        assigned_to=get_primary_assignee(assignees),
        created_at=now,
    )
    
    # Get response time goal
    response_minutes = get_response_time_goal(qualification)
    
    message = (
        f"Quote request captured - {qualification.value.upper()} lead. "
        f"Assigned to {', '.join(assignees)}. "
        f"Target response: {response_minutes} minutes."
    )
    
    return RevenueResult(
        status=RevenueStatus.SUCCESS,
        message=message,
        requires_human=False,
        lead=lead,
        qualification=qualification,
        follow_ups=followups,
        assigned_to=assignees,
        data={
            "qualification_reason": qual_reason,
            "routing_reason": routing_reason,
            "response_time_goal_minutes": response_minutes,
            "recommended_missing": recommended_missing,
        },
    )

